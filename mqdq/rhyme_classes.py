from collections import namedtuple, UserString, UserList
from dataclasses import dataclass
from typing import List, Any
import bs4
from bs4 import BeautifulSoup
from mqdq import rhyme
import seaborn as sns
import copy

VOWEL_ORDER = {"i": 0, "e": 1, "a": 2, "ü": 3, "u": 4, "o": 5}
PALETTE = sns.hls_palette(55, s=0.5, l=0.65).as_hex()[:36]


class Syl(str):
    def __init__(self, s, **kwargs):
        if s != "_":
            self.stressed = s[0] == "`"  # bool
            try:
                if self.stressed:
                    self.onset, self.nucleus, self.coda = rhyme.ONC.split(s[1:])
                else:
                    self.onset, self.nucleus, self.coda = rhyme.ONC.split(s)

                if self.coda.startswith(("m", "n")):
                    self.nucleus += rhyme.COMBINING_TILDE

            except Exception as e:
                raise ValueError("Couldn't split %s: %s" % (s, e))
        else:
            self.onset, self.nucleus, self.coda = "", "", ""
            self.stressed = False
        super().__init__(**kwargs)

    @property
    def main_vowel(self):
        if self.nucleus:
            return self.nucleus.translate(rhyme.DEMACRON).lower()[-1]
        return ""


@dataclass
class Word:
    pre_punct: str
    syls: List[Syl]
    post_punct: str
    mqdq: bs4.element.Tag
    color: str = ""
    best_match: float = 0.0
    best_word: Any = None
    lock_color: bool = False

    # a copy should at least reset the color etc. This isn't perfect. If for example
    # someone expected to be able to make copies of Words before applying
    # line-level elision etc then they're going to be disappointed because
    # syls is a ref not a copy.
    def __copy__(self):
        return Word(self.pre_punct, self.syls, self.post_punct, self.mqdq)

    # quality of life shortcuts
    # return an empty string and not None so that
    # we can always safely do startswith and endswith
    @property
    def wb(self):
        try:
            return self.mqdq["wb"]
        except KeyError:
            return ""

    @property
    def mf(self):
        try:
            return self.mqdq["mf"]
        except KeyError:
            return ""

    @property
    def mqdq_sy(self):
        try:
            return self.mqdq["sy"]
        except KeyError:
            return ""

    @property
    def stress_idx(self):
        try:
            idx = next(i for i, v in enumerate(self.syls) if v.stressed)
        except StopIteration:
            idx = 0
        return idx

    @property
    def stressed_syllable(self):
        try:
            return self.syls[self.stress_idx]
        except IndexError:
            return None

    @property
    def post_stress(self):
        # python trix - this is safe even when the stress is
        # on the final syllable because the slice will be an
        # empty list
        return self.syls[self.stress_idx + 1 :]

    def get_color(self):
        last = self.post_stress[-1:]
        stress = self.stressed_syllable
        if last:
            last_vowel = last[-1].main_vowel
            color_idx = VOWEL_ORDER[last_vowel] * 6
            color_idx += VOWEL_ORDER[stress.main_vowel]
        elif stress:
            color_idx = VOWEL_ORDER[stress.main_vowel] * 6
        else:
            return None

        return PALETTE[color_idx]


class Line(UserList):
    def __init__(self, *args, **kwargs):
        self.words = args[0]
        self.metre = args[1]
        super(Line, self).__init__(args[0])

    def __copy__(self):
        return Line([copy.copy(w) for w in self.words], self.metre)

    @property
    def midword(self):
        mid = [
            w
            for w in self.words
            if w.mqdq_sy.endswith("3A") or w.mqdq_sy.endswith("3b")
        ]
        if len(mid) > 1:
            # Can happen when 3b is a monosyllable. For now call it strong
            return mid[0]
        elif len(mid) == 0:
            return None
        else:
            return mid[0]

    def fetch(self, pos):
        if pos == "mid":
            return self.midword
        else:
            return self[pos]

    @property
    def midword_idx(self):
        for i, w in enumerate(self.words):
            if w.mqdq_sy.endswith("3A"):
                # this will always trigger first, so if we have
                # a choice, take the strong caesura
                return i
            elif w.mqdq_sy.endswith("3b"):
                return i
        return None

    @property
    def antepenult(self):
        if self.midword_idx and self.midword_idx + 3 >= len(self):
            return None
        if len(self) < 6:
            return None
        return self[-3]


class LineSet(UserList):
    def __copy__(self):
        return LineSet([copy.copy(l) for l in self.data])

    def clean(self):

        for l in self.data:
            for w in l:
                w.best_match = 0
                w.best_word = None
                w.color = ""

    # pos1 has an array of (pos2, lim) where pos2 is the position to rhyme
    # and lim is how far ahead to look at most when linking
    BASIC_VERTICAL = {
        # endwords rhyme with endwords OR mids in the same line
        -1: [("mid", 0), (-1, 3)],
        -2: [(-2, 3)],
        "mid": [("mid", 2)],
    }

    VERTICAL_PLUS = {
        0: [(0, 3)],
        -1: [("mid", 0), (-1, 3)],
        -2: [(-2, 3)],
        "mid": [("mid", 2)],
    }

    def link(
        self, config=BASIC_VERTICAL, thresh=rhyme.GLOBAL_RHYME_THRESH, preserve=False
    ):

        # Link words in a LineSet that rhyme. Positions to compare
        # are set out in the config dict. All words which rhyme above
        # the given threshold are linked.

        for li, first_l in enumerate(self.data):
            for pos1 in config.keys():
                w1 = first_l.fetch(pos1)
                matches = []
                if not w1:
                    continue
                for lj, second_l in enumerate(self.data[li:]):
                    # lj is a positive offset index from first_l
                    for pos2, lim in config[pos1]:
                        if pos1 == pos2 and lj == 0:
                            continue
                        if lj <= lim:
                            w2 = second_l.fetch(pos2)
                            s = rhyme.word_rhyme(w1, w2)
                            if s > thresh:
                                if not preserve:
                                    if s > w1.best_match:
                                        w1.best_match = s
                                        w1.best_word = w2
                                    if s > w2.best_match:
                                        w2.best_match = s
                                        w2.best_word = w1
                                else:
                                    # only link clean words. This will not
                                    # be optimal a lot of the time. The idea
                                    # is that custom markfuncs might link and
                                    # score weird positions and we want those
                                    # to stay lit, even if a 'normal' match is
                                    # better
                                    if w1.best_match == 0:
                                        w1.best_match = s
                                        w1.best_word = w2
                                    if w2.best_match == 0:
                                        w2.best_match = s
                                        w2.best_word = w1
                        if lj >= 8:
                            # just in case someone's linking eg a whole book
                            break

    def color(self, preserve=False):

        # color takes a linked (cf link) set of lines and applies the
        # deterministic colouring metadata

        stash = [rhyme._stash_prodelision(l) for l in self.data]

        for l in self.data:
            for w in l:
                if w.best_word:
                    rhymeset = [w, w.best_word]
                    next_w = w.best_word.best_word
                    # follow the best-word matches for each word in
                    # this rhyme group (words that all kind of rhyme).
                    # when we find the best one of all, use that to
                    # colour the rest.
                    for x in range(10):
                        if not any(id(y) == id(next_w) for y in rhymeset):
                            rhymeset.append(next_w)
                            next_w = next_w.best_word
                        else:
                            # once start to loop back around we're done with our
                            # hill climb
                            break
                    rhymeset = sorted(
                        rhymeset, key=lambda w: (w.best_match, id(w)), reverse=True
                    )
                    for w in rhymeset:
                        if preserve and w.lock_color:
                            pass
                        else:
                            # if something in the set is locked then all words should
                            # copy that colour (to keep them matching) since they can't
                            # change it.
                            colorfrom = next(
                                (w for w in rhymeset if w.lock_color), rhymeset[0]
                            )
                            if colorfrom.color:
                                w.color = colorfrom.color
                            else:
                                w.color = colorfrom.get_color()

        for i, stashed_prod in enumerate(stash):
            rhyme._restore_prodelision(self.data[i], stashed_prod)

    def colorlink(
        self, config=BASIC_VERTICAL, thresh=rhyme.GLOBAL_RHYME_THRESH, preserve=False
    ):
        self.link(config, thresh, preserve)
        self.color(preserve)

    # 20/9/21 for v0.6.0 Added initial words to the rhyme scoring and linking

    END_BIAS = {
        "first_count": 1.0,
        "first_score": 0.5,
        "ult_count": 1.2,
        "ult_score": 1.0,
        "penult_count": 0.8,
        "penult_score": 0.8,
        "ante_count": 0.5,
        "ante_score": 0.0,
        "mid_count": 1.0,
        "mid_score": 0.5,
        "score_bias": 0.5,
        "score_exponent": 2.4,
    }

    END_RHYMES = {
        "first_count": 0.0,
        "first_score": 0.0,
        "ult_count": 1.0,
        "ult_score": 1.0,
        "penult_count": 0.0,
        "penult_score": 0.0,
        "ante_count": 0.0,
        "ante_score": 0.0,
        "mid_count": 0.0,
        "mid_score": 0.0,
        "score_bias": 0.5,
        "score_exponent": 2.4,
    }

    MID_RHYMES = {
        "first_count": 0.0,
        "first_score": 0.0,
        "ult_count": 0.0,
        "ult_score": 0.0,
        "penult_count": 0.0,
        "penult_score": 0.0,
        "ante_count": 0.0,
        "ante_score": 0.0,
        "mid_count": 1.0,
        "mid_score": 1.0,
        "score_bias": 0.5,
        "score_exponent": 2.4,
    }

    NEUTRAL = {
        "first_count": 1.0,
        "first_score": 1.0,
        "ult_count": 1.0,
        "ult_score": 1.0,
        "penult_count": 1.0,
        "penult_score": 1.0,
        "ante_count": 1.0,
        "ante_score": 1.0,
        "mid_count": 1.0,
        "mid_score": 1.0,
        "score_bias": 0.5,
        "score_exponent": 2.4,
    }

    def score(self, config=END_BIAS, lim=3):

        # For a linked set of lines, every word that is involved in a rhyme
        # will have a `best_match`. This method calculates a score based on
        # the config dict which adjusts the weights for rhymes in various
        # positions, the _number_ of rhymes versus the raw scores and a
        # configurable exponent (to give the scores more spread if desired).

        count = 0.0
        score = 0.0
        for idx, l in enumerate(self.data):
            if l[0].color and config["first_count"]:
                count += 1 * config["first_count"]
                score += (l[0].best_match) ** config["score_exponent"] * config[
                    "first_score"
                ]
            if l.midword and l.midword.color:
                count += 1 * config["mid_count"]
                score += (l.midword.best_match) ** config["score_exponent"] * config[
                    "mid_score"
                ]
            if l[-3].color:
                count += 1 * config["ante_count"]
                score += (l[-3].best_match ** config["score_exponent"]) * config[
                    "ante_score"
                ]
            if l[-2].color:
                count += 1 * config["penult_count"]
                score += (l[-2].best_match ** config["score_exponent"]) * config[
                    "penult_score"
                ]
            if l[-1].color:
                count += 1 * config["ult_count"]
                # endwords might match mids as well, so recalculate the best match
                # for the purposes of scoring, but DON'T recolor. This is all so we
                # can use the correct "best match" when we weight for mid_score vs
                # end_score
                end_rhymes = [0]
                # slicing past the end is safe in python
                for (idx2, l2) in enumerate(self.data[idx - lim : idx + lim + 1]):
                    if idx2 == idx:
                        continue
                    end_rhymes.append(rhyme.word_rhyme(l[-1], l2[-1]))

                if l.midword:
                    mid_rhyme = rhyme.word_rhyme(l[-1], l.midword)
                else:
                    mid_rhyme = 0

                if (
                    max(end_rhymes) * config["ult_score"]
                    >= mid_rhyme * config["mid_score"]
                ):
                    chosen_score = max(end_rhymes)
                    chosen_weight = config["ult_score"]
                else:
                    chosen_score = mid_rhyme
                    chosen_weight = config["mid_score"]

                score += (chosen_score) ** config["score_exponent"] * chosen_weight

        total = score * config["score_bias"] + count * (1 - config["score_bias"])
        return total / len(self.data)

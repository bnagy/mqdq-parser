from bs4 import BeautifulSoup
from mqdq import rhyme
from mqdq import utils
import random
import copy
import operator
import numpy as np
import scipy as sp
import pandas as pd
import functools
import string
import bisect


def slant_leo(ll):

    if len(ll) != 1:
        raise ValueError("Need %s line." % 1)

    ll = copy.copy(ll)
    w1 = ll[0].fetch("mid")
    w2 = ll[0].fetch(-1)
    s = rhyme.word_rhyme(w1, w2)
    if not s >= 1.75:
        return None
    # once word_rhyme is above the threshold both words have syls

    # if they end with the same two letters they are rhyming
    # because of grammar. Gross but it's a start
    last1 = w1.syls[-1].translate(rhyme.DEFANCY).lower()
    last2 = w2.syls[-1].translate(rhyme.DEFANCY).lower()
    if last1[-2:] == last2[-2:] and last1[-2:] in [
        "os",
        "is",
        "as",
        "us",
        "es",
        "um",
        "ae",
        "am",
    ]:
        return None

    w1.color = w2.get_color()
    w2.color = w1.color
    w1.lock_color, w2.lock_color = True, True
    if s > w1.best_match:
        w1.best_match = s
        w1.best_word = w2
    if s > w2.best_match:
        w1.best_match = s
        w2.best_word = w1

    return ll


# add an attribute to the function to track the number of
# lines it expects. Simplifies the API elsewhere.
slant_leo.length = 1
slant_leo.name = "slant leo"
slant_leo.baseline = None


def build_filter(tups, length, name=None, baseline=None, cross=False):
    def filterfn(ll):

        if len(ll) != length:
            raise ValueError("Need %s lines." % length)

        ll = copy.copy(ll)
        for t in tups:
            w1 = ll[t["w1"]["line"]].fetch(t["w1"]["idx"])
            w2 = ll[t["w2"]["line"]].fetch(t["w2"]["idx"])
            s = rhyme.word_rhyme(w1, w2)
            if not t["op"](s, t["thresh"]):
                return None
            if t["op"] == operator.ge:
                w1.color = w2.get_color()
                w2.color = w1.color
                w1.lock_color, w2.lock_color = True, True
                if s > w1.best_match:
                    w1.best_match = s
                    w1.best_word = w2
                if s > w2.best_match:
                    w1.best_match = s
                    w2.best_word = w1

        return ll

    # Abusing function attributes a little, but it simplifies the API elsewhere.
    filterfn.length = length
    filterfn.cross = cross
    if name:
        filterfn.name = name
    if baseline != None:  # 0 is Falsey lol
        # which entry in the +baseline+ we should use when working out
        # binomial stats
        filterfn.baseline = baseline

    return filterfn


leo = build_filter(
    [
        {
            "w1": {"line": 0, "idx": -1},
            "w2": {"line": 0, "idx": "mid"},
            "op": operator.ge,
            "thresh": rhyme.GLOBAL_RHYME_THRESH,
        }
    ],
    1,
    name="leo",
    baseline="leo",
)
abba = build_filter(
    [
        {
            "w1": {"line": 0, "idx": -1},
            "w2": {"line": 3, "idx": -1},
            "op": operator.ge,
            "thresh": rhyme.GLOBAL_RHYME_THRESH,
        },
        {
            "w1": {"line": 1, "idx": -1},
            "w2": {"line": 2, "idx": -1},
            "op": operator.ge,
            "thresh": rhyme.GLOBAL_RHYME_THRESH,
        },
    ],
    4,
    name="abba",
)
abab = build_filter(
    [
        {
            "w1": {"line": 0, "idx": -1},
            "w2": {"line": 2, "idx": -1},
            "op": operator.ge,
            "thresh": rhyme.GLOBAL_RHYME_THRESH,
        },
        {
            "w1": {"line": 1, "idx": -1},
            "w2": {"line": 3, "idx": -1},
            "op": operator.ge,
            "thresh": rhyme.GLOBAL_RHYME_THRESH,
        },
    ],
    4,
    name="abab",
)

aa = {}
for pos in [0, -1, -2, "mid"]:
    aa[pos] = build_filter(
        [
            {
                "w1": {"line": 0, "idx": pos},
                "w2": {"line": 1, "idx": pos},
                "op": operator.ge,
                "thresh": rhyme.GLOBAL_RHYME_THRESH,
            }
        ],
        2,
        name="aa %s" % pos,
        baseline=pos,
        cross=True,
    )

axa = {}
for pos in [0, -1, -2, "mid"]:
    axa[pos] = build_filter(
        [
            {
                "w1": {"line": 0, "idx": pos},
                "w2": {"line": 2, "idx": pos},
                "op": operator.ge,
                "thresh": rhyme.GLOBAL_RHYME_THRESH,
            }
        ],
        3,
        name="axa %s" % pos,
        baseline=pos,
    )

axxa = {}
for pos in [0, -1, -2, "mid"]:
    axxa[pos] = build_filter(
        [
            {
                "w1": {"line": 0, "idx": pos},
                "w2": {"line": 3, "idx": pos},
                "op": operator.ge,
                "thresh": rhyme.GLOBAL_RHYME_THRESH,
            }
        ],
        4,
        name="axxa %s" % pos,
        baseline=pos,
        cross=True,
    )

standard_tests = [
    leo,
    slant_leo,
    aa[-1],
    axa[-1],
    axxa[-1],
    aa[-2],
    axa[-2],
    axxa[-2],
    aa["mid"],
    axa["mid"],
    axxa["mid"],
]

extended_tests = [
    leo,
    slant_leo,
    aa[0],
    axa[0],
    axxa[0],
    aa[-1],
    axa[-1],
    axxa[-1],
    aa[-2],
    axa[-2],
    axxa[-2],
    aa["mid"],
    axa["mid"],
    axxa["mid"],
]


def bookbabs(fn, name=None):
    if not name:
        name = fn
    books = utils.bookinate(fn)
    babs = []
    for i, x in enumerate(books):
        babs.append(Babbler(x, name="%s %d" % (name, i + 1)))
    return babs


def multibabs(fns, name):
    if not fns:
        raise ValueError("No filenames! (check your glob?)")
    babs = []
    for i, fn in enumerate(fns):
        babs.append(Babbler.from_file(fn, name="%s %d" % (name, i + 1)))
    return babs


def multi_bookbabs(fns, name):
    if not fns:
        raise ValueError("No filenames! (check your glob?)")
    babs = []
    for i, fn in enumerate(fns):
        babs += bookbabs(fn, name="%s %d" % (name, i + 1))
    return babs


EXAMINATE_COLS = [
    "H-aa -1",
    "H-aa -2",
    "H-aa mid",
    "H-axa -1",
    "H-axa -2",
    "H-axa mid",
    "H-axxa -1",
    "H-axxa -2",
    "H-axxa mid",
    "H-leo",
    "H-slant leo",
    "P-aa -1",
    "P-aa -2",
    "P-aa mid",
    "P-axa -1",
    "P-axa -2",
    "P-axa mid",
    "P-axxa -1",
    "P-axxa -2",
    "P-axxa mid",
    "P-leo",
    "P-slant leo",
]


def _pivot(df):
    if df[df.metre == "P"].empty:
        # only hexameter, just double the width
        final = df.pivot(index="work", columns="test", values="pi")
        final = pd.concat([final, final], axis=1)
        cols = sorted("H-" + df["test"]) + sorted("P-" + df["test"])
    else:
        # have to pivot them individually or we get duplicate column errors
        h = df[df.metre == "H"].pivot(index="work", columns="test", values="pi")
        p = df[df.metre == "P"].pivot(index="work", columns="test", values="pi")
        final = pd.concat([h, p], axis=1)
        cols = sorted("H-" + df[df.metre == "H"]["test"]) + sorted(
            "P-" + df[df.metre == "P"]["test"]
        )
    final.columns = cols
    return final


def vectorise_books(fn, name):
    babs = bookbabs(fn, name)
    # +_pivot+ will sort the final rows in lexical order, so sort the sizes
    # to match
    sizes = [len(b.raw_source) for b in sorted(babs, key=lambda b: b.name)]
    res = pd.DataFrame()
    for b in babs:
        res = pd.concat([res, b.examinate()], ignore_index=True)
    final = _pivot(res)
    final["size"] = sizes
    return final, babs


def vectorise_single(fn, name):
    bab = Babbler.from_file(fn, name=name)
    res = bab.examinate()
    final = _pivot(res)
    final["size"] = len(bab.raw_source)
    return final, bab


def vectorise_multi(fns, name):
    babs = []
    for i, fn in enumerate(fns):
        babs.append(Babbler.from_file(fn, name="%s %d" % (name, i + 1)))
    sizes = [len(b.raw_source) for b in sorted(babs, key=lambda b: b.name)]
    res = pd.DataFrame()
    for b in babs:
        res = pd.concat([res, b.examinate()], ignore_index=True)
    final = _pivot(res)
    final["size"] = sizes
    return final, babs


def vectorise_lines(ll, name):
    bab = Babbler(ll, name=name)
    res = bab.examinate()
    final = _pivot(res)
    final["size"] = len(bab.raw_source)
    return final, bab


class Babbler:
    @classmethod
    def from_file(klass, *fns, name=None):

        raw_source = []
        for fn in fns:
            _, ll = utils.slup(fn)
            raw_source += ll

        if not name:
            name = fns[0]

        return klass(raw_source, name)

    def __init__(self, ll, name=None):

        source_h = [l for l in ll if l["metre"] == "H"]
        source_p = [l for l in ll if l["metre"] == "P"]
        self.source_h = self.preprocess(source_h)
        self.source_p = self.preprocess(source_p)
        self.raw_source = ll
        self.name = name
        self.elegiac = bool(self.source_p)

    def __len__(self):
        return len(self.raw_source)

    @functools.lru_cache(maxsize=3)
    def _syl_source(self, metre="both"):
        if metre == "H":
            source_h = [l for l in self.raw_source if l["metre"] == "H"]
            return rhyme.syllabify(source_h)
        elif metre == "P":
            source_p = [l for l in self.raw_source if l["metre"] == "P"]
            return rhyme.syllabify(source_p)
        else:
            return rhyme.syllabify(self.raw_source)

    def preprocess(self, ll):
        # TODO it would be nice to keep the syllabified words, here
        # so that would could return an mqdq.Line object, but the Word
        # objects get stomped when doing line-level elisions, so it's not
        # safe to return them to the caller when doing large amounts of
        # Babble.
        r = []
        for l in ll:
            x = []
            for w in l("word"):
                x.append(
                    {
                        "mqdq": w,
                        "syls": [
                            s.translate(rhyme.DEFANCY).lower()
                            for s in rhyme._phonetify(rhyme._syllabify_word(w)).syls
                        ],
                    }
                )
            r.append(x)
        return r

    def _last_syl(self, w):
        return w["mqdq"]["sy"][-2:]

    def _first_syl(self, w):
        return w["mqdq"]["sy"][:2]

    def _joinable(self, w1, w2):

        w1_sy = w1["syls"]
        w2_sy = w2["syls"]
        w1_last = None if not w1_sy else w1_sy[-1]
        w1_last = None if not w1_last else w1_last[-1]
        w2_first = None if not w2_sy else w2_sy[0]
        w2_first = None if not w2_first else w2_first[0]

        try:

            # workaround for some MQDQ texts that mistakenly
            # include bare punctuation as 'words'
            if not any(x in string.ascii_letters for x in w2["mqdq"].text):
                return False

            if w1["syls"] == w2["syls"]:
                return False

            ls1 = self._last_syl(w1)
            if w2["mqdq"].has_attr("mf") and w2["mqdq"]["mf"] == "PE":
                if w1["mqdq"].has_attr("mf") and w1["mqdq"]["mf"] == "SY":
                    return False
                # the problem is that a PE word could be from anywhere in
                # the line whereas all the other words are only taken
                # from words that start the correct position, so the
                # chance of adding a PE word might be inflated. Half
                # tempted not to allow PE at all :/
                if (not ls1) or (ls1[-1] in "bc"):
                    # if we tack 'st' onto a short syllable it would lengthen
                    # so don't allow PE if w1 ends short.
                    return False
                return (w1_last in "maeiou") and random.random() >= 0.5

            if w1["mqdq"].has_attr("mf") and w1["mqdq"]["mf"] == "PE":
                # w1 got elided 'backwards' onto the word before it, but
                # it was (99%) 'est' so it imposes no phonotactic
                # or metrical constraints on this next word
                return True

            if w1["mqdq"].has_attr("mf") and w1["mqdq"]["mf"] == "SY":
                # first word has elision, so make sure the next word
                # starts with a vowel (otherwise it wouldn't elide)
                return w2_first and w2_first in "aeiouyh"
            else:
                # not elided, so if w1 ends with a vowel, w2 can't start with one
                if w1_last in "maeiouy":
                    return w2_first not in "aeiouyh"

            # ends with a consonant now
            if ls1 and ls1[-1] in "bc":  # a short syllable
                if w1_last not in "aeiouyh":
                    # w1 ends in a consonant, so the next word must start vowelish
                    # otherwise the short syllable would have lengthened by position
                    return w2_first in "aeiouyh"

            # the last thing I don't know how to manage is words that should end short
            # (say 'caput' or 'timet' or something) but have lengthened by position in
            # the text. If we pick those up and they land next to w2 which starts on a
            # vowel then we get a false quantity. How much does it happen? Hard to say.
            #
            # I did some stats on syllables where this might happen, but things like 'us'
            # (the most common offender) is also legit long for genetive. Overall, it's
            # too hard, and for now we'll live with it.

        except:
            print((w1, w2))
            print((w1_sy, w2_sy))
            raise RuntimeError

        return True

    # Fisher-Yates as a generator
    def _shuffled(self, ll):
        while len(ll):
            i = random.randint(0, len(ll) - 1)
            x = ll[i]
            ll[i] = ll[-1]
            ll.pop()
            yield x

    def _build_line(self, ary, m):
        bs = BeautifulSoup(features="lxml")
        l = bs.new_tag("l")
        l["metre"] = m
        l["pattern"] = "BABBLE"  # anything but 'corrupt' or my utils will break
        l.append("\n")
        for w in ary:
            # make a copy, otherwise the source Soup gets corrupted
            l.append(copy.copy(w["mqdq"]))
            l.append("\n")
        return l

    def _fast_forward(self, line, ls):
        fn = int(ls[0])
        for idx, w in enumerate(line):
            # the idea is that if we're looking for say something in
            # foot 5, we don't look at anything until foot 4. This leaves
            # _some_ chance that we'll pick up a word with no syllables
            # but less and less as we get towards the end of the line,
            # so we should get far fewer unbuildable lines.
            if self._first_syl(w) and int(self._first_syl(w)[0]) >= fn:
                return line[idx:]
        return []

    def _build_hexameter(self):

        if not self.source_h:
            raise ValueError("No hexameters in this source text.")

        l = []
        ls = "0T"
        for y in range(10):
            # this outer loop kicks in if we reach an unfixable state and pops the last word
            for x in range(10):
                # this inner loop retries once, in case we get a final word with only ONE
                # useable continuation (in its own line). That continuation won't be hit
                # on the first run through because of the break statements

                # using Fisher-Yates because most of the time we won't get
                # through anything like the whole poem when finding a word
                # to join, so a generator with an early return is better
                # than shuffling all the indices every time
                for idx in self._shuffled(list(range(len(self.source_h)))):
                    if ls[-1] in "Ab":
                        # we want the same number but a higher position
                        # Also, l can't be empty here.
                        if ls[-1] == "A":
                            viable = "bTX"
                        else:
                            viable = "c"
                        for w in self._fast_forward(self.source_h[idx], ls):
                            if not w["mqdq"]["sy"]:
                                # empty of syllables
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    break
                            elif (
                                self._first_syl(w)[-1] in viable
                                and self._first_syl(w)[0] == ls[0]
                            ):
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    ls = self._last_syl(w)
                                    break
                    elif ls[-1] in "Tc":
                        # need to increase the foot number and find an Arsis
                        for w in self._fast_forward(self.source_h[idx], ls):
                            if not w["mqdq"]["sy"]:
                                # empty of syllables
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    break
                            # Tiny chance the line ends 6T7X (hypermetric), so allow for that
                            elif (
                                self._first_syl(w)[-1] in "AX"
                                and int(self._first_syl(w)[0]) == int(ls[0]) + 1
                            ):
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    ls = self._last_syl(w)
                                    break
                    elif ls[-1] == "X":
                        return self._build_line(l, "H")

            # couldn't build, dump last word and try again. What can happen here
            # is that we can get a non-foot-specific word like 'te' at 6A with elision
            # and there are simply no joinable words in the sample.
            l.pop()
            # search backwards for a word that has a syllable so we can rewind ls
            back_idx = -1
            ls = self._last_syl(l[back_idx])
            while not ls:
                back_idx -= 1
                ls = self._last_syl(l[back_idx])

        print(l)
        raise RuntimeError("Failed to build line somehow!")

    def _build_pentameter(self):

        if not self.source_p:
            raise ValueError("No pentameters in this source text.")

        l = []
        ls = "0T"
        for y in range(10):  # max greedy retries
            for x in range(10):  # max words in a line

                # using Fisher-Yates because most of the time we won't get
                # through anything like the whole poem when finding a word
                # to join, so a generator with an early return is better
                # than shuffling all the indices every time
                for idx in self._shuffled(list(range(len(self.source_p)))):

                    if ls == "3A":
                        # special case for pentameter. The obligatory
                        # central caesura is marked by MQDQ as 3A (start of 3rd
                        # foot) but there is no matching thesis, so start
                        # looking for 4A instead.
                        for w in self._fast_forward(self.source_p[idx], ls):
                            if self._first_syl(w) and self._first_syl(w) == "4A":
                                if not w["mqdq"]["sy"]:
                                    # empty of syllables
                                    if len(l) == 0 or self._joinable(l[-1], w):
                                        l.append(w)
                                        break
                                else:
                                    if len(l) == 0 or self._joinable(l[-1], w):
                                        l.append(w)
                                        ls = self._last_syl(w)
                                        break
                    elif ls[-1] in "Ab":
                        # we want the same number but a higher position
                        # Also, l can't be empty here.
                        if ls[-1] == "A":
                            viable = "bTX"
                        else:
                            viable = "c"
                        for w in self._fast_forward(self.source_p[idx], ls):
                            if not w["mqdq"]["sy"]:
                                # empty of syllables
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    break
                            elif (
                                self._first_syl(w)[-1] in viable
                                and self._first_syl(w)[0] == ls[0]
                            ):
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    ls = self._last_syl(w)
                                    break
                    elif ls[-1] in "Tc":
                        # need to increase the foot number and find an Arsis
                        # EXCEPT if we're at 5c in the pentameter (only) then
                        # we need a one syllable 6X
                        for w in self._fast_forward(self.source_p[idx], ls):
                            if not w["mqdq"]["sy"]:
                                # empty of syllables
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    break
                            elif (
                                self._first_syl(w)[-1] in "AX"
                                and int(self._first_syl(w)[0]) == int(ls[0]) + 1
                            ):
                                if len(l) == 0 or self._joinable(l[-1], w):
                                    l.append(w)
                                    ls = self._last_syl(w)
                                    break
                    elif ls[-1] == "X":
                        return self._build_line(l, "P")

            # couldn't build, dump last word and try again. What can happen here
            # is that we can get a non-foot-specific word like 'te' at 6A with elision
            # and there are simply no joinable words in the sample.
            l.pop()
            # search backwards for a word that has a syllable so we can rewind ls
            back_idx = -1
            ls = self._last_syl(l[back_idx])
            while not ls:
                back_idx -= 1
                ls = self._last_syl(l[back_idx])

        print(l)
        raise RuntimeError("Failed to build line somehow!")

    def hexameter(self, n=1):
        res = []
        for _ in range(n):
            res.append(self._build_hexameter())
        if n == 1:
            return res[0]
        else:
            return res

    def pentameter(self, n=1):
        res = []
        for _ in range(n):
            res.append(self._build_pentameter())
        if n == 1:
            return res[0]
        else:
            return res

    def couplet(self, n=1):
        res = []
        for _ in range(n):
            res.append(self._build_hexameter())
            res.append(self._build_pentameter())
        return res

    def _scan_samp(self, samp, scanfn, gather=False, metre="both"):

        true, false = 0, 0
        gathered = []

        for idx in range(len(samp) - scanfn.length):

            # ie if the caller passes 'H' for metre,
            # only take chunks that start on a hexameter
            if metre != "both":
                if samp[idx].metre != metre:
                    continue

            ll = samp[idx : idx + scanfn.length]
            res = scanfn(ll)
            if res:
                true += 1
                if gather:
                    gathered.append(res)
            else:
                false += 1

        return true, false, gathered

    def _random_lines(self, n=None):
        if not n:
            n = len(self.raw_source)

        # OK so to be consistent, if you want 1000 pentameters
        # then you need to generate 1000 couplets, and then
        # only look at the pentameters.
        #
        # If ever this becomes a speed issue, can hack something
        # up with the base methods. Need to do it this way so that
        # we can simulate things like 'couplets with this pattern
        # but starting on a pentameter' like +scan+ lets us do.
        if len(self.source_p) > 0:
            return self.couplet(round(n / 2))
        else:
            return self.hexameter(n)

    def simulate(self, mf, n=None, gather=False, metre="both"):

        samp = rhyme.syllabify(self._random_lines(n))

        return self._scan_samp(samp, mf, gather, metre)

    def scan(self, mf, gather=False, metre="both"):

        return self._scan_samp(self._syl_source(), mf, gather, metre)

    def _propensity(self, ci, t):

        l90, mid, h90 = ci(0.9)
        l95, _, h95 = ci(0.95)
        l99, _, h99 = ci(0.99)

        if t >= mid:
            stars = bisect.bisect_left([h90, h95, h99], t)
        else:
            stars = 3 - bisect.bisect_left([l99, l95, l90], t)

        return t / mid, "*" * stars

    def _bootstraps(self, ci):
        l90, mid, h90 = ci(0.9)
        l95, _, h95 = ci(0.95)
        l99, _, h99 = ci(0.99)
        r = {
            "l99": l99,
            "l95": l95,
            "l90": l90,
            "mid": mid,
            "h90": h90,
            "h95": h95,
            "h99": h99,
        }
        return r

    def examinate(self, tests=standard_tests, n=101, max_brute=5_000_000):

        res = []
        f = self.bootstrap_ci(*tests, n=n)
        for m, results in f.items():
            for idx, ci in enumerate(results):
                bs = self._bootstraps(ci)
                t, f, _ = self.scan(tests[idx], gather=False, metre=m)
                pi, stars = self._propensity(ci, t)

                if tests[idx].baseline != None:
                    # cross tests are ones like aa or axxa where a pent will be rhymed to
                    # a hex (in elegiacs) In that case use the cross-metre baseline,
                    # For things like AXA where both lines will be the same type, we
                    # use the H or P baseline as appropriate.
                    if tests[idx].cross and self.elegiac:
                        bl5, bl, bl95 = self._baseline(
                            tests[idx].baseline, "cross", max_brute=max_brute
                        )
                    else:
                        bl5, bl, bl95 = self._baseline(
                            tests[idx].baseline, m, max_brute=max_brute
                        )

                    expected = (t + f) * bl
                    if t < expected:
                        alt = "less"
                    else:
                        alt = "greater"

                    p = sp.stats.binom_test(t, t + f, bl, alternative=alt)
                    # If we have simulated baselines then we can make a more conservative
                    # estimate of the p value by using the 95th percentile (simulated)
                    # baseline as our ground truth for the binomial test (and similar for
                    # the 5th if our chosen alternative is 'less')
                    extreme_p = p
                    if alt == "less" and bl5:
                        extreme_p = sp.stats.binom_test(t, t + f, bl5, alternative=alt)
                    if alt == "greater" and bl95:
                        extreme_p = sp.stats.binom_test(t, t + f, bl95, alternative=alt)
                else:
                    expected = 0
                    alt = None
                    p = 1
                    extreme_p = 1

                row = {
                    "work": self.name,
                    "metre": m,
                    "test": tests[idx].name,
                    "pi": pi,
                    "stars": stars,
                    "t": t,
                    "f": f,
                    "sum": t + f,
                    "expected": round(expected),
                    "alternative": alt,
                    "binom": p,
                    "conservative": extreme_p,
                }
                row.update(bs)
                res.append(row)
        return pd.DataFrame(res)

    def vector(self):
        if self.elegiac:
            return self.examinate()["pi"]
        else:
            # for hexameters we want a vector of the same length
            # as for elegiacs, so just double it until we think
            # of a better approach
            hv = self.examinate()["pi"]
            return hv.append(hv)

    def _rhyme_pct(self, set1, set2=None, n=5000, thresh=rhyme.GLOBAL_RHYME_THRESH):

        hit = 0
        idx1 = np.random.randint(len(set1), size=n)
        if set2:
            idx2 = np.random.randint(len(set2), size=n)
        else:
            idx2 = np.random.randint(len(set1), size=n)

        for i in range(n):
            if set2:
                score = rhyme.word_rhyme(set1[idx1[i]], set2[idx2[i]])
            else:
                score = rhyme.word_rhyme(set1[idx1[i]], set1[idx2[i]])
            if score >= thresh:
                hit += 1
        return hit / n

    def _brute_word_rhyme(self, set1, set2=None, thresh=rhyme.GLOBAL_RHYME_THRESH):
        hit = 0
        tries = 0
        for i in range(len(set1)):
            if set2:
                for w2 in set2:
                    tries += 1
                    score = rhyme.word_rhyme(set1[i], w2)
                    if score >= thresh:
                        hit += 1
            else:
                # if we are comparing within one set then we can
                # just do the comparisons above the diagonal of the
                # matrix (rhyme is symmetric) and avoid counting twice
                # - i+1 because we don't want to compare words to themselves
                # - 'falling off the end' (ary[4:] when ary is length 4) gives [] in Python
                for w2 in set1[i + 1 :]:
                    tries += 1
                    score = rhyme.word_rhyme(set1[i], w2)
                    if score >= thresh:
                        hit += 1
        return (hit, tries)

    # http://www.jtrive.com/the-empirical-bootstrap-for-confidence-intervals-in-python.html
    def _bootstrap(self, f, n=101, m=50000):
        """
        Generate `n` bootstrap samples, evaluating `f`
        at each resampling. `bootstrap` returns a function,
        which can be called to obtain confidence intervals
        of interest.
        """
        simulations = [None] * n
        for c in range(n):
            simulations[c] = f(m)
        simulations.sort()

        def ci(p):
            """
            Return 2-sided symmetric confidence interval specified
            by p.
            """
            u_pval = (1 + p) / 2.0
            l_pval = 1 - u_pval
            l_indx = int(np.floor(n * l_pval))
            u_indx = int(np.floor(n * u_pval))
            m_idx = int(np.floor(len(simulations) / 2))
            return (simulations[l_indx], simulations[m_idx], simulations[u_indx])

        return ci

    def _sample_word_rhyme(self, set1, set2=None, n=101, m=50000, ci=0.95):
        def f(n):
            return self._rhyme_pct(set1, set2, n=n)

        b = self._bootstrap(f, n, m)
        return b(ci)

    def _brute_or_sim(self, set1, set2=None, max_brute=5_000_000):
        n = 0
        if set2:
            n = len(set1) * len(set2)
        else:
            n = (len(set1) ** 2) / 2

        if n < max_brute:
            h, t = self._brute_word_rhyme(set1, set2)
            return (None, h / t, None)
        else:
            return self._sample_word_rhyme(set1, set2, m=int(max_brute / 100))

    BASELINE_POSITION_DEFAULTS = [-1, -2, "mid"]

    def baselines(self, positions=BASELINE_POSITION_DEFAULTS, max_brute=5_000_000):

        baselines = {}
        for m in ["H", "P", "cross"]:

            if m != "H" and not self.elegiac:
                continue

            this = {}
            for pos in positions:
                this[pos] = self._baseline(pos, m, max_brute)

            if m in ["H", "P"]:
                # no leo for cross metres (leo occurs inside one line)
                this["leo"] = self._baseline("leo", m, max_brute)

            baselines[m] = this

        return baselines

    @functools.lru_cache(maxsize=128)
    def _baseline(self, pos, m, max_brute=5_000_000):

        """
        Take one baseline. Builds a set of all words appearing at a given
        position, and then determines the rhyminess of that set.
        pos - an index (0, -1, -2 etc) OR the special position 'leo'
        m - for vertical rhymes, specify whether to take H, P or 'cross'
        rhymes (rhymes at the given position with one in H one in P)
        """

        if m != "H" and not self.elegiac:
            raise ValueError("No metre '%s' in hexameters" % m)

        if pos == "leo":
            # the Leonine scanner can't work on cross lines, and needs slightly special
            # handling
            if m == "P":
                mids_p = [
                    l.fetch("mid")
                    for l in self._syl_source(metre="P")
                    if l.fetch("mid")
                ]
                adj = len(mids_p) / len(self._syl_source(metre="P"))
                ults_p = [l.fetch(-1) for l in self._syl_source(metre="P")]
                bl = self._brute_or_sim(mids_p, ults_p, max_brute=max_brute)
                bl = tuple(x * adj if x else None for x in bl)
            elif m == "H":
                mids_h = [
                    l.fetch("mid")
                    for l in self._syl_source(metre="H")
                    if l.fetch("mid")
                ]
                adj = len(mids_h) / len(self._syl_source(metre="H"))
                ults_h = [l.fetch(-1) for l in self._syl_source(metre="H")]
                bl = self._brute_or_sim(mids_h, ults_h, max_brute=max_brute)
                bl = tuple(x * adj if x else None for x in bl)
            else:
                raise ValueError("No metre '%s' for Leonine" % m)
        else:
            # The 'adjustment' here is designed for midwords. If the set of lines
            # containing eg a mid is smaller than the total number of lines then
            # the expected number of rhymes needs to include the probability that
            # the line contains the feature at all. For some authors (eg Ovid) it
            # will make almost no difference, for others it will be significant.
            h = [l.fetch(pos) for l in self._syl_source(metre="H") if l.fetch(pos)]
            h_adjust = len(h) / len(self._syl_source(metre="H"))
            p = [l.fetch(pos) for l in self._syl_source(metre="P") if l.fetch(pos)]
            adj = 1
            if p:
                p_adjust = len(p) / len(self._syl_source(metre="P"))
            if m == "cross":
                # if the scan function works on 'cross' lines (one H, one P) eg
                # scanning for couplets, then we need to compare the rhyminess of
                # the given position in H lines vs P lines
                bl = self._brute_or_sim(h, p, max_brute=max_brute)
                adj = h_adjust * p_adjust
            elif m == "H":
                # otherwise we just use only either H or P and compare within that set
                bl = self._brute_or_sim(h, max_brute=max_brute)
                adj = h_adjust ** 2
            elif m == "P":
                bl = self._brute_or_sim(p, max_brute=max_brute)
                adj = p_adjust ** 2
            else:
                raise ValueError("Can't handle metre '%s'" % m)

            # for small texts the upper and lower estimates are None because the ground
            # truth is exhaustively brute forced.
            bl = tuple(x * adj if x else None for x in bl)

        return bl

    @functools.lru_cache(maxsize=128)
    def bootstrap_ci(self, *fns, n=101, m=None, metres=None):

        cis = []

        if not m:
            m = len(self.raw_source)

        if not metres:
            if len(self.source_p) > 0:
                metres = ["H", "P"]
            else:
                metres = ["H"]

        final = {}
        for met in metres:
            # each metre will get an array of sample arrays
            final[met] = [[] for _ in range(len(fns))]

        for ni in range(n):
            rs = rhyme.syllabify(self._random_lines(m))
            for met in metres:
                for idx, fn in enumerate(fns):
                    # scan rs with all the functions
                    t, _, _ = self._scan_samp(rs, fn, gather=False, metre=met)
                    final[met][idx].append(t)

        for m, samp_arys in final.items():
            for idx, simulations in enumerate(samp_arys):
                simulations.sort()

                # adding a default argument makes sure that the function closes
                # around the correct array. Default arguments like this are
                # evaluated at definition time, not at call time. Yay python :/
                def ci(p, ary=simulations):
                    """
                    Return 2-sided symmetric confidence interval specified
                    by p.
                    """
                    u_pval = (1 + p) / 2.0
                    l_pval = 1 - u_pval
                    l_indx = int(np.floor(n * l_pval))
                    # TODO should this be ceil?
                    u_indx = int(np.floor(n * u_pval))
                    m_idx = int(np.floor(len(ary) / 2))
                    return (ary[l_indx], ary[m_idx], ary[u_indx])

                samp_arys[idx] = ci

        return final

    def scanblat(self, fn, metre="both", book=True):
        t, f, r = self.scan(fn, gather=True, metre=metre)
        print(
            "Hit: %d Miss: %d Total %d Pct: %.2f\n" % (t, f, t + f, t / (t + f) * 100)
        )
        for ll in r:
            ll.colorlink(preserve=True)
        for x in sorted(r, key=lambda x: x.score(), reverse=True,)[
            : max(20, int(len(r) / 10))
        ]:  # top 10% or top 20 at worst
            utils.nbshow(x, book=book)
            print("\n" + "-" * 15 + "^ Score: %.2f ^" % x.score() + "-" * 15 + "\n")

    def vectorise(self, n=101):
        res = self.examinate(n=n)
        final = _pivot(res)
        final["size"] = len(self.raw_source)
        return final

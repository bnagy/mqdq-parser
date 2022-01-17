import bs4
from collections import Counter
import re
import numpy as np
import pandas as pd
from mqdq import utils
from mqdq import rhyme

DEFANCY = str.maketrans(
    {"ü": "y", u"\u0304": None, u"\u0303": None, "`": None, "_": None}
)


def classify_caesura(l, n, strict=False):

    """Classify the caesura occurring in foot n.

    Args:
        l (bs4 <line>): Line to classify
        n (int): Foot number to classify (1..6)
        strict (bool): If True, consider Quasi as None

    Returns:
        string: Q, -, W, or S (Quasi, None, Weak, Strong)
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")

    try:
        for w in l("word"):
            # syllable string ends with A, and there's a wordbreak
            # so this is a strong caesura
            if re.search("%dA$" % n, w["sy"]) and w.has_attr("wb"):
                return "S"
            elif re.search("%db$" % n, w["sy"]) and w.has_attr("wb"):
                return "W"
            elif (
                re.search("%d[Ab]$" % n, w["sy"])
                and w.has_attr("mf")
                and w["mf"] == "SY"
            ):
                if not strict:
                    return "Q"
                else:
                    return "-"
            elif re.search("%d[Tc]" % n, w["sy"]):
                # we've passed the end of the foot in question
                return "-"
    except:
        raise ValueError("Can't handle this: %s" % l)


def elision_after_foot(n, l):

    """Is there elision after foot n?

    Args:
        n (int): Foot number to check (1..6)
        l (bs4 <line>): Line to check

    Returns:
        (bool): The result
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")

    try:
        for w in l("word"):
            if re.search("%d[Tc]" % n, w["sy"]):
                if w.has_attr("mf") and w["mf"] == "SY":
                    return True
                return False

        return False

    except:
        raise ValueError("Can't handle this: %s" % l)


def metrical_nucleus(l, strict=False, start=2, end=4):

    """
    DEPRECATED: WILL VANISH IN FUTURE VERSIONS. USE: caesurae

    Classify the caesurae in the second, third and fourth feet
    (sometimes called 1.5, 2.5, 3.5).

    Args:
        l (bs4 <line>): Line to operate on
        strict (bool): If True, consider Quasi as None

    Returns:
        (string): A three element string, made up of the following:
                  Q, -, W, or S (Quasi, None, Weak, Strong)
    """
    return "".join(map(lambda f: classify_caesura(l, f, strict), range(start, end + 1)))


caesurae = metrical_nucleus


def has_3rd_foot_caes(l, strict=True):

    """Determine whether a line has any kind of caesura in the third foot.

    Args:
        l (bs4 <line>): Line to check
        strict (bool): If True, don't accept Quasi caesurae (occurring over an elision)

    Returns:
        (bool): The result
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")

    try:
        caes = classify_caesura(l, 3)
        if strict:
            if caes == "-" or caes == "Q":
                return False
        else:
            if caes == "-":
                return False
        return True

    except:
        raise ValueError("Can't handle this: %s" % l)


def diaer_after_foot(n, l):

    """Determine whether a line contains a bucolic diaeresis.

    Args:
        n (int): Foot to check (1 to 5)
        l (bs4 <line>): Line to check

    Returns:
        (bool): The result
    """

    if n not in range(1, 6):
        raise ValueError("Foot to check must be between 1 and 5")

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")

    try:
        # Here's an example line:
        # <line name="52" metre="H" pattern="DSSD">
        #   <word sy="1A1b1c2A" wb="CM">Oceanus</word>
        #   <word sy="2T3A" wb="CM">fontes</word>
        #   <word sy="3T4A4b4c" wb="DI">torrentibus</word>
        #   <word sy="5A5b5c" wb="DI">ingruit</word>
        #   <word sy="6A6X">undis.</word>
        # </line>

        # So, if the word has a 'DI' word boundary, and its
        # syllables _end_ with the thesis of the given foot
        # (4T for spondee, 4c for dactyl) then we should be done
        for w in l("word"):
            if (
                re.search("%d[cT]$" % n, w["sy"])
                and w.has_attr("wb")
                and w["wb"] == "DI"
            ):
                return True
        return False
    except:
        raise ValueError("Error processing: %s" % line)


def diaereses(l, start=1, end=5):
    return "".join(
        map(lambda f: "T" if diaer_after_foot(f, l) else "F", range(start, end + 1))
    )


def has_bd(line):

    """Determine whether a line contains a bucolic diaeresis.

    Args:
        l (bs4 <line>): Line to check

    Returns:
        (bool): The result
    """

    return diaer_after_foot(4, line)


def _get_syls_with_stress(w):
    if w["sy"] == "":
        return "_"
    if len(w["sy"]) <= 2 and not _has_elision(w):
        return w["sy"]
    if w.text.lower() in _UNACCENTED:
        return w["sy"]
    syls = re.findall("..", w["sy"])
    stress = _stressed(w)
    syls[stress] = "`" + syls[stress]
    return "".join(syls)


def _stressed(w):

    if w.text.lower() in _ACCENT_LAST_FOOT:
        return -1

    syls = re.findall("..", w["sy"])

    # For words with elision and a long syllable ending, I assume the stress
    # stayed on that syllable. This is based on analysing lots of hexameter poetry.
    #
    # 3:464>  Dona dehinc auro grauia sectoque elephanto
    #         1A1b 1c2A   2T3A 3b3c4A 4T5A_    5b5c6A6X
    #
    # We assume that 5A is stressed, so that the ictus and accent coincide.
    # Whereas:
    #
    # Absenti Aeneae currum geminosque iugalis
    # 1A1T_   2A2T3A 3T4A   4b4c5A5b   5c6A6X
    #
    # There's a pretty good chance that 1A is _not_ stressed

    if _has_elision(w) and re.match(".[ATX]", syls[-1]):
        return -1

    # For words ending with a short syllable, though, we ignore
    # the elision. Aeneid is 'packed' with lines like this:
    #
    # 1:177>  Tum Cererem corruptam undis Cerealiaque arma
    #         1A  1b1c2A  2T3A_     3T4A  4b4c5A5b5c_ 6A6X
    #
    # and if we moved the stress it wouldn't fall on 5A anymore.

    # In all remaining cases, we DO consider clitics for the purpose of stress.
    # cf Allen, Vox Latina, or any of a million grammatici

    if len(syls) == 1:
        return 0
    # Two syls, always first syllable
    elif len(syls) == 2:
        return 0
    # If three or more...
    else:
        # Second last syllable is long then it takes the stress
        # (in this markup, long syls are uppercase A, T or X
        if re.match(".[ATX]", syls[-2]):
            return -2
        # otherwise it's the syllable before that is stressed
        else:
            return -3


# cf Allen, Vox Latina (1965), 87-8
_UNACCENTED = {
    "at",
    "ac",
    "atque",
    "et",
    "sed",
    "igitur",
    "vel",
    "aut",
    "iam",
    "seu",
    "nam",
}
_ACCENT_LAST_FOOT = {"nostras", "illic", "adhuc", "tanton", "adduc"}


def _conflict(w, foot):

    # Not only does the stress need to fall on an Arsis, but it needs to
    # fall on the arsis of the foot we're actually interested in.

    # if a word has no stress, then the ictus is not stressed, so it's
    # a conflict.
    if w.text.lower() in _UNACCENTED:
        return True

    syls = re.findall("..", w["sy"])
    if len(w["sy"]) == 0:
        raise ValueError("No syllables?")

    # A means arsis, which is the start of either a spondee or dactyl
    if syls[_stressed(w)] == ("%dA" % foot):
        return False
    return True


def _has_elision(w):
    # SY for synalepha
    return w.has_attr("mf") and w["mf"] == "SY"


def ictus_conflicts(l):

    """Count the number of ictus conflicts in a line, considering
    every foot (not every word).

    Args:
        l (bs4 <line>): Line to check

    Returns:
        (int): Number of conflicts (0..6)
    """

    # Slightly magic. True counts as 1 in python, False as 0
    return sum([conflict_in_foot(f, l) for f in range(1, 7)])


def caps(l):

    """Count the number of capital letters in a line. This can be
    useful for counting proper nouns, but is very sensitive to
    the properties of your edition. Use with caution.

    Args:
        l (bs4 <line>): Line to check

    Returns:
        (int): Number of uppercase letters
    """

    return sum([x[0].isupper() for x in [w.text for w in l("word")]])


CLITICS = ("que", "ne", "ve")


def conflict_in_foot(n, l):

    """Determine if the nth foot in the given line has an ictus/accent conflict

    Args:
        n (int): Foot to check (1..6)

    Returns:
        (bool): True if a conflict exists, False otherwise
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")

    containing_word = next(
        (w for w in l("word") if re.search("%dA" % n, w["sy"])), None
    )
    if not containing_word:
        raise ValueError("No arsis for syllable %d in line?? %s" % (n, l))

    return _conflict(containing_word, n)


def predictors_by_foot(l):

    """
    DEPRECATED: NOTHING USES THIS NOW

    Return a list of the predictors for this line (by foot).
    The things we know about are:
    - Foot length (S or D)
    - Foot ictus harmony (C or H)
    - Foot caesura (S, W, Q, -)
    - Foot bucolic diaeresis

    We record the following per foot as a compound string
    - 1 - length, harmony (4 levels)
    - 2 - length, harmony, caesura (16 levels)
    - 3 - length, harmony, caesura (16 levels)
    - 4 - length, harmony, caesura, BD (32 levels)

    Args:
        l (bs4 <line>): Line to analyze

    Returns:
        (list): a list of four strings
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")
    try:
        l1, l2, l3, l4 = list(l["pattern"])[:4]
        h1, h2, h3, h4 = list(harmony(l))
        c2, c3, c4 = list(metrical_nucleus(l, strict=False))
        bd4 = "T" if has_bd(l) else "F"

        f1 = "".join([l1, h1])
        f2 = "".join([l2, h2, c2])
        f3 = "".join([l3, h3, c3])
        f4 = "".join([l4, h4, c4, bd4])

        return [f1, f2, f3, f4]
    except:
        raise ValueError("Error processing: %s" % l)


def predictors_by_feature(l):

    """
    DEPRECATED: NOTHING USES THIS NOW

    Return a list of predictors for this line (by feature).

    The returned strings are:
    - Quantity of each the first four feet (eg "SSDS")
    - Harmony/Conflict of the first four feet (eg "CHCH")
    - Caesurae in the 2nd, 3rd and 4th foot (eg "SW-")
    - Whether the line has bucolic diaeresis ("T" or "F")

    Args:
        l (bs4 <line>): Line to analyze

    Returns:
        (list): a list of four strings
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt line!")
    try:
        f1 = l["pattern"][:4]
        f2 = harmony(l)
        f3 = metrical_nucleus(l, strict=False)
        f4 = "T" if has_bd(l) else "F"

        return [f1, f2, f3, f4]
    except:
        raise ValueError("Error processing: %s" % l)


# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def _chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


def _chunk_mean(df, n, round=True):

    # - 'arange' NOT 'arrange' - a list [0..len(df)]
    # ie group by the result of row_index div (integer division) n
    # then apply mean() to each group

    newdf = df.groupby(np.arange(len(df)) // n).mean()
    if round and len(df) % n != 0:
        newdf = newdf[:-1]
    return newdf


def _funky_map(l, mappers):

    # Each entry in mappers to consist of a lambda and a baseline
    # The lambda should return something that can be coerced into
    # a list.
    # eg [lambda l: l['pattern'][:4], 'S']
    # the lambda will return 'DDSS' and then each value is
    # compared to the baseline ('S')
    # final result would be [0,0,1,1]

    res = []
    for fn, comp in mappers:
        for x in list(fn(l)):
            res.append(1 if x == comp else 0)
    return res


VALID_FEET = set("DS")


def _pent_pattern(l):
    return [c for c in l["pattern"] if c in VALID_FEET]


def _pent_harmony(l):
    a = list(harmony(l, n=5))
    # The third entry will always be the half-foot
    # it is word-final, so can never be in harmony
    del a[2]
    return a


def _pent_diaereses(l):
    a = list(diaereses(l, end=5))
    # The half-foot can't have diaeresis
    del a[2]
    return a


def _pent_caesurae(l):
    a = list(caesurae(l, start=1, end=5))
    # The half-foot is an obligatory strong caesura
    del a[2]
    return a


def binary_features(l):
    if l["metre"] == "H":
        return _funky_map(
            l,
            [
                [lambda l: l["pattern"][:4], "S"],
                [lambda l: harmony(l), "C"],
                [lambda l: diaereses(l, start=1, end=4), "T"],
                [lambda l: caesurae(l, start=1, end=4), "S"],
                [lambda l: caesurae(l, start=1, end=4), "W"],
            ],
        )
    elif l["metre"] == "P":
        return _funky_map(
            l,
            [
                [lambda l: _pent_pattern(l)[:4], "S"],
                [_pent_harmony, "C"],  # NB these are being passed as functions
                [_pent_diaereses, "T"],
                [_pent_caesurae, "S"],
                [_pent_caesurae, "W"],
            ],
        )
    else:
        raise ArgumentError("Unknown metre type %s" % l["metre"])


BINARY_FEATURES = [
    "1SP",
    "2SP",
    "3SP",
    "4SP",
    "1CF",
    "2CF",
    "3CF",
    "4CF",
    "1DI",
    "2DI",
    "3DI",
    "4DI",
    "1SC",
    "2SC",
    "3SC",
    "4SC",
    "1WC",
    "2WC",
    "3WC",
    "4WC",
]
ALL_FEATURES = BINARY_FEATURES + ["ELC"]


def chunked_features(ll, n=None, feats=ALL_FEATURES):

    """Take a set of binary features per line, and return a chunked average.

    Eg if the feature was F1S (first foot spondee), every line would be given
    a 1 or 0, and the result would be the proportion of lines in the chunk with
    that feature.

    NB: If the length of `ll` is not divisible by `n` the last chunk will still be
        calculated, but the variance might be high. It's up to the user to drop that
        chunk, if this is a problem.

    Args:
        ll (list of bs4 <line>s): Lines to operate on
        n (int): chunk size (1 .. len(ll))

    Returns:
        (pandas.DataFrame): The results, one per row, with a header row
                            matching the predefined features
    """

    # if they give us just one line instead of wrapping it
    # in a list as they should then be nice to them
    if ll.__class__ == bs4.element.Tag:
        ll = [ll]

    if n and n > len(ll):
        raise ValueError("Chunk size must be <= number of lines")
    if not n:
        n = len(ll)

    df = pd.DataFrame(map(lambda l: binary_features(l), ll), columns=BINARY_FEATURES)
    if "ELC" in feats:
        df["ELC"] = [la.elision_count(l) for l in ll]
    return _chunk_mean(df[feats], n)


def elision_count(l):

    """Returns the number of elisions in a given line

    Args:
        l (a bs4 <line>): The line

    Returns:
        (int): The number of elisions
    """

    return sum([(1 if _has_elision(w) else 0) for w in l("word")])


def distribution(ll, feats=ALL_FEATURES):

    """Transforms the lines into the feature vectors, but doesn't chunk them. This
    means that we have one observation per line. Since this transformation is the
    slowest part of the process it can be useful to do this once before using methods
    that sample or analyze multiple times.

    Rather than calculating lots of these with different feature sets, it is probably
    better to calculate it with ALL_FEATURES and then subset the DataFrame using []

    Args:
        ll (list of bs4 <line>s): Lines to operate on

    Returns:
        (pandas.DataFrame): The results, one per row, with a header row
                            matching the predefined features
    """

    return chunked_features(ll, n=1, feats=feats)


def centroid(ll, feats=ALL_FEATURES):

    """Returns the centroid (vector average) for the given set of lines

    Args:
        ll (list of bs4 <line>s): Lines to operate on

    Returns:
        (pandas.DataFrame): A DF containing one row, the centroid
    """

    return chunked_features(ll, len(ll), feats)


def harmony(l, n=4):

    """Calculate the ictus conflicts for the first four feet (since the final
    two feet are almost always in harmony)

    Args:
        l (bs4 <line>): Line to check

    Returns:
        (string): String of four characters (Conflict or Harmony) 'CHHC'
    """

    if l["pattern"] == "corrupt":
        raise ValueError("Can't operate on a corrupt l!")

    res = []
    try:
        for i in range(1, n + 1):  # (stops at 4 not 5)
            if conflict_in_foot(i, l):
                res.append("C")
            else:
                res.append("H")

        return "".join(res)
    except:
        raise ValueError("Error processing: %s" % l)


def raw_scansion(l):
    return [_get_syls_with_stress(w) for w in l("word")]


def raw_phonetics(l):
    return [
        w.pre_punct + ".".join(w.syls) + w.post_punct for w in rhyme.syllabify_line(l)
    ]


def raw_phonemics(l):
    return ["".join(w.syls).lower().translate(DEFANCY) for w in rhyme.syllabify_line(l)]


def word_idx_syls(l, idx):

    """For a given line, return the number of syllables in the word appearing
    at index `idx`. Attempts to cater for elision and prodelision (eg mea est
    at the end of a line will yield two syllables for the final word).

    Args:
        l (bs4 <line>: Line to operate on
        idx (int): Line position (negative indices are OK)

    Returns:
        (float): Number of syllables
    """

    ww = l("word")
    try:
        w = ww[idx]
    except IndexError:
        raise IndexError("No word at index %d: %s" % (idx, utils.txt(l)))
    if not w["sy"]:
        if w.has_attr("mf") and w["mf"] == "PE" and idx != 0:  # don't wrap
            # prodelision, include the word before in the count (eg mea est -> meast)
            try:
                count = word_idx_syls(l, idx - 1)
            except IndexError:
                raise IndexError(
                    "IndexError going backwards at prodelision %d: %s"
                    % (idx, utils.txt(l))
                )
        elif w.has_attr("mf") and w["mf"] == "SY" and idx != -1:
            # ordinary elision, include the next word (eg cum arte -> carte)
            try:
                count = word_idx_syls(l, idx + 1)
            except IndexError:
                raise IndexError(
                    "IndexError going forwards at elision %d: %s" % (idx, utils.txt(l))
                )
        else:
            raise ValueError(
                "Word at index %d has no syllables?: %s" % (idx, utils.txt(l))
            )
    else:
        count = len(w["sy"]) / 2
    return count

import re
import numpy as np
from typing import Iterable, Callable
from mqdq import rhyme
from mqdq.rhyme_classes import Word, Line

CONS_SPACE = {
    "p": 0.0,
    "b": 0.0303030303030303,
    "m": 0.0606060606060606,
    "w": 0.0909090909090909,
    "f": 0.1212121212121212,  # ^^ labial
    "t": 0.1515151515151515,  # vv coronal
    "d": 0.1818181818181818,
    "n": 0.2121212121212121,
    "l": 0.2424242424242424,
    "r": 0.2727272727272727,
    "s": 0.303030303030303,
    "z": 0.3333333333333333,  # ^^ coronal
    # DELIBERATE GAP HERE
    "g": 0.6666666666666666,  # vv dorsal
    "k": 0.75,
    "j": 0.8333333333333333,
    "x": 0.9166666666666666,
    "h": 0.95,
    "": 1.0,  # null sound is closest to 'h'
}

# Follows the sounds around from [i] (high front), down the front, back to [o]
# (low back) and up the back ending at y (=[ɯ])
VOWEL_SPACE = {"i": 0.0, "e": 0.2, "a": 0.4, "o": 0.6, "u": 0.8, "y": 1.0}


def _locate(s: str, h: dict[str, float]) -> float:
    """Given an initial mapping of single character tokens, return a float for
    any single token or cluster of tokens."""
    if s in h:
        return h[s]
    try:
        h[s[0]]
    except KeyError:
        raise ValueError("Couldn't find anchor for cluster")
    for i in range(1, len(s)):
        # we build up increasing substrings, so spr makes
        # a point 'sp' between s and p (closer to p) then
        # makes a point spr between sp and r
        left = s[:i]
        right = s[i]
        h[left + right] = (h[left] + h[right] * 3) / 4
    if not s in h:
        raise ValueError("Failed to locate %s somehow", s)
    return h[s]


def _syl_meta(w: Word) -> list[list[float]]:
    """
    Convert a word into a List of Lists, one list per syllable. Each list
    contains a value for Onset, Nucleus, Coda and Prosody, which are all in
    [0,1].

    Args:
        w (rhyme.Word): Word to convert

    Returns:
        List[List[float]]: the result.
    """
    syls = re.findall(re.compile(".."), str(w.mqdq["sy"]))
    final = []
    for i, s in enumerate(syls):

        # Since we enumerate the MQDQ syllable string, we shouldn't get any
        # empty syllables (lost by elision) which can appear in my +syls+ List
        # in the Word object.

        # Get the prosody layer as a single number by combining binary flags. In
        # order of importance: Long, Elision, CM, DI, CF, Ictus, Accent.
        meta = 0
        if i == w.stress_idx:
            # Accent
            meta |= 0b1
        if s[1] == "A":
            # Ictus
            meta |= 0b10
        if s[1].isupper():
            # Long
            meta |= 0b1000000
        if i == len(syls) - 1:
            if w.mqdq.has_attr("wb"):
                # Assorted word breaks, which can appear in the last syl only
                if w.mqdq["wb"] == "CM":
                    meta |= 0b10000
                elif w.mqdq["wb"] == "DI":
                    meta |= 0b1000
                elif w.mqdq["wb"] == "CF":
                    meta |= 0b100
            if w.mf == "SY":
                # Elision
                meta |= 0b100000
        # normalise to [0,1] (max possible value here since SY, CM CF and DI are
        # mutually exclusive)
        metaf = meta / 0b1100011

        onc = []
        for meth in ["onset", "nucleus", "coda"]:
            onc.append(getattr(w.syls[i], meth).translate(rhyme.DEFANCY).lower())
        onc.append(metaf)
        onc[0], onc[2] = _locate(onc[0], CONS_SPACE), _locate(onc[2], CONS_SPACE)
        onc[1] = _locate(onc[1], VOWEL_SPACE)

        final.append(onc)
    return final


def _flatten(t: Iterable) -> list:
    return [item for sublist in t for item in sublist]


def compact_layers(l: Line) -> np.ndarray:
    """
    Produce a matrix from a rhyme.Line using +syl_meta+. The final array is 4 x
    num_syls.

    Args:
        l (rhyme.Line): line to operate on

    Returns:
        numpy.ndarray: The result
    """
    try:
        ary = [_syl_meta(w) for w in l]
    except Exception as e:
        print("Problem with this line: %s" % l)
        raise e

    mtrx = np.array(_flatten(ary))
    return mtrx.transpose()


XX = re.compile("..")


def loose_layers(l: Line) -> np.ndarray:
    """
    Convert a line into a List of Lists, one list per syllable. In this
    experiment we will stay metronized (12 metrons) but record the onset and
    coda of the metron, and also use three layers for prosody, pauses
    (bitfield), length and elision (binary), for a final layer count of 6

    Args:
        l (rhyme.Line): Line to convert

    Returns:
        np.ndarray: the result.
    """
    final = []
    nuc = ""
    onset = ""
    cf = syn = long = pause = 0b0
    for w in l:
        syls = re.findall(XX, str(w.mqdq["sy"]))
        for i, s in enumerate(syls):

            # Since we enumerate the MQDQ syllable string, we shouldn't get any
            # empty syllables (lost by elision) which can appear in my +syls+ List
            # in the Word object.

            if s[1] != "c":
                # we lose the onset of the second breve in uu. That metron
                # becomes the onset of the first, then both vowels then the coda
                # of the second.
                onset = w.syls[i].onset.translate(rhyme.DEFANCY).lower()
            if (s[1] == "A" and not i == w.stress_idx) or (
                i == w.stress_idx and not s[1] == "A"
            ):
                # Ictus / Accent Conflict
                cf = 0b1
            if s[1].isupper():
                # Long
                long = 0b1

            if i + 1 == len(syls):
                # end of a word. Because these are OR'd it's possible for a
                # metron with two breves to contain two pauses (eg CM and CF).
                if w.mqdq.has_attr("wb"):
                    if w.mqdq["wb"] == "CM":
                        pause |= 0b100
                    elif w.mqdq["wb"] == "DI":
                        pause |= 0b10
                    elif w.mqdq["wb"] == "CF":
                        pause |= 0b1
                if w.mf == "SY":
                    # Elision aka synalepha
                    syn = 0b1

            nuc += w.syls[i].nucleus.translate(rhyme.DEFANCY).lower()
            # if it's the first breve in a dactyl we don't write out a metron
            # yet, otherwise we're done
            if s[1] != "b":
                # If in 'ATX' it's a metron by itself, if it's 'c' it's the end
                # of a metron. Either way it's time to write out this metron.

                coda = w.syls[i].coda.translate(rhyme.DEFANCY).lower()
                final.append(
                    [
                        _locate(onset, CONS_SPACE),
                        _locate(nuc, VOWEL_SPACE),
                        _locate(coda, CONS_SPACE),
                        long,
                        # splat the pause bitstring into 3 binary layers
                        *[int(x) for x in list(format(pause, "03b"))],
                        cf,
                        syn,
                    ]
                )
                # print("W:", "%1s" % onset, nuc, "%1s" % coda, "\t", bin(long), format(pause,'03b'), bin(cf), bin(syn), w.syls[i], w.mqdq)
                nuc = ""
                onset = ""
                cf = syn = long = pause = 0b0
            else:
                # print("..", "%1s" % onset, nuc, "%1s" % coda, "\t", bin(long), format(pause,'03b'), bin(cf), bin(syn), w.syls[i], w.mqdq)
                pass

    return np.array(final).transpose()


# more efficient to break this out as a method so we can pad in a list comp.
def _pad(m: np.ndarray, layers: int, pad_left: int, pad_right: int) -> np.ndarray:
    pre = np.zeros((layers, pad_left))
    post = np.zeros((layers, pad_right - m.shape[1]))
    return np.concatenate([pre, m, post], axis=1)


def lines_to_tensor(
    syl_lines: Iterable[Line],
    line_mapper: Callable[[Line], np.ndarray] = compact_layers,
    pad_right: int = 18,
    pad_left: int = 2,
) -> np.ndarray:
    """
    Convert an enumerable of rhyme.Lines to a tensor using +syl_meta+. The final
    tensor contains four layers, one layer for each of Onset, Nucleus, Coda and
    Prosody. Each layer is of shape (len(syl_lines), pad_left+pad_right). The
    final numpy.ndarray should be suitable for building a tf tensor.

    Args:
        syl_lines (enum of rhyme.Line): Lines to operate on

        pad_right (int=18): right pad with zeroes to this width. The final width
            will be pad_left+pad_right. Note that pad_right must be >= the width
            in syallables of the longest line in syl_lines. Default: 18 (since
            the longest legal hexameter line is 17 syllables, with the pattern
            DDDDDS)

        pad_left (int=2): left pad each layer with this many zeroes

    Returns:
        numpy.ndarray: final shape (len(syl_lines), pad_left+pad_right, 4)
    """
    mxx = [line_mapper(l) for l in syl_lines]
    longest = max([mx.shape[1] for mx in mxx])
    n_layers = mxx[0].shape[0]
    if longest > pad_right:
        raise ValueError("right pad width is less than longest line!")

    # The syllable arrays might be ragged right, so pad them right to form a
    # rectangle. This should be based on the longest line in the entire input
    # universe, not just the longest line in this set of lines (although that's
    # the only thing we can check here). We should add some left padding as well
    # so that the first syllable gets used more than once by the convolutional
    # layers.
    mxx_padded = [_pad(mx, n_layers, pad_left, pad_right) for mx in mxx]
    # Now concatenate all the lines and split out each kind of row to form
    # n_layers layers
    full_df = np.concatenate(mxx_padded)
    layers = []
    for i in range(n_layers):
        # [i::n] is pandas notation - start at i, take every n rows
        layers.append(full_df[i::n_layers].copy())
    # finally, stack the n layers 'backwards' to make the final proto-tensor of
    # shape lines (long) x pad_width (wide) x n_layers (deep). In Tensorflow CNN
    # lingo this is 'channels last'
    return np.stack(layers, axis=-1)

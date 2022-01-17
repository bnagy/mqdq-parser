from mqdq import line_analyzer as la
from mqdq import utils
from mqdq import rhyme_classes

import pandas as pd
import scipy as sp
import copy


def metre_vectors(bab):

    """Take a Babbler for an elegiac work and return a Pandas
    Dataframe containing the metrical features. The features
    are broadly the same as +line_analyzer.BINARY_FEATURES+ (cf)
    but each feature is preceded by 'H' or 'P' for hexameter and
    pentameter. Some features are dropped because they are useless
    eg P3SP (the third foot of a Pentameter is a mandatory dactyl)

    Args:
        bab (babble.Babbler): The Babbler to operate on

    Returns:
        (pandas.DataFrame): The results, one per row, with column names
                            matching the predefined features
    """

    if not bab.elegiac:
        raise ValueError("Error: Babbler is not elegiac.")
    if len(bab) % 2 != 0:
        raise ValueError("Error: Length of work (%d) is not even!" % len(bab))

    df = pd.DataFrame(map(lambda l: la.binary_features(l), bab.raw_source))
    # split into even and odd lines. Probably a slicker way to do this?
    even = df[df.index % 2 == 0]
    odd = df[df.index % 2 == 1]
    even.columns = ["H" + x for x in la.BINARY_FEATURES]
    odd.columns = ["P" + x for x in la.BINARY_FEATURES]
    # If we don't have matching indices they won't concatenate column-wise
    even.reset_index(inplace=True, drop=True)
    odd.reset_index(inplace=True, drop=True)
    # Concat the Hexameter features and Pentameter features sideways to
    # make a wide vector.
    # No information in the foot pattern for the last two feet of
    # the Pentameter, so we drop those columns.
    return pd.concat([even, odd], axis=1).drop(["P3SP", "P4SP"], axis=1)


# Slightly different to the version in +rhyme_classes+ - the rhymes only
# extend 2 lines instead of three, ie we won't consider a rhyme between
# a hexameter and the pentameter in the next couplet. For continuous
# hexameters a span of 3 is best because it picks up quatrain moasaics
VERTICAL_INIT = {
    0: [(0, 2)],
    -1: [("mid", 0), (-1, 2)],
    -2: [(-2, 2)],
    "mid": [("mid", 2)],
}

LEO = {"mid": [(-1, 0)]}


def elegy_vector(bab):

    """Take a Babbler for an elegiac work and return a Pandas
    Dataframe containing the poetic features. The metrical features
    are broadly the same as +line_analyzer.BINARY_FEATURES+ (cf)
    but each feature is preceded by 'H' or 'P' for hexameter and
    pentameter. Some features are dropped because they are useless
    eg P3SP (the third foot of a Pentameter is a mandatory dactyl)

    The rest of the features are 'whole work' features, and are:
        - LEO: Count of Leonine rhymes (per-line)
        - ELC: Elision count (per-line)
        - RS: Rhyme Strength. The per-line rhyme score
                        (see +rhyme_classes.LineSet.score+)
        - PFSD: The standard deviation in the number of syllables
                        of the final word in the pentameter (traditionally two
                        but some authors are more punctilious than others)
        - LEN: The number of lines in the work

    Args:
        bab (babble.Babbler): The Babbler to operate on

    Returns:
        (pandas.DataFrame): The results, one per row, with column names
                            matching the predefined features
    """

    wide_df = metre_vectors(bab)
    chunked_feats = la._chunk_mean(wide_df, len(wide_df))

    # Now do full-work features

    elisions = [la.elision_count(l) for l in bab.raw_source]
    chunked_feats["ELC"] = sum(elisions) / len(elisions)
    cl = copy.copy(bab._syl_source())
    cl.colorlink(config=VERTICAL_INIT)
    s = cl.score(config=rhyme_classes.LineSet.NEUTRAL)
    chunked_feats["RS"] = s
    cl = copy.copy(bab._syl_source())
    cl.colorlink(config=LEO)
    leo = cl.score(config=rhyme_classes.LineSet.NEUTRAL)
    chunked_feats["LEO"] = leo
    chunked_feats["LEN"] = len(cl)
    pent_finals = [la.word_idx_syls(l, -1) for l in bab.raw_source if l["metre"] == "P"]
    chunked_feats["PFSD"] = sp.std(pent_finals)
    return chunked_feats


def vectorise_babs(babs):

    """Create a DataFrame containing the +elegy_vector+ (cf) of several
    Babblers.

    Args:
        babs (enumerable of babble.Babbler): Babblers to convert

    Returns:
        (pandas.DataFrame): The results, one per row, with column names
                            matching the predefined features
    """

    vecs = []
    for b in babs:
        v = elegy_vector(b)
        v.insert(0, "Poem", b.name)
        v.insert(0, "Work", b.name.split(" ")[0])
        if hasattr(b, "author"):
            v.insert(0, "Author", b.author)
        vecs.append(v)
    df = pd.concat(vecs)
    df.reset_index(drop=True, inplace=True)
    return df

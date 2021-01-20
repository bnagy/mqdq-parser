import bs4
from bs4 import BeautifulSoup
from collections import Counter, Iterable
import re
import numpy as np
import pandas as pd
from mqdq import line_analyzer as la
from mqdq import rhyme
import unicodedata
import bisect

import dominate
from IPython.core.display import display, HTML

DEFANCY = str.maketrans(
    {"ü": "y", u"\u0304": None, u"\u0303": None, "`": None, "_": None}
)


def slup(fn):
    with open(fn) as fh:
        soup = bs4.BeautifulSoup(fh, "xml")
        ll = clean(soup("line"))
    return soup, ll


def grep(soup, s):

    """Case insensitive grep on the text contents of bs4 soup object.

    Args:
        soup (bs4 soup): The text in which to search
        s (string): String to search for. This will be converted
                    into a regular expression, so re characters
                    are allowed.

    Returns:
        (list): a list of matching bs4 <line>s
    """

    # TODO this is word by word only! Rewrite to get some kind of
    # at least line-by-line search

    r = re.compile(s, re.IGNORECASE)
    return list(set(s.parent.parent for s in soup.find_all(string=r)))


def blat(ll, scan=True, phon=False, number_with=None):

    """Quickly print the text of a set of lines to screen

    Args:
        ll (list of bs4 <line>): Lines to print
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X
    Returns:
        Nothing (the lines are printed)
    """

    # if they give us just one line instead of wrapping it
    # in a list as they should then be nice to them
    if ll.__class__ == bs4.element.Tag:
        ll = [ll]

    print("\n\n".join([txt(l, scan, phon, number_with) for l in ll]))


def blatsave(ll, fn, scan=True, phon=False, number_with=None):

    """Quickly write the text of a set of lines to a file.
    Opens filename with mode 'w' (will truncate and overwrite).
    Exceptions are left to the caller.

    Args:
        ll (list of bs4 <line>): Lines to write
        fn (String): filename to write to
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, fo
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X

        Returns:
            Nothing (the lines are written)
    """

    with open(fn, "w") as fh:
        fh.write("\n\n".join([txt(l, scan, phon, number_with) for l in ll]))


def txt(l, scan=False, phon=False, number_with=None):

    """Extract the text from a (single) line.

    Args:
        l (bs4 <line>): Line to operate on
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X WSQ
    Returns:
        (string): The result. Because of the internal de-duping, the results are not sorted.
    """

    try:

        words = l("word")

        l_prefix = ""
        scan_prefix = ""
        if number_with:
            l_prefix = bookref(l, number_with) + "> "
            padding = " " * len(l_prefix)

        if l["pattern"] == "corrupt" or l["pattern"] == "not scanned":
            return (
                l_prefix
                + " ".join([w.text for w in l("word")])
                + "\n"
                + " " * len(l_prefix)
                + "[corrupt]"
            )

        ph = raw_phonetics(l)
        syls = raw_scansion(l)
        words = [w.text for w in l("word")]

        if number_with:
            words = [l_prefix] + words
            syls = [padding] + syls
            ph = [padding] + ph

        ll = [words]

        if phon:
            ll.append(ph)
        if scan:
            ll.append(syls)

        return _align(*ll)

    except:
        raise ValueError("Can't handle this: %s" % l)


def raw_scansion(l):
    return [la._get_syls_with_stress(w) for w in l("word")]


def raw_phonetics(l):
    return [
        w.pre_punct + ".".join(w.syls) + w.post_punct for w in rhyme.syllabify_line(l)
    ]


def raw_phonemics(l):
    return ["".join(w.syls).lower().translate(DEFANCY) for w in rhyme.syllabify_line(l)]


def _align(*ll):

    # align a list of lists of strings
    ss = ["" for l in ll]
    # each list needs the same number of elements
    if len(set([len(l) for l in ll])) > 1:
        raise ValueError("Can't align, lengths not equal.")

    # make the scan and the words line up, depending on which is longer.
    zipped = zip(*ll)
    for tupl in zipped:
        # need special magic to get length with combining unicode macrons
        lens = [sum(1 for ch in x if unicodedata.combining(ch) == 0) for x in tupl]
        maxl = max(lens)
        for idx, s in enumerate(tupl):
            ss[idx] = ss[idx] + s + " " * (maxl - lens[idx]) + " "

    return "\n".join([s.rstrip() for s in ss])


def txt_and_number(ll, every=5, scan=False, phon=False, start_at=1):

    """Extract the text from a list of lines, with numbers. Where `txt` uses references to the text,
    this uses independent numbers. Use this method if you want to print out a sequentially numbered
    extract. Use `txt` if you want to add book refs to the result of a search or a random sample.

    Args:
        ll (list of bs4 <line>): Lines to operate on
        every (int, default=5): How often to add numbers
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        start_at (int, default=1): Where to start the numbering

    Returns:
        (string): The result
    """

    # the string length of the highest line number (100==3)
    n_len = len(str(len(ll) + start_at))
    pad = " " * (n_len + 2)
    strs = [txt(l, scan, phon).split("\n") for l in ll]
    numbered = []
    for idx, ss in enumerate(strs):
        if (idx + start_at) % every == 0:
            ss[0] = ("%*d  " % (n_len, idx + start_at)) + ss[0]
            ss[1:] = [pad + s for s in ss[1:]]
        else:
            ss = [pad + s for s in ss]
        numbered.append("\n".join(ss))

    return numbered


def which_book(l, soup):

    """Determine which book in a bs4 soup contains a given line.

    Args:
        l (bs4 <line>): Line to check
        soup (bs4 soup): Soup to check in

    Returns:
        (int): The index of the first 'division' containing l (0-based) or None
    """

    for d in soup("division"):
        if l in d:
            return d["title"]
    return None


def by_ref(bn, ln, soup):
    b = soup("division")[bn - 1]
    return b("line")[ln - 1]


def bookref(l, soup):

    """Return a formatted reference book:line for a given line and text.

    Args:
        l (bs4 <line): Line to use
        soup (bs4 soup): Text to use for the numbering

    Returns:
        (string): The reference, eg 6:825 or None
    """

    b = which_book(l, soup)
    if not b:
        return None
    return "%2s:%-3d" % (b, int(l["name"]))


def bookrange(ll, soup):
    ll = list(ll)
    b1, l1 = bookref(ll[0], soup).split(":")
    b2, l2 = bookref(ll[-1], soup).split(":")
    if b2 == b1:
        b2 = ""
    else:
        b2 = b2 + ":"
    return "--".join([x.strip() for x in ["%s:%s" % (b1, l1), "%s%s" % (b2, l2)]])


def clean(ll):

    """Remove all corrupt lines from a set of bs4 <line>s

    Args:
        ll (list of bs4 <line>): Lines to clean

    Returns:
        (list of bs4 <line>): The lines, with the corrupt ones removed.
    """

    return [
        l
        for l in ll
        if l.has_attr("pattern")
        and l["pattern"] != "corrupt"
        and l["pattern"] != "not scanned"
    ]


def indices_to_bookref(soup, rr):

    # parsing the soup is slow, so do it once
    cumsums = np.cumsum([len(d("line")) for d in soup("division")])
    # allow single refs as rr, with some hackery
    if not isinstance(rr, Iterable):
        rr = [rr]

    res = []
    for ref in rr:
        # finds leftmost value greater than idx
        insert_at = bisect.bisect_right(cumsums, ref)
        if insert_at >= len(cumsums):
            raise IndexError("Line index out of range")
        br = insert_at + 1
        lr = ref
        if insert_at > 0:
            lr = lr - cumsums[insert_at - 1]
        res.append((br, lr))
    if len(res) == 1:
        return res[0]
    return res


def slurp(fn):
    with open(fn) as fh:
        soup = BeautifulSoup(fh, "xml")
        ll = clean(soup("line"))
    return soup, ll


def bookinate(fn):
    with open(fn) as fh:
        soup = BeautifulSoup(fh, "xml")
    return [clean(d("line")) for d in soup("division")]


def _bloop(s):
    display(HTML(s.render()))


def _make_p(l, font="Times", size="small", indent=True, book=False, line=False):

    # CSS style for words that will have a background colour
    setbg = """
    background-color: %s;
    padding-right: 0.25em;
    padding-left: 0.25em;
    padding-bottom: 0.08em;
    color: black;
    border-radius: 4px
    """

    parastyle = """
    line-height: 1.4;
    margin-top: 0;
    margin-bottom: 0;
    font-family: %s;
    font-size: %s"
    """

    para = dominate.tags.p(style=parastyle % (font, size))
    if book:
        try:
            bn = l[0].mqdq.parent.parent["title"]
        except KeyError:
            bn = None
        line = int(re.sub("[^0-9]", "", l[0].mqdq.parent["name"]))
        if bn:
            para += dominate.tags.span(
                "%2s:%-4s" % (bn, line), style="float: left; width: 5em"
            )
        else:
            para += dominate.tags.span("%-4s" % line, style="float: left; width: 3em")
    elif line:
        line = int(re.sub("[^0-9]", "", l[0].mqdq.parent["name"]))
        para += dominate.tags.span("%-4s" % (line), style="float: left; width:4em")

    if l.metre == "P" and indent:
        para += dominate.tags.span("", style="padding-right: 1.5em")
    for w in l:
        if w.color:
            para += dominate.tags.span(w.mqdq.text, style=setbg % w.color)
        else:
            para += dominate.tags.span(w.mqdq.text)
    return para


def _make_d(ll, font="Times", size="small", indent=True, book=False, line=False):
    d = dominate.document()
    for l in ll:
        d += _make_p(l, font, size, indent, book, line)
    return d


def nbshow(ll, indent=True, book=False, line=False):
    _bloop(_make_d(ll, "Envy Code R", "medium", indent, book, line))

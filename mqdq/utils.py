import bs4
from bs4 import BeautifulSoup
from bs4.element import Tag
import re
import numpy as np
import pandas as pd
from typing import Optional, Union, cast
from mqdq import line_analyzer as la
from mqdq import rhyme
from mqdq.rhyme_classes import Line
import unicodedata
import bisect

import dominate
from dominate import tags
from IPython.core.display import HTML
from IPython.display import display
from mqdq.rhyme_classes import LineSet

DEFANCY = str.maketrans(
    {"ü": "y", "\u0304": None, "\u0303": None, "`": None, "_": None}
)


def grep(soup: BeautifulSoup, s: str) -> list[Tag]:
    """
    Case insensitive grep on the text contents of BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The text in which to search
        s (str): String to search for. This will be converted
                    into a regular expression, so re characters
                    are allowed.

    Returns:
        list[bs4.element.Tag]: a list of matching bs4.element.Tags
    """

    # TODO this is word by word only! Rewrite to get some kind of
    # at least line-by-line search

    r = re.compile(s, re.IGNORECASE)
    return list(set(s.parent.parent for s in soup.find_all(string=r)))


def blat(
    ll: list[Tag],
    scan: bool = False,
    phon: bool = False,
    number_with=None,
):
    """
    Quickly print the text of a set of lines to screen

    Args:
        ll (list of bs4.element.Tag): Lines to print
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        number_with (BeautifulSoup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X
    Returns:
        Nothing (the lines are printed)
    """

    print("\n\n".join([txt(l, scan, phon, number_with) for l in ll]))


def blatsave(
    ll: list[Tag],
    fn: str,
    scan: bool = False,
    phon: bool = False,
    number_with: Optional[BeautifulSoup] = None,
):
    """
    Quickly write the text of a set of lines to a file.
    Opens filename with mode 'w' (will truncate and overwrite).
    Exceptions are left to the caller.

    Args:
        ll (list of bs4.element.Tag): Lines to write
        fn (str): filename to write to
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        number_with (BeautifulSoup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, fo
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X

        Returns:
            Nothing (the lines are written)
    """

    with open(fn, "w") as fh:
        fh.write("\n\n".join([txt(l, scan, phon, number_with) for l in ll]))


def txt(
    l: Tag,
    scan: bool = False,
    phon: bool = False,
    number_with: Optional[BeautifulSoup] = None,
) -> str:
    """
    Extract the text from a (single) line.

    Args:
        l (bs4.element.Tag): Line to operate on
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        number_with (BeautifulSoup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X WSQ
    Returns:
        str: The result. Because of the internal de-duping, the results are not sorted.
    """

    try:
        words = l("word")

        l_prefix = ""
        padding = ""
        if number_with:
            l_prefix = str(bookref(l, number_with)) + "> "
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


def raw_scansion(l: Tag) -> list[str]:
    return [la._get_syls_with_stress(w) for w in l("word")]


def raw_phonetics(l: Tag) -> list[str]:
    return [
        w.pre_punct + ".".join(w.syls) + w.post_punct for w in rhyme.syllabify_line(l)
    ]


def raw_phonemics(l: Tag) -> list[str]:
    return ["".join(w.syls).lower().translate(DEFANCY) for w in rhyme.syllabify_line(l)]


def _align(*ll: list[str]) -> str:
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


def txt_and_number(
    ll: list[Tag],
    every: int = 5,
    scan: bool = False,
    phon: bool = False,
    start_at: int = 1,
) -> list[str]:
    """
    Extract the text from a list of lines, with numbers. Where `txt` uses references to the text,
    this uses independent numbers. Use this method if you want to print out a sequentially numbered
    extract. Use `txt` if you want to add book refs to the result of a search or a random sample.

    Args:
        ll (list of bs4.element.Tag): Lines to operate on
        every (int, default=5): How often to add numbers
        scan (bool, default=False): Include scansion codes
        phon (bool, default=False): Include phonetic transcription
        start_at (int, default=1): Where to start the numbering

    Returns:
        str: The result
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


def which_book(l: Tag, soup: BeautifulSoup) -> Union[str, None]:
    """
    Determine which book in a BeautifulSoup contains a given line.

    Args:
        l (bs4.element.Tag): Line to check
        soup (BeautifulSoup): Soup to check in

    Returns:
        str: The string title (usually a number) of the first 'division'
        containing l (0-based) or None
    """

    for d in soup("division"):
        if l in d:
            return d["title"]
    return None


def by_ref(bn: int, ln: int, soup: BeautifulSoup) -> Union[Tag, None]:
    try:
        b = soup("division")[bn - 1]
        return b("line")[ln - 1]
    except IndexError:
        return None


def bookref(l: Tag, soup: BeautifulSoup) -> Union[str, None]:
    """
    Return a formatted reference book:line for a given line and text.

    Args:
        l (bs4.element.Tag): Line to use
        soup (BeautifulSoup): Text to use for the numbering

    Returns:
        str: The reference, eg 6:825 or None
    """

    b = which_book(l, soup)
    if not b:
        return None
    return "%2s:%-3d" % (b, int(str(l["name"])))


def bookrange(ll: list[Tag], soup: BeautifulSoup) -> str:
    if bookref(ll[0], soup) == None:
        # no books or something
        return ""
    b1, l1 = str(bookref(ll[0], soup)).split(":")
    b2, l2 = str(bookref(ll[-1], soup)).split(":")
    if b2 == b1:
        b2 = ""
    else:
        b2 = b2 + ":"
    return "--".join([x.strip() for x in ["%s:%s" % (b1, l1), "%s%s" % (b2, l2)]])


def _build_hex_pattern(syls: str) -> str:
    pattern = ""
    for i in range(4):
        if syls.count(str(i + 1)) == 2:
            pattern += "S"
        elif syls.count(str(i + 1)) == 3:
            pattern += "D"
        else:
            raise ValueError(f"Unknown foot in {syls}")
    return pattern


def _build_pent_pattern(syls: str) -> str:
    pattern = ""
    for i in ["1", "2", "4", "5"]:
        if syls.count(i) == 2:
            pattern += "S"
        elif syls.count(i) == 3:
            pattern += "D"
        else:
            raise ValueError(f"Unknown foot in {syls}")
    pattern = pattern[:2] + "-|" + pattern[2:] + "-"
    return pattern


def _build_pattern(syls: str) -> str:
    try:
        if syls.count("3") == 1:
            # pentameter, because the 'half foot' at the caesura has only one syllable
            return _build_pent_pattern(syls)
        else:
            return _build_hex_pattern(syls)
    except Exception as e:
        raise e


def fix_meters(ll: list[Tag]) -> None:
    """
    For "free scansions" from Pedecerto, elegiac couplets have all the meters set to 'E' instead of
    alternating H and P. This fixes that, and also adds the line pattern, which is not filled in in
    that output

    Args:
        ll (list[bs4.element.Tag]): Lines to fix meters

    Returns:
        nothing (modifies the lines and their containing soup in-place)
    """
    for l in ll:
        ww = l.find_all("word")
        syl = "".join([w["sy"] for w in ww])
        # inconsistency between meter and metre, force the latter
        if l.has_attr("meter"):
            del l["meter"]

        if "6A6X" in syl:
            l["metre"] = "H"
        elif "6A" not in syl:
            l["metre"] = "P"
        else:
            raise ValueError(f"Cannot determine meter type: {l})")

        try:
            l["pattern"] = _build_pattern(syl)
        except ValueError as ve:
            raise ValueError(f"Error processing line {l}: {ve}")


def clean(ll: list[Tag]) -> list[Tag]:
    """
    Remove all corrupt lines from a list of MQDQ bs4 lines

    Args:
        ll (list[bs4.element.Tag]): Lines to clean

    Returns:
        list[bs4.element.Tag]: The lines, with the corrupt ones removed.
    """

    ll = [
        l
        for l in ll
        if l.has_attr("pattern")
        and l["pattern"] != "corrupt"
        and l["pattern"] != "not scanned"
    ]

    # pedecerto free scansion of elegy
    if ll[0].has_attr("meter") and ll[0]["meter"] == "E":
        fix_meters(ll)

    return ll


def indices_to_bookref(soup: BeautifulSoup, rr: list[int]) -> list[tuple[int, int]]:
    # parsing the soup is slow, so do it once.
    # get the starting points of each book
    cumsums = list(np.cumsum([len(d("line")) for d in soup("division")]))
    res = []
    for ref in rr:
        # finds leftmost start value greater than idx
        insert_at = bisect.bisect_right(cumsums, ref)
        if insert_at >= len(cumsums):
            raise IndexError("Line index out of range")
        br = insert_at + 1
        lr = ref
        if insert_at > 0:
            # line idx in book is overall idx - start_of_book idx
            lr = lr - cumsums[insert_at - 1]
        res.append((br, lr))
    return res


def chunk_lines(
    ll: list[Tag],
    sz: int,
    step: int,
    name: str = "",
    author: str = "",
    strict: bool = True,
) -> pd.DataFrame:
    if step > sz:
        raise ValueError("Step cannot be greater than chunksize.")
    chunk_ary = []
    br_ary = []
    for idx in range(0, len(ll) - step, step):
        chunk = ll[idx : idx + sz]
        if len(chunk) < sz and strict:
            break
        chunk_ary.append(chunk)
        try:
            # apparently impossible to convince Pylance that I'm dealing with
            # the possibility that parent name might not exist
            if ll[idx].parent.name == "division":  # type: ignore
                book = str(ll[idx].parent["title"])  # type: ignore
            else:
                book = ""
            ln = str(ll[idx]["name"])
            br = book + ":" + ln
        except KeyError:
            br = "<??>"
        br_ary.append(br)

    df = pd.DataFrame()
    df["Chunk"] = chunk_ary
    df["Bookref"] = br_ary
    if name:
        df["Work"] = name
    if author:
        df["Author"] = author

    return df


def slurp(fn: str) -> tuple[BeautifulSoup, list[Tag]]:
    with open(fn) as fh:
        soup = BeautifulSoup(fh, "xml")
        ll = clean(soup("line"))
    return soup, ll


def bookinate(fn: str) -> list[list[Tag]]:
    with open(fn) as fh:
        soup = BeautifulSoup(fh, "xml")
    return [clean(d("line")) for d in soup("division")]


def _bloop(s: dominate.document):
    display(HTML(s.render()))


def _make_p(
    l: Line,
    font: str = "Times",
    size: str = "small",
    indent=True,
    book=False,
    line=False,
) -> tags.p:
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

    para = tags.p(style=parastyle % (font, size))
    if book:
        try:
            bn = l[0].mqdq.parent.parent["title"]
        except KeyError:
            bn = None
        line = int(re.sub("[^0-9]", "", l[0].mqdq.parent["name"]))
        if bn:
            para += tags.span("%2s:%-4s" % (bn, line), style="float: left; width: 5em")
        else:
            para += tags.span("%-4s" % line, style="float: left; width: 3em")
    elif line:
        line = int(re.sub("[^0-9]", "", l[0].mqdq.parent["name"]))
        para += tags.span("%-4s" % (line), style="float: left; width:4em")

    if l.metre == "P" and indent:
        para += tags.span("", style="padding-right: 1.5em")
    for w in l:
        if w.color:
            para += tags.span(w.mqdq.text, style=setbg % w.color)
        else:
            para += tags.span(w.mqdq.text)
    return para


def _make_d(
    ll: list[Line],
    font: str = "Times",
    size: str = "small",
    indent: bool = True,
    book: bool = False,
    line: bool = False,
) -> dominate.document:
    d = dominate.document()
    for l in ll:
        d += _make_p(l, font, size, indent, book, line)
    return d


def nbshow(ll: list[Line], indent: bool = True, book: bool = False, line: bool = False):
    _bloop(_make_d(ll, "Envy Code R", "medium", indent, book, line))

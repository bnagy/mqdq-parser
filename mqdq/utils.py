from bs4 import BeautifulSoup
from collections import Counter
import re
import numpy as np
import pandas as pd
from mqdq import line_analyzer as la
from mqdq import rhyme
import unicodedata

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


def blat(ll, scan=True, number_with=None):

    """Quickly print the text of a set of lines to screen

    Args:
        ll (list of bs4 <line>): Lines to print
        scan (bool): if True, add scansion (see `txt`)
        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X
    Returns:
        Nothing (the lines are printed)
    """

    print("\n\n".join([txt(l, scan, number_with) for l in ll]))

def blatsave(ll, fn, scan=True, number_with=None):

    """Quickly write the text of a set of lines to a file.
    Opens filename with mode 'w' (will truncate and overwrite).
    Exceptions are left to the caller.

    Args:
        ll (list of bs4 <line>): Lines to write
        fn (String): filename to write to
        scan (bool): if True, add scansion (see `txt`)
        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X

        Returns:
            Nothing (the lines are written)
    """

    with open(fn, 'w') as fh:
        fh.write("\n\n".join([txt(l, scan, number_with) for l in ll]))

def txt(l, scan=False, number_with=None):

    """Extract the text from a (single) line.

    Args:
        l (bs4 <line>): Line to operate on
        scan (bool): If True, add a line of scansion and accent:
                     Dixerat, atque illam media  inter talia   ferro
                     1A'1b1c  2A'_  2T'3A 3b'3c_ 4A'4T 5A'5b5c 6A'6X

        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X WSQ
    Returns:
        (string): The result. Because of the internal de-duping, the results are not sorted.
    """

    res = []

    try:
            
        words = l('word')

        l_prefix = ''
        scan_prefix = ''
        if number_with:
            l_prefix = bookref(l, number_with) + '> '
            scan_prefix = ' '*len(l_prefix)

        res=[]
        if not scan:
            return l_prefix + ' '.join([w.text for w in l('word')])
        if l['pattern']=='corrupt' or l['pattern']=='not scanned':
            return l_prefix + ' '.join([w.text for w in l('word')]) + "\n" + scan_prefix + "[corrupt]"

        for w in words:
            if len(w['sy'])==0:
                if w.text:
                    # There are two cases that go here. One is prodelision, where
                    # curae est -> cur'est and normal elision with a single syllable
                    # word eg cum aspicerem -> c'aspicerem (so 'cum' ends up
                    # with no syllables.
                    res.append(['_',w.text])
                    continue
            syls = la._get_syls_with_stress(w)
            if la._has_elision(w):
                res.append([syls+'_',w.text])
            else:
                res.append([syls,w.text])
            
    except:
        raise ValueError("Can't handle this: %s" % l)
    
    s1, s2='',''
    # make the scan and the words line up, depending on which is longer.
    for syls,txt in res:
        if len(txt)>=len(syls):
            s1 += txt + ' '
            s2 += syls + ' '*(len(txt) - len(syls) + 1)
        else:
            s1 += txt + ' '*(len(syls) - len(txt) + 1)
            s2 += syls + ' '
    
    return (l_prefix + s1.strip() + '\n' + scan_prefix + s2.strip())

def phonetic(l, number_with=None):

    res = []

    try:
            
        words = l('word')

        l_prefix = ''
        scan_prefix = ''
        if number_with:
            l_prefix = bookref(l, number_with) + '> '
            scan_prefix = ' '*len(l_prefix)

        res=[]
        if l['pattern']=='corrupt' or l['pattern']=='not scanned':
            return l_prefix + ' '.join([w.text for w in l('word')]) + "\n" + scan_prefix + "[corrupt]"

        res = zip([w.text for w in words], rhyme.syllabify_line(l).split(' '))
            
    except:
        raise ValueError("Can't handle this: %s" % l)
    
    s1, s2='',''
    # make the scan and the words line up, depending on which is longer.
    for a,b in res:
        blen = sum(1 for ch in b if unicodedata.combining(ch) == 0)
        if len(a)>=blen:
            s1 += a + ' '
            s2 += b + ' '*(len(a) - blen) + ' '
        else:
            s1 += a + ' '*(blen - len(a)) + ' '
            s2 += b + ' '
    
    return (l_prefix + s1.strip() + '\n' + scan_prefix + s2.strip())

def txt_and_number(ll, every=5, scan=False, start_at=1):
    
    """Extract the text from a list of lines, with numbers. Where `txt` uses references to the text,
    this uses independent numbers. Use this method if you want to print out a sequentially numbered
    extract. Use `txt` if you want to add book refs to the result of a search or a random sample.

    Args:
        ll (list of bs4 <line>): Lines to operate on
        every (int, default=5): How often to add numbers
        start_at (int, default=1): Where to start the numbering

    Returns:
        (string): The result
    """

    # the string length of the highest line number (100==3)
    n_len = len(str(len(ll)+start_at))
    strs = [txt(l,scan) for l in ll]
    numbered = []
    for idx, s in enumerate(strs):      
        if scan:
            s1, s2 = s.splitlines()
            if (idx+start_at)%every==0:
                s1 = ("%*d  " % (n_len,idx+start_at)) + s1
            else:
                s1 = ' '*(n_len+2) + s1
            s2 = ' '*(n_len+2) + s2
            numbered.append('\n'.join([s1,s2]))
        else:
            if (idx+start_at)%every==0:
                s = ("%*d  " % (n_len,idx+start_at)) + s
            else:
                s = ' '*(n_len+2) + s
            numbered.append(s)

    return numbered

def which_book(l, soup):

    """Determine which book in a bs4 soup contains a given line.

    Args:
        l (bs4 <line>): Line to check
        soup (bs4 soup): Soup to check in

    Returns:
        (int): The index of the 'division' containing l (0-based) or None
    """

    for d in soup('division'):
        if l in d:
            return d['title']
    return None

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
    return("%2s:%-3d" % (b, int(l['name'])))

def clean(ll):

    """Remove all corrupt lines from a set of bs4 <line>s

    Args:
        ll (list of bs4 <line>): Lines to clean

    Returns:
        (list of bs4 <line>): The lines, with the corrupt ones removed.
    """

    return [l for l in ll if l.has_attr('pattern')
    and l['pattern']!='corrupt' 
    and l['pattern']!='not scanned']
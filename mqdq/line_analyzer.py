from bs4 import BeautifulSoup
from collections import Counter
import re

def classify_caesura(l, n, strict=False):
    
    """Classify the caesura occurring in foot n.

    Args:
        l (bs4 <line>): Line to classify
        n (int): Foot number to classify (1..6)
        strict (bool): If True, consider Quasi as None

    Returns:
        string: Q, -, W, or S (Quasi, None, Weak, Strong)
    """
    
    if l['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")
            
    try:
        for w in l('word'):
            # syllable string ends with A, and there's a wordbreak
            # so this is a strong caesura
            if re.search('%dA$' % n, w['sy']) and w.has_attr('wb'):
                return 'S'
            elif re.search('%db$' % n, w['sy']) and w.has_attr('wb'):
                return 'W'
            elif re.search('%d[Ab]$' % n, w['sy']) and w.has_attr('mf') and w['mf']=='SY':
                if not strict:
                    return 'Q'
                else:
                    return '-'
            elif re.search('%d[Tc]' % n, w['sy']): 
                # we've passed the end of the foot in question
                return '-'
    except:
        raise ValueError("Can't handle this: %s" % l)
  
def grep(soup, s):

    """Case insensite grep on the text contents.

    Args:
        soup (bs4 soup): The text in which to search
        s (string): String to search for. This will be converted
                    into a regular expression, so re characters
                    are allowed.

    Returns:
        (list): a list of matching bs4 <line>s
    """

    r = re.compile(s, re.IGNORECASE)
    return [s.parent.parent for s in soup.find_all(string=r)]

def elision_after_foot(n, l):

    """Is there elision after foot n?

    Args:
        n (int): Foot number to check (1..6)
        l (bs4 <line>): Line to check

    Returns:
        (bool): The result
    """

    if l['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")

    try:    
        for w in l('word'):
            if re.search('%d[Tc]' % n, w['sy']): 
                if w.has_attr('mf') and w['mf']=='SY':
                    return True
                return False

        return False

    except:
        raise ValueError("Can't handle this: %s" % l)

def metrical_nucleus(l, strict=False):

    """Classify the caesurae in the second, third and fourth feet 
    (sometimes called 1.5, 2.5, 3.5).

    Args:
        l (bs4 <line>): Line to operate on
        strict (bool): If True, consider Quasi as None

    Returns:
        (string): A three element string, made up of the following:
                  Q, -, W, or S (Quasi, None, Weak, Strong)
    """

    return ''.join([
        classify_caesura(l,2,strict),
        classify_caesura(l,3,strict),
        classify_caesura(l,4,strict),
    ])

def has_3rd_foot_caes(l, strict=True):
    
    """Determine whether a line has any kind of caesura in the third foot.
    
    Args:
        l (bs4 <line>): Line to check
        strict (bool): If True, accept Quasi caesurae (occurring over an elision)

    Returns:
        (bool): The result
    """
    
    if l['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")

    try:
        caes = classify_caesura(l, 3)
        if strict:
            if caes == '-' or caes == 'Q':
                return False
        else:
            if caes == '-':
                return False
        return True

    except:
        raise ValueError("Can't handle this: %s" % l)

def diaer_after_first(l):

    """Determine whether a line has a diaeresis after the first foot.
    
    Args:
        l (bs4 <line>): Line to check

    Returns:
        (bool): The result
    """

    if l['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")
    
    try:
        for w in l('word'):
            if re.search('1[Tc]$', w['sy']) and w.has_attr('wb') and w['wb']=='DI':
                return True
            if re.search('2', w['sy']):
                break
        return False

    except:
        raise ValueError("Can't handle this: %s" % l)

def has_bd(line):
    
    """Determine whether a line contains a bucolic diaeresis.
    
    Args:
        l (bs4 <line>): Line to check

    Returns:
        (bool): The result
    """
    
    if line['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")

    try:
        # We're looking for a diaeresis after the fourth foot.
        # Here's an example line (without bucolic diaeresis):
        # <line name="52" metre="H" pattern="DSSD">
        #   <word sy="1A1b1c2A" wb="CM">Oceanus</word>
        #   <word sy="2T3A" wb="CM">fontes</word>
        #   <word sy="3T4A4b4c" wb="DI">torrentibus</word>
        #   <word sy="5A5b5c" wb="DI">ingruit</word>
        #   <word sy="6A6X">undis.</word>
        # </line>
        
        # So, if the word has a 'DI' word boundary, and its
        # syllables _end_ with the thesis of the fourth foot
        # (4T for spondee, 4c for dactyl) then we should be done
        for w in line('word'):
            if re.search('4[cT]$', w['sy']) and w.has_attr('wb') and w['wb']=='DI':
                return True
        return False
    except:
        raise ValueError("Error processing: %s" % line)

def _get_syls_with_stress(w):
    if len(w['sy']) <= 2 and not _has_elision(w):
        return w['sy']
    syls = re.findall('..', w['sy'])
    stress = _stressed(w)
    return( ''.join(syls[:stress+1]) + '\'' + ''.join(syls[stress+1:]))

def txt(l, scan=False, number_with=None):

    """Extract the text from a line.

    Args:
        l (bs4 <line): Line to operate on
        scan (bool): If True, add a line of scansion and accent:
                     Dixerat, atque illam media  inter talia   ferro
                     1A'1b1c  2A'_  2T'3A 3b'3c_ 4A'4T 5A'5b5c 6A'6X

        number_with (bs4 soup): If provided, text will be numbered by finding the lines
                                in that bs4 object (WARNING! Can be slow!):
                                8:196> Caede tepebat humus, foribusque affixa  superbis
                                       1A'1b 1c2A'2b 2c'3A  3b3c4A'_   4T5A'5b 5c6A'6X WSQ
    Returns:
        (string): The result
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
        if l['pattern']=='corrupt':
            return l_prefix + ' '.join([w.text for w in l('word')]) + "\n" + scan_prefix + "[corrupt]"

        for w in words:
            if len(w['sy'])==0:
                if w.has_attr('mf') and w['mf']=='PE':
                    # prodelision, the word is there but
                    # the syllables vanished
                    # Pollicita est -> Pollicit'est
                    res.append(['_', w.text])
                continue
            syls = _get_syls_with_stress(w)
            if _has_elision(w):
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

def txt_and_number(ll, every=5, scan=False, start_at=1):
    
    """Extract the text from a line, with numbers. Where `txt` uses references to the text,
    this uses independent numbers. Use this method if you want to print out a
    sequentially numbered extract. Use `txt` if you want to add numbers to the result of a
    search or a random sample.

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

    return [l for l in ll if l['pattern']!='corrupt']

def _stressed(w):
    syls = re.findall('..', w['sy'])
    
    # For words with elision and a long syllable ending, I assume the stress
    #stayed on that syllable. This is based on analysing lots of hexameter poetry.
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

    if _has_elision(w) and re.match('.[ATX]',syls[-1]):
        return len(syls)-1

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
        return(0)
    # Two syls, always first syllable
    elif len(syls) == 2:
        return(0)
    # If three or more...
    else:
        # Second last syllable is long then it takes the stress
        # (in this markup, long syls are uppercase A, T or X
        if re.match('.[ATX]', syls[-2]):
            return(len(syls)-2)
        # otherwise it's the syllable before that is stressed
        else:
            return(len(syls)-3)

def _conflict(w,foot):

    # Not only does the stress need to fall on an Arsis, but it needs to
    # fall on the arsis of the foot we're actually interested in.

    syls = re.findall('..', w['sy'])
    if len(w['sy'])==0:
        raise ValueError("No syllables?")
    # A means arsis, which is the start of either a spondee or dactyl
    if syls[_stressed(w)] == ('%dA'%foot):
        return(False)
    return(True)

def _has_elision(w):
    # SY for synalepha
    return w.has_attr('mf') and w['mf']=='SY'

def ictus_conflicts(l):

    """Count the number of ictus conflicts in a line, considering
    every foot (not every word).

    Args:
        l (bs4 <line>): Line to check

    Returns:
        (int): Number of conflicts (0..6)
    """

    # Slightly magic. True counts as 1 in python, False as 0
    return sum([conflict_in_foot(f,l) for f in range(1,7)])

CLITICS = ('que', 'ne', 've')

def conflict_in_foot(n, l):

    """Determine if the nth foot in the given line has an ictus/accent conflict

    Args:
        n (int): Foot to check (1..6)

    Returns:
        (bool): True if a conflict exists, False otherwise
    """

    if l['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")

    containing_word = next((w for w in l('word') if re.search('%dA'%n, w['sy'])), None)
    if not containing_word:
        raise ValueError("No arsis for syllable %d in line?? %s" % (n, txt(l)))

    return _conflict(containing_word, n)

def harmony(l):

    """Calculate the ictus conflicts for the first four feet (since the final
    two feet are almost always in harmony)
    
    Args:
        l (bs4 <line): Line to check

    Returns:
        (string): String of four characters (Conflict or Harmony) 'CHHC'
    """

    if l['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt l!")

    res = []
    try:
        for i in range(1,5): # (stops at 4 not 5)
            if conflict_in_foot(i, l):
                res.append('C')
            else:
                res.append('H')

        return ''.join(res)
    except:
        raise ValueError("Error processing: %s" % l)
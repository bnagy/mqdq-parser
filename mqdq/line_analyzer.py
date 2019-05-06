from bs4 import BeautifulSoup
from collections import Counter
import re

def classify_caesura(l, n, strict=False):
    
    # Classify the caesura occurring in foot n
    # In: l, a BeautifulSoup <line>; n, an Int
    # Out: A String, Q, -, W, or S (Quasi, None, Weak, Strong)
    
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
                break
        return '-'

    except:
        raise ValueError("Can't handle this: %s" % l)
  

def elision_after_foot(n, l):

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

    # Classify the caesurae in the second, third and fourth feet (sometimes
    # called 1.5, 2.5, 3.5). The possible values are:
    # - '-' for None (foot falls completely inside a word)
    # - 'Q' for Quasi (caesura would occur, but there is elision)
    # - 'W' for Weak (caesura after the first breve in a trochee)
    # - 'S' for Strong (caesura after the arsis)
    #
    # In: a <line>
    # Out: a String of three characters

    return ''.join([
        classify_caesura(l,2,strict),
        classify_caesura(l,3,strict),
        classify_caesura(l,4,strict),
    ])

def has_3rd_foot_caes(l, strict=True):
    
    # Determine whether a line has any kind of caesura
    # in the third foot
    # In: a <line>
    # Out: Boolean
    
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

    # Determine whether a line has a diaeresis after the first foot.
    # In: a <line>
    # Out: Boolean

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
    
    # Determine whether a given line has bucolic diaeresis.
    # In: a <line>
    # Out: Boolean
    
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

    # Return the text from a line. If the scan option is True add another line
    # formatted with the scansion below it (including elision and stress). Eg:
    #
    # Dixerat, atque illam media  inter talia   ferro
    # 1A'1b1c  2A'_  2T'3A 3b'3c_ 4A'4T 5A'5b5c 6A'6X
    #
    # In: a <line>
    # Out: a String
    #
    # NB: Numbering the lines with book:line references can be pretty slow, because
    # we need to search the whole bs4 collection per line.

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
    
    # We can't assume ll has been cleaned!

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
    for d in soup('division'):
        if l in d:
            return d['title']
    return None

def bookref(l, soup):
    return("%2s:%-3d" % (which_book(l, soup), int(l['name'])))

def clean(ll):
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

def ictus_conflicts(line):

    # Count the number of ictus conflicts in a line
    #
    # In: a <line>
    # Out: Int, number of conflicts

    count = 0
    for idx, w in enumerate(line('word')):
        # don't process words with no syllables
        if len(w['sy'])==0:
            # no content at all, ignore
            continue
        if w.has_attr('mf') and w['mf'] == "PE":
            # prodelision, fama est --> fama'st skip this word, it has no
            # syllables left.
            if len(w['sy']) != 0:
                raise RuntimeError("BUG: Prodelision with content??")
            continue
        if _conflict(w, idx):
            count+=1

    return count

CLITICS = ('que', 'ne', 've')

def conflict_in_foot(n, line):

    if line['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")

    containing_word = next((w for w in line('word') if re.search('%dA'%n, w['sy'])), None)
    if not containing_word:
        raise ValueError("No arsis for syllable %d in line?? %s" % (n, txt(line)))

    return _conflict(containing_word, n)

def ic_by_foot(line):

    # Calculate the ictus conflicts for the first four feet, not by word
    #
    # In: a <line>
    # Out: a String of four syllables (Conflict or Harmony) 'CHHC'

    if line['pattern'] == 'corrupt':
        raise ValueError("Can't operate on a corrupt line!")

    res = []
    try:
        for i in range(1,5): # (stops at 4 not 5)
            if conflict_in_foot(i, line):
                res.append('C')
            else:
                res.append('H')

        return ''.join(res)
    except:
        raise ValueError("Error processing: %s" % line)
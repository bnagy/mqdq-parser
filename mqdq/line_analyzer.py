from bs4 import BeautifulSoup
from collections import Counter
import re

def classify_caesura(l, n, strict=False):
    
    # Classify the caesura occurring in foot n
    # In: l, a BeautifulSoup <line>; n, an Int
    # Out: A String, Q, -, W, or S (Quasi, None, Weak, Strong)
    
    try:
        if l['pattern'] == 'corrupt':
            raise ValueError("Can't calculate conflicts on a corrupt line!")
            
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
    
    try:
        if l['pattern'] == 'corrupt':
            raise ValueError("Can't calculate conflicts on a corrupt line!")
            
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

    try:
        if l['pattern'] == 'corrupt':
            raise ValueError("Can't calculate conflicts on a corrupt line!")
            
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
    
    try:
        if line['pattern'] == 'corrupt':
            raise ValueError("Can't check metrical features on corrupt lines!")
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

def txt(l, scan=False):

    # Return the text from a line. If the scan option is True add another line
    # formatted with the scansion below it (including elision). Eg:
    #
    # Litora, multum ille et terris iactatus et alto
    # 1A1b1c  2A_    2T_  3A 3T4A   4T5A5b   5c 6A6X
    #
    # In: a <line>
    # Out: a String

    res = []

    try:
            
        words = l('word')
        res=[]
        if not scan:
            return ' '.join([w.text for w in l('word')])
        if l['pattern']=='corrupt':
            return ' '.join([w.text for w in l('word')]) + "\n[corrupt]"

        for w in words:
            if len(w['sy'])==0:
                if w.has_attr('mf') and w['mf']=='PE':
                    # prodelision, the word is there but
                    # the syllables vanished
                    # Pollicita est -> Pollicit'est
                    res.append(['_', w.text])
                continue
            if __has_elision(w):
                res.append([w['sy']+'_',w.text])
            else:
                res.append([w['sy'],w.text])
            
    except:
        raise ValueError("Can't handle this: %s" % l)
    
    s1, s2='',''
    for syls,txt in res:
        if len(txt)>=len(syls):
            s1 += txt + ' '
            s2 += syls + ' '*(len(txt) - len(syls) + 1)
        else:
            s1 += txt + ' '*(len(syls) - len(txt) + 1)
            s2 += syls + ' '
    
    return (s1.strip() + '\n' + s2.strip())

def txt_and_number(lines, every=5, scan=False, start_at=0):
    
    # We can't assume lines has been cleaned!

    n_len = len(str(len(lines)+start_at))
    strs = [txt(l,scan) for l in lines]
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


def __stressed(syllables):
    
    # Compute the index of the stressed syllable in a Latin word
    # Caller should remove clitics before this point.
    #
    # in: a syllable array (of strings)
    # out: Int, the index of the stressed syllable
    
    # One syllable words are stressed
    if len(syllables) == 1:
        return(0)
    # Two syllables, always first syllable
    elif len(syllables) == 2:
        return(0)
    # If three or more...
    else:
        # Second last syllable is long then it takes the stress
        # (in this markup, long syllables are uppercase A, T or X
        if re.match('.[ATX]', syllables[-2]):
            return(len(syllables)-2)
        # otherwise it's the syllable before that is stressed
        else:
            return(len(syllables)-3)

def __conflict(syllables):
    
    # Determine whether the stress in a Latin word falls on
    # a hexameter ictus (the start of a foot)
    #
    # Caller needs to deal with elision before this point!
    #
    # in: a syllable array bearing just one stress
    #     (ie a word or two words mushed together by elision)
    # out: Bool, does the stress fall on the start of a hexameter foot?
    
    if len(syllables)==0:
        raise ValueError("No syllables?")
    # A means arsis, which is the start of either a spondee or dactyl
    if re.match('.A', syllables[__stressed(syllables)]):
        return(False)
    return(True)

def __has_elision(w):
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
            # prodelision, fama est --> fama'st
            # just drop this word, it has no syllables
            # left.
            if len(w['sy']) != 0:
                raise RuntimeError("BUG: Prodelision with content??")
            continue
        syls = re.findall('..', w['sy'])
        if __has_elision(w):
            # don't need to worry about clitics
            if len(syls)==0:
                raise ValueError("Elision marked, but no syllables? %s in %s" % (w, line))
            if __conflict(syls):
                count += 1
        else:
            if len(syls) > 1 and w.text.endswith(CLITICS):
                # ignore the clitic for the purposes of detecting word stress
                syls.pop()
            if __conflict(syls):
                count += 1
    return count

CLITICS = ('que', 'ne', 've')
def ic_by_foot(line):

    # Calculate the ictus conflicts for the first four feet, not by word
    #
    # In: a <line>
    # Out: a String of four syllables (Conflict or Harmony) 'CHHC'


    res = []
    try:
        if line['pattern'] == 'corrupt':
            raise ValueError("Can't calculate conflicts on a corrupt line!")
        for i in range(1,5): # (stops at 4 not 5)
            # find the word containing the ictus for this foot
            # (some words may be found more than once)
            containing_word = next((w for w in line('word') if re.search('%dA'%i, w['sy'])), None)
            if not containing_word:
                raise ValueError("No arsis for syllable %d in line?? %s" % (i, txt(line)))
            
            # split into syllables and find the ictus syllable index then
            # check if it's the same as the accent index, but taking clitics
            # into account.
            syls = re.findall('..', containing_word['sy'])
            ictus_idx = syls.index('%dA'%i)
            if __has_elision(containing_word):
                # don't need to worry about clitics
                if len(syls)==0:
                    raise ValueError("Elision marked, but no syllables? %s in %s" % (w, line))
                if __stressed(syls) == ictus_idx:
                    res.append('H')
                else:
                    res.append('C')
            else:
                if len(syls) > 1 and containing_word.text.endswith(CLITICS):
                    # ignore the clitic for the purposes of detecting word stress
                    syls.pop()
                if __stressed(syls) == ictus_idx:
                    res.append('H')
                else:
                    res.append('C')
        return ''.join(res)
    except:
        raise ValueError("Error processing: %s" % line)

def syllabenate(l):
    
    # Convert a line into an array of syllable strings,
    # resolving elision and prodelision.
    #
    # in: a <line>
    # out: a list of strings
    
    res = []
    
    try:
        if l['pattern'] == 'corrupt':
            raise ValueError("Can't calculate conflicts on a corrupt line!")
        words = l('word')
        res=[]
        for w in words:
            if len(w['sy'])==0:
                continue
            if has_elision(w):
                res.append(w['sy']+'_')
            else:
                res.append(w['sy'])
            
    except:
        raise ValueError("Can't handle this: %s" % l)
    
    return res
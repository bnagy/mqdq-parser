import mqdq.line_analyzer as la
import re
from collections import Counter

# Retired Versions
# def ictus_counter(lines, trim_tails=True):
#     c = Counter(x for x in [la.ictus_conflicts(l) for l in lines if l['pattern']!='corrupt'])
#     # empirically, there aren't many lines 
#     # with 0 or 6 conflicts, so this option folds those
#     # into the counts for 1 and 5
#     if trim_tails:
#         c[1] += c[0]
#         c[5] += c[6]
#         del c[0]
#         del c[6]
#     return c

# def foot_counter(lines, feet=3):
#     # The foot pattern is a string, so we can consider
#     # just the first three letters, which will 'merge' the counts
#     # for eg SSSD and SSSS.
#     return Counter([l['pattern'][:feet] for l in lines if l['pattern']!='corrupt'])

def caesura_counter(lines, strict=False):
    return Counter([la.metrical_nucleus(l, strict) for l in lines if l['pattern']!='corrupt'])

def conflict_counter(lines):
    return Counter([la.ic_by_foot(l) for l in lines if l['pattern']!='corrupt'])

def __diaer(l):
    # l isn't corrupt
    return len([w for w in l('word') if (w.has_attr('wb') and w['wb']=='DI')])

def di_counter(lines):
    return Counter([__diaer(l) for l in lines if l['pattern'] != 'corrupt'])

def bool_counter(lines, indic_fn):
    
    # Return a Counter for a set of lines, according to
    # a supplied indicator function (which should return a Boolean)
    
    res = {}
    t = len([l for l in lines if indic_fn(l)])
    f = len([l for l in lines if not indic_fn(l)])
    if not t+f == len(lines):
        raise ValueError("Indictator function didn't partition the lines!")
    return Counter({True: t, False: f})

__HEXAMETER_PATTERN_GROUPS = [
    'SDSD|SDDS',
    'SSSD',
    'SDSS|SSDS',
    'DDDD',
    'DDSD|DSDD',
    'DSDS',
    'DDDS',
    'DSSD|DDSS',
    'SDDD|SSDD',
    'DSSS',
    'SSSS',
]
def pattern_counter(lines):
    results = dict.fromkeys(__HEXAMETER_PATTERN_GROUPS, 0)
    clean_lines = [x for x in lines if x['pattern'] != 'corrupt']
    for p in __HEXAMETER_PATTERN_GROUPS:
        for l in clean_lines:
            if re.match(p, l['pattern']):
                results[p] += 1
    return Counter(results)

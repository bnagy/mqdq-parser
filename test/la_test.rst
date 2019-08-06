# Tests

## mqdq.line_analyzer

>>> from mqdq import line_analyzer as la
>>> from mqdq import utils
>>> from bs4 import BeautifulSoup

>>> with open('VERG-aene.xml') as fh:
...     aen_soup = BeautifulSoup(fh,"xml")

>>> aen = utils.clean(aen_soup('line'))
>>> len(aen)
9840

# Caesurae

>>> aen[60]
<line metre="H" name="61" pattern="DSSS">
<word sy="1A" wb="CM">Hoc</word>
<word sy="1b1c2A" wb="CM">metuens</word>
<word mf="SY" sy="2T3A">molemque</word>
<word sy="3T" wb="DI">et</word>
<word sy="4A4T" wb="DI">montis</word>
<word sy="5A5b5c" wb="DI">insuper</word>
<word sy="6A6X">altos</word>
</line>

The caesura in the third foot occurs over an elision

>>> la.classify_caesura(aen[60], 3)
'Q'

In strict mode, it's counted as no caesura

>>> la.classify_caesura(aen[60], 3, strict=True)
'-'

There's a diaeresis after foot 4, which isn't a caesura

>>> la.classify_caesura(aen[60], 4)
'-'

Strong caesura in foot 2

>>> la.classify_caesura(aen[60], 1)
'S'

Let's look at another line

>>> aen[97]
<line metre="H" name="98" pattern="DDDS">
<word sy="1A" wb="CM">Non</word>
<word sy="1b1c2A2b" wb="CF">potuisse</word>
<word mf="SY" sy="2c3A">tuaque</word>
<word mf="SY" sy="3b3c">animam</word>
<word sy="4A" wb="CM">hanc</word>
<word sy="4T5A5b5c" wb="DI">effundere</word>
<word sy="6A6X">dextra,</word>
</line>
>>> la.classify_caesura(aen[97], 2)
'W'

# Other Caesura Stuff

>>> la.metrical_nucleus(aen[97])
'WQS'
>>> la.has_3rd_foot_caes(aen[97])
False
>>> la.has_3rd_foot_caes(aen[60])
False
>>> la.has_3rd_foot_caes(aen[60], strict=False)
True

# Elision

>>> la.elision_after_foot(2, aen[60])
True
>>> la.elision_count(aen[60])
1

# Bucolic Diaeresis

>>> la.has_bd(aen[60])
True

# Ictus/Accent conflict

Here's the scansion of line 61. Note how the stress (`)
doesn't fall on the Arsis (A) of foot 2. That's a conflict.

>>> print(utils.txt(aen[60], scan=True))
Hoc metuens molemque et montis insuper altos
1A  `1b1c2A 2T`3A_   3T `4A4T  `5A5b5c `6A6X

>>> la.conflict_in_foot(2, aen[60])
True
>>> la.conflict_in_foot(4, aen[60])
False
>>> la.ictus_conflicts(aen[60])
1

We can also get the harmony of the first four feet as a string
(the last two are almost always HH)

>>> la.harmony(aen[60])
'HCHH'

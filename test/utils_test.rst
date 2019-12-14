>>> from mqdq import line_analyzer as la
>>> from mqdq import utils
>>> from bs4 import BeautifulSoup

>>> with open('VERG-aene.xml') as fh:
...     aen_soup = BeautifulSoup(fh,"xml")

>>> aen = utils.clean(aen_soup('line'))

(These results are only sorted so the tests pass. grep
results are not deterministically ordered)

grep for stuff in the XML soup

>>> sorted(utils.grep(aen_soup, 'strages'), key=lambda x: x['name'])
[<line metre="H" name="526" pattern="DSSS">
<word sy="1A" wb="CM">Quas</word>
<word sy="1b1c" wb="DI">ibi</word>
<word sy="2A" wb="CM">tum</word>
<word sy="2T3A" wb="CM">ferro</word>
<word sy="3T4A" wb="CM">strages,</word>
<word sy="4T" wb="DI">quae</word>
<word sy="5A5b5c" wb="DI">funera</word>
<word sy="6A6X">Turnus</word>
</line>, <line metre="H" name="784" pattern="DSSS">
<word sy="1A1b1c2A" wb="CM">Aggeribus</word>
<word sy="2T3A" wb="CM">tantas</word>
<word sy="3T4A" wb="CM">strages</word>
<word sy="4T5A5b" wb="CF">impune</word>
<word sy="5c" wb="DI">per</word>
<word sy="6A6X">urbem</word>
</line>]

Regexes supported...
(The sorting stuff is just so the test is deterministic)

>>> sorted(utils.grep(aen_soup, 'orum$'), key=lambda x: x['name']+x['pattern'])[-1]
<line metre="H" name="98" pattern="SSSS">
<word sy="1A" wb="CM">Et</word>
<word sy="1T2A" wb="CM">nati</word>
<word mf="SY" sy="2T3A">natorum</word>
<word sy="3T" wb="DI">et</word>
<word sy="4A" wb="CM">qui</word>
<word sy="4T5A5b" wb="CF">nascentur</word>
<word sy="5c" wb="DI">ab</word>
<word sy="6A6X">illis."</word>
</line>

Blatting text (prints to screen)

>>> utils.blat(utils.grep(aen_soup, 'nymphaeque'), scan=False)
"Haec nemora indigenae Fauni Nymphaeque tenebant

Or blat with scansion (or phonetic transcription)

>>> utils.blat(aen[100])
Scuta uirum galeasque et fortia  corpora uoluit!"
`1A1b `1c2A 2b2c`3A   3T `4A4b4c `5A5b5c `6A6X

There are more nymphs, of course...

>>> len(utils.grep(aen_soup, 'nymph'))
22

Programmatically, we can also extract that text

>>> sorted([utils.txt(l, scan=False) for l in utils.grep(aen_soup, 'nympharum')])
['(An Phoebi soror? an Nympharum sanguinis una?),', 'Nympharum domus. Hic fessas non uincula nauis']

Also with scansion

>>> utils.txt(aen[100], scan=True)
'Scuta uirum galeasque et fortia  corpora uoluit!"\n`1A1b `1c2A 2b2c`3A   3T `4A4b4c `5A5b5c `6A6X'

To just number up chunks of text there's txt_and_number

>>> print("\n".join(utils.txt_and_number(aen[:12])))
    Arma uirumque cano, Troiae qui primus ab oris
    Italiam fato profugus Lauiniaque uenit
    Litora, multum ille et terris iactatus et alto
    Vi superum, saeuae memorem Iunonis ob iram,
 5  Multa quoque et bello passus, dum conderet urbem
    Inferretque deos Latio, genus unde Latinum
    Albanique patres atque altae moenia Romae.
    Musa, mihi causas memora, quo numine laeso
    Quidue dolens regina deum tot uoluere casus
10  Insignem pietate uirum, tot adire labores
    Impulerit. Tantaene animis caelestibus irae?
    Vrbs antiqua fuit (Tyrii tenuere coloni)

Which works with scansion

>>> print("\n".join(utils.txt_and_number(aen[:10], scan=True)))
    Arma  uirumque cano, Troiae qui primus ab oris
    `1A1b 1c`2A2b  `2c3A `3T4A  4T  `5A5b  5c `6A6X
    Italiam   fato  profugus Lauiniaque uenit
    1A`1b1c2A `2T3A `3b3c4A  4T`5A5b5c  `6A6X
    Litora, multum ille et terris iactatus et alto
    `1A1b1c `2A    `2T  3A `3T4A  4T`5A5b  5c `6A6X
    Vi superum, saeuae memorem Iunonis ob iram,
    1A `1b1c2A  `2T3A  `3b3c4A 4T`5A5b 5c `6A6X
 5  Multa quoque et bello passus, dum conderet urbem
    `1A1b `1c    2A `2T3A `3T4A   4T  `5A5b5c  `6A6X
    Inferretque deos  Latio,  genus unde  Latinum
    1A1T`2A2b   `2c3A `3b3c4A `4b4c `5A5b 5c`6A6X
    Albanique patres atque altae moenia  Romae.
    1A1T`2A2b `2c3A  3T    `4A4T `5A5b5c `6A6X
    Musa, mihi  causas memora, quo numine  laeso
    `1A1b `1c2A `2T3A  `3b3c4A 4T  `5A5b5c `6A6X
    Quidue dolens regina  deum  tot uoluere casus
    `1A1b  `1c2A  2T`3A3b `3c4A 4T  `5A5b5c `6A6X
10  Insignem pietate   uirum, tot adire   labores
    1A`1T2A  2b2c`3A3b `3c4A  4b  4c`5A5b 5c`6A6X

Or with phonetic transcrption

>>> print("\n".join(utils.txt_and_number(aen[:10], phon=True)))
    Arma   uirumque    cano,   Troiae   qui primus   ab oris
    `Ār.ma wi.`rum.kwe `ka.nō, `Troi.ae kwi `pri.mus ab `ō.ris
    Italiam    fato   profugus    Lauiniaque     uenit
    Ī.`ta.li.ã `fā.tō `pro.fu.gus Lā.`win.ja.kwe `wē.nit
    Litora,    multum ille   et  terris   iactatus    et alto
    `Lī.to.ra, `mul._ `til._ let `ter.ris jak.`tā.tus et `āl.to
    Vi superum,   saeuae   memorem   Iunonis    ob iram,
    Wī `su.per.ũ, `sae.wae `me.mo.rẽ Jū.`nō.nis ob `ī.rã,
 5  Multa   quoque et   bello   passus,   dum conderet    urbem
    `Mul.ta `kwo._ kwet `bel.lō `pas.sus, dũ  `kon.de.ret `ūr.bẽ
    Inferretque     deos   Latio,    genus   unde   Latinum
    Īn.fer.`ret.kwe `de.ōs `La.ti.ō, `ge.nus `ūn.de La.`tī.nũ
    Albanique     patres   atque altae     moenia    Romae.
    Āl.bā.`nī.kwe `pa.tres āt._  `kwal.tae `moe.ni.a `Rō.mae.
    Musa,   mihi   causas   memora,    quo numine    laeso
    `Mū.sa, `mi.hī `kau.sas `me.mo.rā, kwo `nū.mi.ne `lae.so
    Quidue   dolens   regina    deum  tot uoluere    casus
    `Kwid.we `do.lens rē.`gī.na `de.ũ tot `wol.we.re `kā.sus
10  Insignem   pietate     uirum,  tot adire    labores
    Īn.`sin.jẽ pi.e.`tā.te `wi.rũ, tot a.`dī.re la.`bō.res


# Tests

## mqdq.rhyme

>>> from mqdq import rhyme
>>> from mqdq import utils
>>> from bs4 import BeautifulSoup

>>> with open('VERG-aene.xml') as fh:
...     aen_soup = BeautifulSoup(fh,"xml")

>>> aen = utils.clean(aen_soup('line'))
>>> len(aen)
9840

>>> for l in aen[:10]:
...     print(utils.phonetic(l, number_with=aen_soup))
 1:1  > Arma   uirumque    cano,   Troiae   qui primus   ab oris
        `Ār.ma wi.`rum.kwe `ka.nō, `Troi.ae kwi `pri.mus ab `ō.ris
 1:2  > Italiam     fato   profugus    Lauiniaque     uenit
        Ī.`ta.li.ām `fā.tō `pro.fu.gus Lā.`win.ja.kwe `wē.nit
 1:3  > Litora,    multum ille   et  terris   iactatus    et alto
        `Lī.to.ra, `mul._ `til._ let `ter.ris jak.`tā.tus et `āl.to
 1:4  > Vi superum,    saeuae   memorem    Iunonis    ob iram,
        Wī `su.per.ūm, `sae.wae `me.mo.rem Jū.`nō.nis ob `ī.ram,
 1:5  > Multa   quoque et   bello   passus,   dum conderet    urbem
        `Mul.ta `kwo._ kwet `bel.lō `pas.sus, dum `kon.de.ret `ūr.bem
 1:6  > Inferretque     deos   Latio,    genus   unde   Latinum
        Īn.fer.`ret.kwe `de.ōs `La.ti.ō, `ge.nus `ūn.de La.`tī.num
 1:7  > Albanique     patres   atque altae     moenia    Romae.
        Āl.bā.`nī.kwe `pa.tres āt._  `kwal.tae `moe.ni.a `Rō.mae.
 1:8  > Musa,   mihi   causas   memora,    quo numine    laeso
        `Mū.sa, `mi.hī `kau.sas `me.mo.rā, kwo `nū.mi.ne `lae.so
 1:9  > Quidue   dolens   regina    deum   tot uoluere    casus
        `Qui.due `do.lens rē.`gī.na `de.ūm tot `wō.lue.re `kā.sus
 1:10 > Insignem    pietate     uirum,   tot adire    labores
        Īn.`sin.jem pi.e.`tā.te `wi.rum, tot ad.`ī.re la.`bō.res
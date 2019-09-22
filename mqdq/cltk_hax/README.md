# CLTK Hacks

## About

This directory contains code I have stolen and modified from the [CTLK](https://github.com/cltk/cltk). I made a series of changes, with the intention of using the MQDQ scansion in [`rhyme.py`](../rhyme.py) to take the raw output from this syllabifier and adjust it according to the correct syllable count as determined by MQDQ. In general, (after modification) this code now forms less dipthongs, and doesn't internally convert 'gue' etc to 'gwe'. I also fixed some bugs with the prefixing system which would form incorrect syllabifications where a prefix was followed by a phonotactically illegal cluster (eg 'servit' used to form `['se', 'rvit']` instead of `['ser', 'vit']`), and maybe one or two other bugs that I forget. I suspect that for general use, I may have made it slightly worse, hence I have not suggested that the changes be pushed upstream.

## License & Acknowledgements

MIT as per author license.
Original author (according to the files) is Todd Cook, gratias ago ei.


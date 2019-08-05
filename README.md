# MQDQParser

## About

`mqdq` is a collection of utility and analysis code for working with the XML format of scanned Latin poems provided by MQDQ. These XML files can be downloaded from [pedecerto](http://www.pedecerto.eu/pagine/autori).

## Installation

I am very bad at python. I suppose you run `setup.py` at some point, or `pip install .`. There are pre-reqs. You'll need at least `numpy`, `scipy`, `pandas` and `bs4`. The aim is for this to be pip installable, but I don't know if we're there yet.

## Usage

This is all very alpha. When I work out how to autogenerate docs, you could use those. For now, read the code, sorry. Caveat - I work mainly with hexameters, at the moment, so I'm not sure if some features will break on elegiacs.

There are some tests in [test/](test), which are more or less human-readable ipython examples. There are some Jupyter notebooks in [notebooks/](notebooks) which run through a couple of non-trivial workflow examples. More of those are expected to follow.

## License & Acknowledgements

BSD style, see the [LICENSE](LICENSE.txt)

## Contributing

Fork and PR. Particularly welcome would be:
- improving the packaging structure
- tests
- general addition of pythonicity

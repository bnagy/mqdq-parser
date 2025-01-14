# MQDQParser [![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause) [![DOI](https://zenodo.org/badge/182027877.svg)](https://zenodo.org/badge/latestdoi/182027877)


## About

`mqdq` is a collection of utility and analysis code for working with the XML format of scanned Latin poems provided by MQDQ. These XML files can be downloaded from [pedecerto](http://www.pedecerto.eu/pagine/autori).

## Installation

HOPEFULLY, you can just do pip install MQDQParser and it will all work. Open issues if not.

Latest pypi version: 0.6.1
Latest github version: 0.8.0

## Usage

This is all very alpha. When I work out how to autogenerate docs, you could use those. For now, read the code, sorry. Caveat - I work mainly with hexameters, at the moment, so I'm not sure if some features will break on elegiacs.

There are some tests in [test/](test), which are more or less human-readable ipython examples. There are some Jupyter notebooks in [notebooks/](notebooks) which run through a couple of non-trivial workflow examples. More of those are expected to follow.

## Citation

If you are also playing the Fun Academia Game, please help me refill my Academia Hearts.

```
@software{nagy_mqdq_2019,
    author      = "Nagy, Ben",
    title       = "{MQDQParser}: Utility scripts in {P}ython for working with {XML} poems from {MQDQ}",
    year        = "2019",
    publisher   = {Zenodo},
    version     = {0.8.0},
    doi         = {10.5281/zenodo.4602588},
    url         = "https://github.com/bnagy/mqdq-parser"
}
```

## License & Acknowledgements

Code: BSD style, see the [LICENSE](LICENSE.txt)

The XML files used in the `hexameter_corpus` method are (c) [Pedecerto](http://www.pedecerto.eu), licensed (by them) under CC-BY-NC-ND.

## Contributing

Fork and PR. Particularly welcome would be:
- improving the packaging structure
- tests
- general addition of pythonicity

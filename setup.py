from distutils.core import setup

setup(
    name="MQDQParser",
    version="0.8.2",
    author="Ben Nagy",
    packages=["mqdq", "mqdq.cltk_hax"],
    license="3-Clause BSD",
    url="https://github.com/bnagy/mqdq-parser",
    long_description="""
	mqdq is a collection of utility and analysis 
	code for working with the XML format of scanned 
	Latin poems provided by MQDQ. These XML files 
	can be downloaded from http://www.pedecerto.eu/pagine/autori
	""",
    install_requires=[
        "setuptools",
        "beautifulsoup4",
        "numpy",
        "scipy",
        "pandas",
        "seaborn",
        "dominate",
    ],
)

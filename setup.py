import setuptools
from distutils.core import setup
import os

setup(
	name='MQDQParser',
	version='0.1.2',
	author='Ben Nagy',
	packages=['mqdq'],
	license='3-Clause BSD',
	url='https://github.com/bnagy/mqdq-parser',
	long_description='''
	mqdq is a collection of utility and analysis 
	code for working with the XML format of scanned 
	Latin poems provided by MQDQ. These XML files 
	can be downloaded from http://www.pedecerto.eu/pagine/autori
	''',
	install_requires=[
		'setuptools',
		'beautifulsoup4',
		'numpy',
		'scipy',
		'pandas'
	],
)

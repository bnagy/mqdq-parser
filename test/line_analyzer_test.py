import logging
from nose import *
from mqdq import line_analyzer as la
from bs4 import BeautifulSoup
import sys

# FML. So, first we set up a custom logger
mqdq = logging.getLogger('root')
mqdq.setLevel(logging.DEBUG)
# Now normally I'd just set the logging.basicConfig formatter, but
# nosetests will eat all those messages without a --debug flag.
# Instead, we set up a Console logger, and add that as a new handler
# to the custom logger. So, nose eats the mqdq output, but not the
# extra console output, and we get logging without having to pass flags
fmt = logging.Formatter("<%(filename)s:%(lineno)3s> in %(funcName)s ] %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(fmt)
mqdq.addHandler(ch)

_stuff = {}

def setup():
	with open('VERG-aene.xml') as fh:
		aen_soup = BeautifulSoup(fh,"xml")

	_stuff['aen'] = [l for l in aen_soup('line')]
	_stuff['aen_clean'] = [l for l in aen_soup('line') if l['pattern']!='corrupt']

def test_loaded_aen():
	mqdq.debug("Aeneid (cleaned) should be 9840 lines")
	assert(len(_stuff['aen_clean'])==9840)




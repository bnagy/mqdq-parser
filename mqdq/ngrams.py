from bs4 import BeautifulSoup
from collections import Counter
import re
import numpy as np
import pandas as pd
from mqdq import utils
from mqdq import rhyme
from mqdq import line_analyzer as la
import string

DEPUNCT = str.maketrans('', '', string.punctuation)
DEFANCY = str.maketrans({'ü':'y', u'\u0304':None, u'\u0303':None, '`':None})

def _remove_propers(ll, type='phon'):

	fixed_lines = []
	propers = set()

	for l in ll:

		# convert the line to a word array using orth or phon
		if type=='phon':
			syllab = rhyme.syllabify_line(l)
			a = [(w.pre_punct, ''.join(w.syls).translate(DEFANCY), w.post_punct) for w in syllab]
		else:
			a = [rhyme._punct_split(w) for w in l('word')]

		# Now convert easy propers while building a global propers set
		this_line=[]
		for idx, (pre,w,post) in enumerate(a):

			if w=='_' or len(w)==0:
				continue

			# The aim at this point is to identify things that are definitely
			# proper nouns, so we don't add things at the start of the line,
			# after a full stop, or at the start of a quote. Once we have
			# identified them, we'll replace them in all positions later.
			if idx > 0 and w[0].isupper() and not(
				a[idx-1][2].endswith(('?','.'))) and not(
				pre.startswith(("'",'"'))):

				# don't learn very short proper nouns
				if len(w) >= 5:
					propers.add(w)
					if w.endswith('_'):
						this_line.append('8_')
					else:
						this_line.append('8')
					continue

			this_line.append(w.lower())

		fixed_lines.append(this_line)

	# now do the rest of the replacements
	for l in fixed_lines:
		for i,w in enumerate(l):
			if w.capitalize() in propers:
				if w.endswith('_'):
					l[i] = ('8_')
				else:
					l[i] = ('8')

	return fixed_lines

def _join_line_array(ary):
	s = ary[0]
	for x in ary[1:]:
		if s.endswith('_'):
			s += x
		else:
			s = s + ' ' + x
	s += "\n"
	return s

def _just_stringify(ll, type='orth'):

	if type != 'orth' and type != 'phon':
		raise ValueError("Unknown stringify type (%s) only 'orth' or 'phon'." % type)

	fixed_lines = []
	propers = set()

	for l in ll:

		if type=='phon':
			syllab = rhyme.syllabify_line(l)
			a = [(w.pre_punct, ''.join(w.syls).translate(DEFANCY), w.post_punct) for w in syllab]
		else:
			a = [rhyme._punct_split(w) for w in l('word')]

		fixed_lines.append([x[1].lower() for x in a])

	return fixed_lines



def common_wordstems(ll, max_stem=5):

	ctr = Counter()

	for l in ll:
		s = utils.txt(l).translate(DEPUNCT).lower()
		for w in s.split(' '):
			if len(w) > max_stem:
				ctr[w[:max_stem]] += 1
			else:
				ctr[w] += 1

	return ctr

WORKS = [
	('Vergil', 'Aeneid', 'VERG-aene.xml'),
	('Ovid', 'Metamorphoses', 'OV-meta.xml'),
	('Silius', 'Punica', 'SIL-puni.xml'),
	('Statius', 'Thebaid', 'STAT-theb.xml'),
	('Lucan', 'Pharsalia', 'LVCAN-phar.xml'),
	('Vergil', 'Georgics', 'VERG-geor.xml'),
	('Ovid', 'Fasti', 'OV-fast.xml'),
	('Juvenal', 'Satires', 'IVV-satu.xml'),
	('Vergil', 'Eclogues', 'VERG-eclo.xml'),
	('Ovid', 'Amores3', 'ovid/OV-amo3.xml')
]

def string_chunks(ll, chunksz=80, type='phon', drop_propers=True):
	if drop_propers:
		ll = _remove_propers(ll, type=type)
	else:
		ll = _just_stringify(ll, type=type)

	chunks = list(la._chunks(ll, chunksz))
	if len(ll)%chunksz != 0:
		chunks = chunks[:-1]

	chunks = [[_join_line_array(x) for x in c] for c in chunks]
	chunks = [''.join(ss) for ss in chunks]
	return chunks

def geezit_corpus(chunksz=80, type='phon', drop_propers=True):

	df = pd.DataFrame()

	for auth,title,fn in WORKS:
		
		with open(fn) as fh:
			soup = BeautifulSoup(fh,"xml")
		ll = utils.clean(soup('line'))
		if title=='Punica':
			print("Cleaning out the Additamentum. %d lines" % len(ll))
			puni_books = [utils.clean(d('line')) for d in soup('division')]    
			addit=puni_books[7][143:224]
			ll = [l for l in ll if l not in addit]
			print("OK, %d lines left." % len(ll))

		tmpdf = pd.DataFrame()
		try:
			chunks = string_chunks(ll, chunksz, type, drop_propers)
		except Exception as e:
			print("Failed on %s." % title)
			raise e
		tmpdf['Chunk'] = chunks
		tmpdf['Author'] = auth
		tmpdf['Work'] = title
		df = df.append(tmpdf).reset_index(drop=True)

	return df



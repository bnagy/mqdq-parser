from mqdq.cltk_hax.syllabifier import Syllabifier
import re
from mqdq import utils
from mqdq import line_analyzer as la
import string
from collections import namedtuple, UserString
from dataclasses import dataclass
from typing import List, Any
import bs4
from bs4 import BeautifulSoup
from itertools import combinations

S = Syllabifier()
VOWELS = "aeiouyAEIOUY"
ALL_VOWELS = "aeiouyAEIOUYāēīōūȳĀĒĪŌŪȲüÜ\u0304"
COMBINING_MACRON = u'\u0304'
COMBINING_TILDE = u'\u0303'
# The 'vowel' in the nucleus can also include a unicode
# combining macron (U+0304)
ONC = re.compile(r'([aeiouyAEIOUYāēīōūȳĀĒĪŌŪȲüÜ\u0304\u0303]+)')
DBL_CONS = re.compile(r'^([bcdfghjklmnpqrstvwxz])\1', flags=re.I)

ELISION_DROP = VOWELS + 'mM'
VOWELS_NO_U = "aeioyAEIOY"
UV = str.maketrans({'u':'v', 'U':'V'})
VW = str.maketrans({'v':'w', 'V':'W'})
CK = str.maketrans({'c':'k', 'C':'K'})
YU = str.maketrans({'y':'ü', 'Y':'Ü'})
DEMACRON = str.maketrans({COMBINING_MACRON:None, COMBINING_TILDE:None})
KILL_M = str.maketrans({'m':None})

VU = str.maketrans({'V':'U'})
IJ = str.maketrans({'i':'j', 'I':'J'})
# 'oy' appears in Juvenal
DIPTHONGS = ['ae', 'oi', 'oe', 'eu', 'eo', 'ei', 'au', 'ui', 'ue'] #, 'ai', 'oy', 'ea']
RARE_DIPTHONGS = ['ai', 'oy', 'ea']
NON_U_DIPTHONGS = ['ae', 'oi', 'oe', 'eu', 'eo', 'ei', 'au', 'ai', 'oy', 'ea']
U_DIPTHONGS = ['ui', 'ue']
DEPUNCT = str.maketrans('', '', string.punctuation)
# These are either contracted sometimes, in poetry, or
# scanned weirdly in major works.
WEIRD_SCANS = ['dehinc', 'semihominis', 'semihomines', 
	'alueo', 'reliquo', 'reliquas', 'antehac', 'quoad',
	'aquai']

SCAN_HAX = {
	'dehinc':['deink'],
	'semihomines':['se','mi','jom','nes'],
	'semihominis':['se','mi','jom','nis'],
	'alueo':['al','wjo'],
	'reliquo':['re','li','ku','o'], # Lucr. DNR
	'reliquas':['re','li','ku','as'],
	'antehac':['an', 'tjak'],
	'quoad':['quoad'], # leave 'qu', will be phonetified later
	'aquai':['a','ku','a','i'],
}

PUNCT_SPLIT = re.compile(r'([%s]+)' % re.escape(string.punctuation))
DEFANCY = str.maketrans({'ü':'y', u'\u0304':None, u'\u0303':None, '`':None, '_':None})

class Syl(str):

	def __init__(self, s, **kwargs):
		if s != '_':
			self.stressed = (s[0]=='`') # bool
			try:
				if self.stressed:
					self.onset,self.nucleus,self.coda = ONC.split(s[1:])
				else:
					self.onset,self.nucleus,self.coda = ONC.split(s)
			except Exception as e:
				raise ValueError("Couldn't split %s: %s" % (s, e))
		else:
			self.onset,self.nucleus,self.coda = '','',''
			self.stressed = False
		super().__init__(**kwargs)


@dataclass
class Word:
	pre_punct: str
	syls: List[Syl]
	post_punct: str
	mqdq: bs4.element.Tag


def _try_form_dipthong(d, t, t_list, syls, mqdq_slen):

	d1 = tuple("%s%s" % (d[0], d[0].capitalize()))
	d2 = tuple("%s%s" % (d[1], d[1].capitalize()))

	# this regegx seems redundant, but it makes sure we don't 
	# drop off the edge of the string
	if re.search(d, t, flags=re.I):
		end_indices = [i for i, x in enumerate(syls) if x.endswith(d1)]
		for idx in end_indices:
			
			if len(syls) > idx+1 and syls[idx+1].startswith(d2):

				# special cases:
				if d == 'ea':
					# ea is not a 'real' Latin dipthong, but it is subject
					# to contraction by some of the poets
					syls[idx+1] = syls[idx][:-1] + "j" + syls[idx+1]
				elif d == 'ue' and len(syls)==idx+2 and len(syls[idx+1])==1:
					# We have eg quid.u.e, so we should form
					# the clitic 've', not the dipthong 'ue'. This
					# will be wrong less often. This amounts to running
					# consonantify instead of form_dipthong for this special
					# case.
					return _try_consonantify('u', 'v', t, t_list, syls, mqdq_slen)
				else:
					syls[idx+1] = syls[idx]+syls[idx+1]

				syls = syls[:idx] + syls[idx+1:]
				if len(syls) <= mqdq_slen:
					return syls
	return syls


def _try_split_dipthong(d, t, t_list, syls, mqdq_slen):

	# make a string that we can use as a character class
	# in the split below (to match upper or lowercase)
	d1 = "%s%s" % (d[0], d[0].capitalize())

	if re.search(d, t, flags=re.I):
		indices = [i for i, x in enumerate(syls) if re.search(d, x, flags=re.I)]
		for idx in indices:
			try:
				if 'u' in d1:
					# don't split a u dipthong after 'q'
					if re.search('qu', syls[idx], flags=re.I):
						continue
				pre,x,post = re.split("([%s])" % d1, syls[idx])
			except Exception as e:
				print(d)
				print(d1)
				print(t)
				raise e

			syls = syls[:idx] + [pre+x, post] + syls[idx+1:]
			if len(syls) >= mqdq_slen:
				return syls
	return syls


def _try_unconsonantify(frm, to, t, t_list, syls, mqdq_slen):

	frm_re = "[%s%s]" % (frm, frm.capitalize())
	indices = [i for i, x in enumerate(syls) if re.search('^%s'%frm, x, flags=re.I)]
	for idx in indices:
		pre,post = re.split(frm_re, syls[idx])
		syls = syls[:idx] + [pre+to] + S.syllabify(''.join([post]+syls[idx+1:]))
		if len(syls) >= mqdq_slen:
			return syls
	return syls


def _try_consonantify(frm, to, t, t_list, syls, mqdq_slen):

	frm_re = "[%s%s]" % (frm, frm.capitalize())
	if re.search("%s[%s]" % (frm, VOWELS), t, flags=re.I):
		indices = [m.start() for m in re.finditer(frm_re, t)]
		for idx in indices:
			if idx==len(t_list)-1:
				# never convert at the end
				continue
			if t_list[idx-1] in 'qQ':
				# don't convert after 'q'
				continue
			if t_list[idx+1] not in VOWELS:
				# don't consonantify before a consonant
				continue
			cache = syls
			old_len = len(syls)
			if t_list[idx].isupper():
				t_list[idx] = to.capitalize()
			else:
				t_list[idx] = to
			syls =  S.syllabify(''.join(t_list))
			if len(syls)==old_len:
				syls = cache
			if len(syls) <= mqdq_slen:
				return syls
	return syls


def _try_shrink(w, syls, t, t_list, mqdq_slen):

	if len(syls)==mqdq_slen:
		return syls

	# it's much more common to consonantify a 'u' than form a dipthong.
	for (frm, to) in [('u', 'v')]:
		syls = _try_consonantify(frm, to, t, t_list, syls, mqdq_slen)
		if len(syls) <= mqdq_slen:
			return syls

	# Now try to form various dipthongs to drop a syllable
	for d in DIPTHONGS:
		syls = _try_form_dipthong(d, t, t_list, syls, mqdq_slen)
		if len(syls) <= mqdq_slen:
			return syls

	# need to form 'oe' before consonantifying 'i' for moenia

	for (frm, to) in [('i', 'j')]:
		syls = _try_consonantify(frm, to, t, t_list, syls, mqdq_slen)
		if len(syls) <= mqdq_slen:
			return syls

	# There are a few more, which we only want to try if all consonantification fails.
	for d in RARE_DIPTHONGS:
		syls = _try_form_dipthong(d, t, t_list, syls, mqdq_slen)
		if len(syls) <= mqdq_slen:
			return syls

	# Last chance - 'ee' / 'ii' contraction
	if re.search('ee', t, flags=re.I):
		syls = S.syllabify(re.sub('ee', 'e', t, flags=re.I))

	if re.search('ii', t, flags=re.I):
		syls = S.syllabify(re.sub('ii', 'i', t, flags=re.I))

	return syls


def _try_grow(w, syls, t, t_list, mqdq_slen):

	if len(syls)==mqdq_slen:
		return syls

	# First try to split a dipthong
	for d in DIPTHONGS:
		syls = _try_split_dipthong(d, t, t_list, syls, mqdq_slen)
		if len(syls) >= mqdq_slen:
			return syls

	for frm, to, in [('j','i'), ('v', 'u')]:
		syls = _try_unconsonantify(frm, to, t, t_list, syls, mqdq_slen)
		if len(syls) >= mqdq_slen:
			return syls

	return syls


def _macronize_short_syl(syl):
	if len(syl)>1 and all(x in VOWELS for x in list(syl)):
		return syl

	l = [x+COMBINING_MACRON if x in VOWELS else x for x in list(syl)]
	return ''.join(l)


def _syllabify_text(w, t):

	# w is the MQDQ word blob (I need the metadata), t is the raw text,
	# cleaned of punctuation.

	# Irritatingly, the MQDQ texts use V for capital
	# 'u' (even when not consonantal)
	t = t.translate(VU)

	mqdq_slen = len(w['sy'])/2
	if w.has_attr('mf') and (w['mf']=="SY" or w['mf']=="PE"):
		# note to self, I also do this for prodelision because the
		# word level syllabification of 'est' has one syllable
		# but the MQDQ scansion records it as having 0 (it
		# vanishes)
		mqdq_slen += 1

	# a very few words are scanned strangely. In those cases, if
	# the mqdq_slen matches the weird scansion, just return it.
	# these are mostly unusual contractions
	if t.lower() in SCAN_HAX:
		hax = SCAN_HAX[t.lower()][:]
		if len(hax)==mqdq_slen:
			# copy the capitalisation of t
			# still no good for INSCRIPTION CASE
			hax[0] = t[0] + hax[0][1:]
			return hax

	t_list = list(t)

	# Whether we have a length mismatch or not, always convert
	# uV at the start of a line or VuV anywhere
	u_indices = [m.start() for m in re.finditer(r'[uU]', t)]
	for idx in u_indices:
		if idx==0 and len(t_list)>1 and t_list[idx+1] in VOWELS_NO_U:
			t_list[0] = t_list[0].translate(UV)
		if idx==len(t_list)-1:
			# never convert last u
			continue
		if t_list[idx+1] in VOWELS_NO_U and t_list[idx-1] in VOWELS:
			t_list[idx] = t_list[idx].translate(UV)

	syls =  S.syllabify(''.join(t_list))
	# Now, if we don't match the MQDQ length, try to fix things up
	# using various strategies
	while len(syls) > mqdq_slen:
		old_syls = syls
		syls = _try_shrink(w, syls, t, t_list, mqdq_slen)
		if len(syls) == len(old_syls):
			# we're not getting anywhere, give up.
			break
	while len(syls) < mqdq_slen:
		old_syls = syls
		syls = _try_grow(w, syls, t, t_list, mqdq_slen)
		if len(syls) == len(old_syls):
			break

	if len(syls)==mqdq_slen:
		try:
			return [Syl(s) for s in syls]
		except Exception as e:
			print(w)
			raise e
	else:
		raise ValueError("Length mismatch syllabifying %s (have %s, want length %d)" % (w.text, '.'.join(syls), mqdq_slen))

def _punct_split(w):

	# This will return an array pre_punc, syls, post_punc

	# python spit will yield a blank string at each end where
	# these match, eg ['', '(', 'huc', ')', '']
	ary = PUNCT_SPLIT.split(w.text)
	l = len(ary)
	if l == 5:
		return [ary[1], ary[2], ary[3]]
	elif l == 3:
		# one punctuation
		if len(ary[0])==0:
			# at the start
			return [ary[1], ary[2], '']
		else:
			return ['', ary[0], ary[1]]
	else:
		return ['', ary[0], '']

def _syllabify_word(w):

	# Word is a dataclass, the constructor is prepunct, syl_array, postpunct
	pre,txt,post = _punct_split(w)
	return Word(pre, _syllabify_text(w,txt), post, w)


def _elide(s1, s2):

	# strip final nasals, but not all nasals
	s1 = s1.rstrip('mMnN')
	s1 = s1.rstrip(VOWELS)

	if len(s1)==0:
		return s2
	if s1 and s1 in 'qQ':
		# special-case, don't strip u after q because really
		# it's just one phoneme
		s1 += 'u'

	# strip 'h' at the start of the syllable on the right
	s2 = s2.lstrip('hH')

	# and fix up capitalisation (elision before a proper noun etc)
	if s2[0].isupper():
		s2 = s2[0].lower() + s2[1:]
		s1 = s1.capitalize()
	return Syl(s1 + s2)


def _phonetify(w) -> Word:

	scan_syls = re.findall('..', w.mqdq['sy'])
	slen = len(w.syls)
	if '_' in w.syls:
		slen-=1
	for idx, s_syl in enumerate(scan_syls):
		if idx+1 > slen:
			break

		# phoenetic representation, but not 'real' IPA	
		try:
			w.syls[idx] = w.syls[idx].translate(VW).translate(YU).translate(CK)
		except Exception as e:
			print(w)
			raise e

		# x at the start of a non-initial syllable becomes the cluster 'ks'
		# and the k moves backwards I.xi.on -> Ik.si.on
		if idx > 0 and w.syls[idx].startswith('x'):
			w.syls[idx-1]+='k'
			w.syls[idx] = 's' + w.syls[idx][1:]

		if w.syls[idx].endswith('x'):
			w.syls[idx] = w.syls[idx][:-1] + 'ks'

		# remaining double consonants at the start of a syllable get compressed
		# geminate consonants in general should already have been split
		dc = DBL_CONS.match(w.syls[idx])
		if dc:
			w.syls[idx] = dc.group(1) + w.syls[idx][2:]

		# qu becomes 'kw', although really
		# it should probably be more like rounded k (kʷ) per Allen
		if re.match('qu', w.syls[idx], flags=re.I):
			w.syls[idx] = re.sub('qu', 'kw', w.syls[idx])
			w.syls[idx] = re.sub('Qu', 'Kw', w.syls[idx])
			w.syls[idx] = re.sub('QU', 'KW', w.syls[idx])

		# gn was pronounced as a palatalised nasal, which I'm writing as nj	
		# TODO should also do this after elision somehow
		# magnum Alciden -> man._ Jal.ki.den
		if len(w.syls) > idx+1 and w.syls[idx].endswith('g') and w.syls[idx+1].startswith('n'):
			# mag.nus -> man.jus
			w.syls[idx] = w.syls[idx][:-1]+'n'
			w.syls[idx+1] = 'j' + w.syls[idx+1][1:]

		# the cluster 'ph' / 'kh' represent aspirated p (pʰ/kʰ) so these should not be split
		# across syllable boundaries. Can't change 'ph' to 'f' because it's
		# incorrect (Allen, Vox Latina, 26)
		#
		# I am removing the 'h'. Arguably wrong. Are p/pʰ phonemically different in Latin?
		# (pʰ is really only in Greek imports...)
		#
		# I'm also resolving 'rh' and 'rrh' which were introduced to transcribe A.Gk.ῤ and ῤῥ
		# which were 'voiceless r'. Allen (33) doubts if these were ever pronounced unvoiced.
		if len(w.syls) > idx+1 and w.syls[idx][-1] in 'pkr' and w.syls[idx+1].startswith('h'):	
			# we don't include 't' here because posthabita is post.ha.bi.ta (aspiration on the 'a')
			# TODO: this means eg Teuthra is still not correct (Teut.hra, want Teut.ra) but it's
			# more correct this way than de-aspirating a ton of vowels
			w.syls[idx+1] = w.syls[idx][-1] + w.syls[idx+1][1:]
			w.syls[idx] = w.syls[idx][:-1]

		# resolve aspirated consonants at the start and end of syllables
		if re.match('[pkrt]h', w.syls[idx], flags=re.I):
			w.syls[idx] = w.syls[idx][0] + w.syls[idx][2:]
		if re.search('[pkrt]h$', w.syls[idx], flags=re.I):
			w.syls[idx] = w.syls[idx][:-1]

		# this handling is still not perfect, but hopefully the remaining errors are
		# confined to irritating Greek names and loanwords.

	for idx, s_syl in enumerate(scan_syls):
		if idx+1 > slen:
			# safety valve
			break
		if len(w.syls[idx]) < 3 and s_syl[-1] in 'AT':
			w.syls[idx] = _macronize_short_syl(w.syls[idx])

	# My syllable string after parsing looks like 5A5b5c`6A6X etc
	# which is converted to ['5A', '5b', '5c', '`', '6A', '6X']
	sarr = re.findall('[1-9ATXbc]{1,2}|`|_', la._get_syls_with_stress(w.mqdq))
	if '`' in sarr:
		w.syls[sarr.index('`')] = '`' + w.syls[sarr.index('`')]

	if len(w.syls)>0 and w.syls[-1][-1] in 'mM':
		# elision has taken place by now, so final m does not
		# precede a vowel, so it should be dropped.
		w.syls[-1] = w.syls[-1][:-1]
		# if what's left ends with a macron, it was a vowel
		# that now needs to be nasalised (tilde) instead
		if w.syls[-1].endswith(COMBINING_MACRON):
			w.syls[-1] = w.syls[-1][:-1]
		if w.syls[-1][-1] in VOWELS:
			w.syls[-1] = w.syls[-1] + COMBINING_TILDE

	# ensure that the syls are turned into the fancy subclass, in case they got
	# made into normal strings while messing around above.
	w.syls = [Syl(s) for s in w.syls]

	return w


def syllabify_line(l) -> List[Word]:

	try:
		line = [_syllabify_word(w) for w in l('word')]
	except Exception as e:
		print(l)
		raise e

	res = []

	# resolve elision first, at the line level
	for idx, w in enumerate(line):
		if w.mqdq.has_attr('mf'):
			# synalepha ie 'normal' elision here
			if w.mqdq['mf']=='SY':

				try:
					elided = _elide(w.syls[-1], line[idx+1].syls[0])
				except IndexError as e:
					print("IndexError while eliding - check the text.")
					print(l)
					raise e

				w.syls[-1] = '_'
				line[idx+1].syls[0] = elided
				# drop final punctuation, elision over punct is silly
				w.post_punct=''
			# prodelision, which 'elides backwards' (puella est -> puellast)
			elif w.mqdq['mf']=='PE':
				line[idx-1].syls[-1] = line[idx-1].syls[-1].rstrip('mM') + w.syls[0].lstrip(VOWELS)
				w.syls[0] = '_'
				
	# now do phonetics at the word level
	return [_phonetify(w) for w in line]

NUCLEUS_SCORES = {
'i':{'i':1,'e':0.7, 'a':0.42, 'o':0.42, 'u':0.4, 'ü':0.5},
'e':{'i':0.7,'e':1, 'a':0.6, 'o':0.6, 'u':0.42, 'ü':0.5},
'a':{'i':0.42,'e':0.6, 'a':1, 'o':0.6, 'u':0.42, 'ü':0.4},
'o':{'i':0.42,'e':0.6, 'a':0.6, 'o':1, 'u':0.7, 'ü':0.35},
'u':{'i':0.4,'e':0.42, 'a':0.42, 'o':0.7, 'u':1, 'ü':0.6},
'ü':{'i':0.5,'e':0.5, 'a':0.4, 'o':0.35, 'u':0.6, 'ü':1},
}

FRIC = {'s','f'}
UNV_STOP = {'k','t','p'}
V_STOP = {'g','d','b'}
STOP = UNV_STOP | V_STOP
ALVEOLAR = {'t','d','s','z'}
VELAR = {'g','k'}
BILAB = {'p','b','w'}
SON = {'n','m','l','r'}
NAS = {'n', 'm'}
CONT = SON | NAS | FRIC | {''}

CONS_CLOSE = {
'' : FRIC | UNV_STOP | SON,
't': ALVEOLAR | STOP,
'd': STOP,
's': FRIC | (UNV_STOP - BILAB),
'f': FRIC,
'k': STOP - BILAB,
'h': STOP, # only occurs as kh and th which are both stops
'g': STOP - BILAB,
'r': SON,
'n': SON,
'm': CONT, # m isn't really there, it nasalises the vowel
'l': SON,
'b': (V_STOP | BILAB) - VELAR, # b--g seems too far away
'p': STOP - VELAR,
'x': UNV_STOP | FRIC
}


def _syl_rhyme(s1, s2):
	if s1.nucleus=='' or s2.nucleus=='':
		return 0
	try:
		# Basic score for the final vowel
		nuc1 = s1.nucleus.translate(DEMACRON)[-1].lower()
		nuc2 = s2.nucleus.translate(DEMACRON)[-1].lower()
		score = NUCLEUS_SCORES[nuc1][nuc2]

		# One's a dipthong and one isn't
		if len(nuc1) != len(nuc2):
			score *= 0.7
		elif nuc1[0]!=nuc2[0] and score==1:
			# dipthongs but first vowel not equal
			score *= 0.7

		# apply bonuses or penalties for the coda
		try:
			last1 = s1.coda[-1].lower()
		except IndexError:
			last1 = ''

		try:
			last2 = s2.coda[-1].lower()
		except IndexError:
			last2 = ''

		# print("Nucleus: %f" % score)

		if len(s1.coda) + len(s2.coda) > 2:
			# at least one cluster
			if s1.coda == s2.coda:
				score *= 1.3
			else:
				score *= 0.6 
		elif s1.coda==s2.coda:
			score *= 1.3
		elif last2 in CONS_CLOSE[last1] or last1 in CONS_CLOSE[last2]:
			score *= 0.9
		else:
			score *= 0.6

		# Perfect onset match gives a bonus
		if s1.onset==s2.onset and s1.onset != '':
			score *= 1.3

		if score > 1:
			score = 1
		# print(score)
		return score
	except Exception as e:
		print(s1)
		print(s2)
		raise e


def score(l1, l2):

	w1, w2 = syllabify_line(l1)[-1], syllabify_line(l2)[-1]
	#print("%s -- %s" % (''.join(w1.syls),''.join(w2.syls)))
	try:
		s_idx1 = next(i for i,v in enumerate(w1.syls) if v.stressed)
	except StopIteration:
		s_idx1 = 0
	except Exception as e:
		print(w1.syls)
		print(w2.syls)
		raise e

	try:
		s_idx2 = next(i for i,v in enumerate(w2.syls) if v.stressed)
	except StopIteration:
		s_idx2 = 0
	except Exception as e:
		print(w1.syls)
		print(w2.syls)
		raise e

	# calculate the rhyme score on the stressed syllable
	score = _syl_rhyme(w1.syls[s_idx1], w2.syls[s_idx2])

	# Now the rhyme on the remainder. In Latin, in theory,
	# the final syllable is not stressed, so there should be
	# at least one extra, but there _are_ exceptions.

	# For uneven lengths, if we have Xx vs Yyy then compare 
	# the two final syllables, slurring over like 
	# UN.der.ground // COM.pound
	
	if len(w1.syls[s_idx1:])>0 and len(w2.syls[s_idx2:])>0:
		score += _syl_rhyme(w1.syls[-1], w2.syls[-1])
	return score


def combined_score(ll):

	# the combined score of a set (for now) is just the
	# mean of the pairwise scores.

	scores = [score(a,b) for a,b in combinations(ll,2)]
	return sum(scores)/len(scores)


def find_end_rhymes(ll, gather_thresh=1.4, global_thresh=1.65, min_lines=4):

	rhyming = False
	working_set, final_set = [], []
	        
	for idx in range(len(ll)-1):
	    if rhyming:
	        if score(ll[idx], ll[idx+1]) >= gather_thresh:
	            working_set.append(ll[idx+1])
	        else:
	            rhyming = False
	            if len(working_set) >= min_lines:
	                if combined_score(working_set) >= global_thresh:
	                	final_set.append(working_set)
	            working_set = []
	    else:
	        if score(ll[idx], ll[idx+1]) >= gather_thresh:
	            working_set = ll[idx:idx+2]
	            rhyming = True
	        else:
	            continue
	return final_set


def find_abab(ll, thresh=1.65):

	final_set = []

	idx = 0
	while idx < len(ll)-3:
		a1, a2 = ll[idx], ll[idx+2]
		b1, b2 = ll[idx+1], ll[idx+3]
		if score(a1,a2)>=thresh and score(b1,b2) >= thresh:
			# try and extend to six. Eights will find themselves.
			if idx < len(ll)-5:
				if score(a2,ll[idx+4]) >=thresh and score(b2,ll[idx+5]) >= thresh:
					final_set.append(ll[idx:idx+6])
					idx+=2
				else:
					final_set.append(ll[idx:idx+4])
			else:
				final_set.append(ll[idx:idx+4])
			idx+=4
		else:
			idx+=1

	return final_set


def find_abba(ll, thresh=1.65):

	final_set = []

	idx = 0
	while idx < len(ll)-3:
		a1, a2 = ll[idx], ll[idx+3]
		b1, b2 = ll[idx+1], ll[idx+2]
		if score(a1,a2)>=thresh and score(b1,b2) >= thresh:
			final_set.append(ll[idx:idx+4])
			idx+=4
		else:
			idx+=1

	return final_set

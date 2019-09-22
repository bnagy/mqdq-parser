from mqdq.cltk_hax.syllabifier import Syllabifier
import re
from mqdq import utils
from mqdq import line_analyzer as la
import string

S = Syllabifier()
VOWELS = "aeiouyAEIOUY"
ELISION_DROP = VOWELS + 'mM'
VOWELS_NO_U = "aeioyAEIOY"
UV = str.maketrans({'u':'v', 'U':'V'})
VW = str.maketrans({'v':'w', 'V':'W'})
CK = str.maketrans({'c':'k', 'C':'K'})
YU = str.maketrans({'y':'ü', 'Y':'Ü'})

VU = str.maketrans({'V':'U'})
IJ = str.maketrans({'i':'j', 'I':'J'})
DIPTHONGS = ['ae', 'oi', 'oe', 'eu', 'eo', 'ei', 'au', 'ui', 'ue']
DEPUNCT = str.maketrans('', '', string.punctuation)
PERMISSIBLE_ERRORS = ['dehinc', 'semihominis', 'proinde']
PUNCT_SPLIT = re.compile(r'([%s]+)' % re.escape(string.punctuation))

def _try_form_dipthong(d, t, t_list, syls, mqdq_slen):

	d1 = tuple("%s%s" % (d[0], d[0].capitalize()))
	d2 = tuple("%s%s" % (d[1], d[1].capitalize()))

	# this regegx seems redundant, but it makes sure we don't 
	# drop off the edge of the string
	if re.search(d, t, flags=re.I):
		end_indices = [i for i, x in enumerate(syls) if x.endswith(d1)]
		for idx in end_indices:
			if syls[idx+1].startswith(d2):
				syls[idx+1] = syls[idx]+syls[idx+1]
				syls = syls[:idx] + syls[idx+1:]
				if len(syls) <= mqdq_slen:
					return syls
	return syls

def _try_split_dipthong(d, t, t_list, syls, mqdq_slen):

	d1 = "%s%s" % (d[0], d[0].capitalize())

	if re.search(d, t, flags=re.I):
		indices = [i for i, x in enumerate(syls) if re.search(d, x, flags=re.I)]
		for idx in indices:
			pre,x,post = re.split("([%s])" % d1, syls[idx])
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
	
	for (frm, to) in [('u', 'v'), ('i', 'j')]:
		syls = _try_consonantify(frm, to, t, t_list, syls, mqdq_slen)
		if len(syls) <= mqdq_slen:
			return syls

	# Now try to form various dipthongs to drop a syllable

	for d in DIPTHONGS:
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

	l = [x+u'\u0304' if x in VOWELS else x for x in list(syl)]
	return ''.join(l)

def _syllabify_text(w, t):
	# Irritatingly, the MQDQ texts use V for capital
	# 'u' (even when not consonantal)
	t = t.translate(VU)

	mqdq_slen = len(w['sy'])/2
	if w.has_attr('mf') and (w['mf']=="SY" or w['mf']=="PE"):
		mqdq_slen += 1

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
	if len(syls) > mqdq_slen:
		syls = _try_shrink(w, syls, t, t_list, mqdq_slen)
	if len(syls) < mqdq_slen:
		syls = _try_grow(w, syls, t, t_list, mqdq_slen)

	scan_syls = re.findall('..', w['sy'])

	if len(syls)==mqdq_slen:
		return syls
	else:
		if w.text.translate(DEPUNCT).lower() in PERMISSIBLE_ERRORS:
			return syls
		raise ValueError("Length mismatch syllabifying %s (have %s, want length %d)" % (w.text, '.'.join(syls), mqdq_slen))

def _syllabify_word(w):

	# This will return an array pre_punc, syls, post_punc

	# python spit will yield a blank string at each end where
	# these match, eg ['', '(', 'huc', ')', '']
	ary = PUNCT_SPLIT.split(w.text)
	l = len(ary)
	if l == 5:
		return [ary[1], _syllabify_text(w,ary[2]), ary[3]]
	elif l == 3:
		# one punctuation
		if len(ary[0])==0:
			# at the start
			return [ary[1], _syllabify_text(w,ary[2]), '']
		else:
			return ['', _syllabify_text(w,ary[0]), ary[1]]
	else:
		return ['', _syllabify_text(w,ary[0]), '']


def _elide(s1, s2):
	s1 = s1.rstrip('mMnN')
	s1 = s1.rstrip(VOWELS)
	if len(s1)==0:
		return s2
	if s1 and s1 in 'qQ':
		s1 += 'u'
	s2 = s2.lstrip('hH')
	if s2[0].isupper():
		s2 = s2[0].lower() + s2[1:]
		s1 = s1.capitalize()
	return s1 + s2

def _phonetify(syls, w):
	scan_syls = re.findall('..', w['sy'])
	slen = len(syls)
	if '_' in syls:
		slen-=1

	for idx, s_syl in enumerate(scan_syls):	
		if len(syls[idx]) < 3 and s_syl[-1] in 'AT':
			syls[idx] = _macronize_short_syl(syls[idx])
		syls[idx] = syls[idx].translate(VW).translate(YU).translate(CK)
		if idx > 0 and syls[idx].startswith('x'):
			syls[idx-1]+='k'
			syls[idx] = 's' + syls[idx][1:]
		if syls[idx].startswith('qu'):
			syls[idx] = 'kw' + syls[idx][2:]
		if len(syls) > idx+1 and syls[idx].endswith('g') and syls[idx+1].startswith('n'):
			syls[idx] = syls[idx][:-1]+'n'
			syls[idx+1] = 'j' + syls[idx+1][1:]
		# the cluster 'ph' represents an aspirated p so these should not be split
		# across syllable boundaries. Can't change 'ph' to 'f' because it's
		# incorrect (Allen, Vox Latina, 26)
		if len(syls) > idx+1 and syls[idx].endswith('p') and syls[idx+1].startswith('h'):
			syls[idx] = syls[idx][:-1]
			syls[idx+1] = 'p' + syls[idx+1]

	# My syllable string after parsing looks like 5A5b5c`6A6X etc
	# which is converted to ['5A', '5b', '5c', '`', '6A', '6X']
	sarr = re.findall('[1-9ATXbc]{1,2}|`|_', la._get_syls_with_stress(w))
	if '`' in sarr:
		syls[sarr.index('`')] = '`' + syls[sarr.index('`')]

	return syls


def syllabify_line(l):

	# TODO this is unreadable dreck. Objectify the line object
	# and make accessors.
	line = [(w,_syllabify_word(w)) for w in l('word')]
	res = []
	for idx, (w,ss) in enumerate(line):
		# reminder: ss is [prepunc, syls, postpunc]
		if w.has_attr('mf'):
			if w['mf']=='SY':
				elided = _elide(ss[1][-1], line[idx+1][1][1][0])
				ss[1][-1] = '_'
				line[idx+1][1][1][0] = elided
				# drop final punctuation, elision over punct is silly
				ss[-1]=''
			elif w['mf']=='PE':
				line[idx-1][1][1][-1] = line[idx-1][1][1][-1].rstrip('mM') + ss[1][0].lstrip(VOWELS)
				ss[1][0] = '_'
				

	line = [x[1][0]+'.'.join(_phonetify(x[1][1],x[0]))+x[1][2] for x in line]
	return ' '.join(line)
	







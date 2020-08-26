from collections import namedtuple, UserString
from dataclasses import dataclass
from typing import List, Any
import bs4
from bs4 import BeautifulSoup
from mqdq import rhyme
import seaborn as sns

VOWEL_ORDER = {'i':0, 'e':1, 'a':2, 'ü':3, 'u':4, 'o':5}
PALETTE = sns.hls_palette(55, s=.5, l=.65).as_hex()[:36]

class Syl(str):

	def __init__(self, s, **kwargs):
		if s != '_':
			self.stressed = (s[0]=='`') # bool
			try:
				if self.stressed:
					self.onset,self.nucleus,self.coda = rhyme.ONC.split(s[1:])
				else:
					self.onset,self.nucleus,self.coda = rhyme.ONC.split(s)

				if self.coda.startswith(('m','n')):
					self.nucleus += rhyme.COMBINING_TILDE

			except Exception as e:
				raise ValueError("Couldn't split %s: %s" % (s, e))
		else:
			self.onset,self.nucleus,self.coda = '','',''
			self.stressed = False
		super().__init__(**kwargs)

	@property
	def main_vowel(self):
		if self.nucleus:
			return self.nucleus.translate(rhyme.DEMACRON).lower()[-1]
		return ''


@dataclass
class Word:
	pre_punct: str
	syls: List[Syl]
	post_punct: str
	mqdq: bs4.element.Tag
	color: str = ''
	best_match: float = 0.0

	# quality of life shortcuts
	# return an empty string and not None so that
	# we can always safely do startswith and endswith
	@property
	def wb(self):
		try:
			return self.mqdq['wb']
		except KeyError:
			return ''

	@property
	def mf(self):
		try:
			return self.mqdq['mf']
		except KeyError:
			return ''

	@property
	def mqdq_sy(self):
		try:
			return self.mqdq['sy']
		except KeyError:
			return ''

	@property
	def stress_idx(self):
		try:
			idx = next(i for i,v in enumerate(self.syls) if v.stressed)
		except StopIteration:
			idx = 0
		return idx

	@property
	def stressed_syllable(self):
		try:
			return self.syls[self.stress_idx]
		except IndexError:
			return None

	@property
	def post_stress(self):
		# python trix - this is safe even when the stress is
		# on the final syllable because the slice will be an
		# empty list
		return self.syls[self.stress_idx+1:]

	def get_color(self):
	    last = self.post_stress[-1:]
	    stress = self.stressed_syllable
	    if last:
	        last_vowel = last[-1].main_vowel
	        color_idx = VOWEL_ORDER[last_vowel]*6
	        color_idx += VOWEL_ORDER[stress.main_vowel]
	    elif stress:
	        color_idx = VOWEL_ORDER[stress.main_vowel]*6
	    else:
	        return None

	    return PALETTE[color_idx]


class Line(list):

	def __init__(self, *args, **kwargs):
		self.words = args[0]
		self.metre = args[1]
		super(Line, self).__init__(args[0])

	@property
	def midword(self):
		mid = [w for w in self.words if w.mqdq_sy.endswith('3A')]
		if len(mid) > 1:
			raise ArgumentError("Two words ending the third foot??")
		elif len(mid)== 0:
			return None
		else:
			return mid[0]

	@property
	def midword_idx(self):
		for i,w in enumerate(self.words):
			if w.mqdq_sy.endswith('3A'):
				return i
		return None		

	@property
	def antepenult(self):
		if self.midword_idx and self.midword_idx+3 >= len(self):
			return None
		if len(self) < 6:
			return None
		return self[-3]

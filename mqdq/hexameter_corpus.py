from bs4 import BeautifulSoup
from collections import Counter
import re
import numpy as np
import pandas as pd
from mqdq import utils
from mqdq import rhyme
from mqdq import line_analyzer as la
import string

WORKS = [
	('Vergil', 'Aeneid', 'VERG-aene.xml'),
	('Ovid', 'Metamorphoses', 'OV-meta.xml'),
	('Silius', 'Punica', 'SIL-puni.xml'),
	('Statius', 'Thebaid', 'STAT-theb.xml'),
	('Lucan', 'Pharsalia', 'LVCAN-phar.xml'),
	('Juvenal', 'Satires', 'IVV-satu.xml'),
]

def geezit_corpus():

	df = pd.DataFrame()

	for auth,title,fn in WORKS:
		
		with open(fn) as fh:
			soup = BeautifulSoup(fh,"xml")

		this_work=[]
		for d_idx, d in enumerate(soup('division')):
			ll = utils.clean(d('line'))
			for l_idx, l in enumerate(ll):
				try:
					ln = int(l['name'])
				except ValueError:
					# sometimes we have lines called '547a' etc
					# NB: this might leave duplicate line numbers in any
					# given book!
					ln = int(''.join(x for x in l['name'] if x.isdigit()))
				this_work.append({
					'LN':ln,
					'Book':d_idx+1,
					'Work':title,
					'Author':auth,
					'XML':l,
					})

		df = df.append(pd.DataFrame(this_work)).reset_index(drop=True)

	# set the author of the Additamentum rows to PsSilius

	df.loc[
		(df['Book']==8)
		& (df['Author']=='Silius')
		& (df['LN'] >= 144)
		& (df['LN']<224), 'Author'
	] = 'PsSilius'

	return df



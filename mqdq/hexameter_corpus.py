from bs4 import BeautifulSoup
from collections import Counter
import re
import numpy as np
import pandas as pd
from mqdq import utils
from mqdq import rhyme
from mqdq import line_analyzer as la
import string
import pathlib
from tqdm import tqdm as tqdm_base
import sys

WORKS = [
	('Vergil', 'Aeneid', 'VERG-aene.xml'),
	('Ovid', 'Metamorphoses', 'OV-meta.xml'),
	('Silius', 'Punica', 'SIL-puni.xml'),
	('Statius', 'Thebaid', 'STAT-theb.xml'),
	('Lucan', 'Pharsalia', 'LVCAN-phar.xml'),
	('Juvenal', 'Satires', 'IVV-satu.xml'),
]

# this is hax to stop tqdm from going crazy sometimes
# when a Jupyter notebook is interrupted and an old
# instance goes stale.
# orig: https://github.com/tqdm/tqdm/issues/375#issuecomment-522182387
def tqdm(*args, **kwargs):
    if hasattr(tqdm_base, '_instances'):
        for instance in list(tqdm_base._instances):
            tqdm_base._decr_instances(instance)
    return tqdm_base(*args, **kwargs)

def geezit_corpus():

	df = pd.DataFrame()

	for auth,title,fn in tqdm(WORKS, file=sys.stdout, ncols=80):
		
		fn = pathlib.Path(__file__).parent / fn
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

# TODO OK, maybe just this once I could refactor this as an object
def vectorize_prosody(corp, by='Author'):
	vecs = la.chunked_features(corp['XML'], n=1)
	vecs[by] = corp[by]
	return vecs

def rechunk(df, n, by='Author', rand=False, seed=None, feats=la.ALL_FEATURES):
	chunked = []
	rng = np.random.RandomState(seed=seed)
	for idx, subdf in df.groupby(by, sort=False):
		if rand:
			subdf = subdf.sample(frac=1, random_state=rng)
		chunks = la._chunk_mean(subdf, n=n)
		chunks[by]=subdf.iloc[0][by]
		chunked.append(chunks)

	df = pd.concat(chunked)
	df = df.reset_index(drop=True)
	return df

from bs4 import BeautifulSoup
import random
from mqdq import line_analyzer as la
from mqdq import utils
import pandas as pd
import numpy as np
import scipy as sp
from scipy.stats import chi2

def explain(x, dist):

    """Calculate the Mahalanobis distance of a vector x from
    the distribution dist. This also returns a contribution vector
    which shows how much each feature contributes to the distance.

    You may notice that some features in that vector have negative values.
    The vector itself will always sum to a non-negative value, because
    of the nature of the calculation (the co-variance matrix is positive
    semi-definite). The negative value features occur when there is
    correlation. For example, if feature A scores contributes 20 to the
    distance, but it is correlated with feature B, then B might have a
    negative value to compensate for 'double counting' those features.

    The interpretability of the contribution vector is open to debate. It
    is not clear what statistical meaning the individual values have, but
    in my tests they have reflected what appear to be 'real' feature effects.

    Args:
        x (ideally a pandas.DataFrame): The observation to consider
        dist (pandas.DataFrame) : The distribution to take the distance from

    Returns:
        f (pandas.DataFrame): Feature contribution vector
        m (float64): Mahalanobis distance squared. m is the sum of f.
        p: The p-value calculated from m, assuming it follows a chi-square
           distribution, and using the default degrees of freedom (dim(dist)-1) 
    """

    # hat-tip: https://www.machinelearningplus.com/statistics/mahalanobis-distance/
    # NB: this produces the SQUARE of the distance ([x-m].C^{-1}.[x-m]^T)
    # which is what we want if we're claiming that the chi-sq distribution applies

    x_minus_mu = x - np.mean(dist)
    cov = np.cov(dist.values.T)
    inv_covmat = sp.linalg.inv(cov)
    left_term = np.dot(x_minus_mu, inv_covmat)

    # for the normal Mahalanobis distance we would take the dot product here
    # but instead we multiply the vectors pointwise (as in .dot) but don't add
    # up the entries. This lets us see how much each column contributes to the
    # distance. NB I have NO IDEA what the statistical meaning of this is, since
    # we've moved one vector into some weird space defined by the covariance matrix.
    # It seems to have explanatory meaning, though.

    v = left_term*x_minus_mu

    m = np.dot(left_term, x_minus_mu.T)[0]
    p = 1 - chi2.cdf(m, len(x.columns)-1)[0]

    return (v, m[0], p)

def chunk_explain(samp, dist, n=5000, chunksz=None, feats=la.ALL_FEATURES, seed=None, rd=None):

    """Take a sample and a distribution, and test the Mahalanobis distance
    of the sample against a randomly sampled distribution drawn from dist.

    The ideal dist size is tricky to determine theoretically, but you can
    just do empirical tests and see when your results start to stabilise.

    If rd is supplied, the dist parameter is ignored.

    Args:
        samp (pandas.DataFrame): Sample (m rows x n features)
        dist (pandas.DataFrame): Comparison distribution
        n (int, default=5000): Number of samples to draw
        chunksz (int, default=len(samp)): Chunk size to use
        seed (int, optional): seed the PRNG for the shuffling.
        feats (list, default=la.ALL_FEATURES): Features to use
        rd (pandas.DataFrame): Pregenerated random sampled distribution

    Returns (as per explain):
        f (pandas.Series): Feature contribution vector (sorted)
        m (float64): Mahalanobis distance squared. m is the sum of f.
        p: The p-value calculated from m, assuming it follows a chi-square
           distribution, and using the default degrees of freedom (dim(dist)-1)     
    """

    s = samp[feats]
    d = dist[feats]
    if not chunksz:
        chunksz = len(s)

    if rd is None:
        rand_dist = _create_sampled_dist(d, chunksz, n, seed)
    else:   
        rand_dist = rd[feats]

    samp_centroid = la._chunk_mean(s, len(s))
    v,m,p = explain(samp_centroid, rand_dist)
    return( m, p, v.mean().sort_values(ascending=False) )

def lazy_compare(samp, dist, n=5000, chunksz=None, feats=la.ALL_FEATURES, seed=None, rd=None):

    """Print a quick comparison of a sample against a distribution,
    using chunk_explain (cf).

    Example Output:
    ------------------------------
    M-dist 41.65,  p-value: 0.0003
    Feat     Score   Samp%   Dist%
    ------------------------------
    F2WC     14.39   0.00    11.55
    BD       8.27    35.80   50.91
    F1C      8.08    28.40   42.57
    F4SC     3.36    66.67   60.11
    F3C      2.73    87.65   84.27
    F2SC     2.51    72.84   62.79
    F3SC     2.32    79.01   81.82
    F3WC     1.05    9.88    12.24
    F4S      0.93    76.54   72.61
    SYN      0.59    51.85   44.12
    F4WC     0.39    6.17    4.88
    F3S      0.33    59.26   61.34
    F1S      0.23    43.21   50.66
    F2S      -0.12   62.96   56.32
    F4C      -1.68   64.20   60.71
    F2C      -1.74   82.72   78.39
    ------------------------------

    Args (as per chunk_explain):
        samp (pandas.DataFrame): Sample (m rows x n features)
        dist (pandas.DataFrame): Comparison distribution
        n (int, default=5000): Number of samples to draw
        seed (int, optional): seed the PRNG for the shuffling.
        feats (list, default=la.ALL_FEATURES): Features to use
        chunksz (int, default=len(samp)): Chunk size to use

    Returns:
        Nothing (prints output)
    """


    m,p,f = chunk_explain(samp, dist, n, chunksz, feats=feats, seed=seed, rd=rd)
    samp_cent = la._chunk_mean(samp,len(samp))
    dist_cent = la._chunk_mean(dist,len(dist))
    print('-'*30)
    print("M-dist %.2f,  p-value: %.4f" % (m,p))
    print("Feat \t Score \t Samp% \t Dist%")
    print('-'*30)
    for feat,score in f.iteritems():
        print("%s   %6.2f    %5.2f    %5.2f" % (feat, score, samp_cent[feat]*100, dist_cent[feat]*100))
    print('-'*30)

def _compare_latex(
    lines,
    dist,
    n=5000,
    chunksz=None,
    feats=la.ALL_FEATURES,
    seed=None,
    rd=None,
    soup=None):

    """Creates a LaTeX table with results similar to lazy_compare
    """

    preamble=r"""
\begin{tabular}{ crcc }
\toprule
\multicolumn{2}{c}{Book Ref.} & $M^{2}$ & \multicolumn{1}{c}{\textit{p}-value}\\
"""
    samp = la.distribution(lines)
    m,p,f = chunk_explain(samp, dist, n, chunksz, feats=feats, seed=seed, rd=rd)
    samp_cent = la._chunk_mean(samp,len(samp))
    dist_cent = la._chunk_mean(dist,len(dist))
    br = utils.bookrange(lines, soup)
    print(preamble, end='')
    if p < 0.0001:
        p = "$<$\\,0.0001"
    else:
        p = "%.4f" % p
    print("\\multicolumn{2}{c}{%s} & %.2f & %s \\\\" % (br, m, p))
    print("\\midrule")
    print("Feat & Score & Samp.\\,\\% & Mean\\,\\% \\\\")
    print("\\midrule")
    for feat,score in f.iteritems():
        print("\\texttt{%s} & %6.2f & %5.2f & %5.2f \\\\" % (feat, score, samp_cent[feat]*100, dist_cent[feat]*100))
    print("\\bottomrule")
    print(r"""\end{tabular}""")

def _create_sampled_dist(dist, chunksz, distsz, seed=None):

    """Take a lot of random samples from a binary distribution, each one of size
    chunksz.

    Eg: If we have a 10000 line poem, which has been converted to a binary distribution
    using la.distribution, and we wanted 5000 random samples, with each one being the
    mean of 150 random lines:

    _create_sampled_dist(poem_dist, 150, 5000)

    Args:
        dist (pandas.DataFrame): Source distribution, NOT chunked
        chunksz (int): Chunk size for each observation
        distsz (int): Number of observations to sample
        seed (int, optional): seed the PRNG for the shuffling.

    Returns:
        (pandas.DataFrame): The final distribution
    """

    if chunksz > len(dist):
        raise ValueError("Chunk size is bigger than source distribution.")

    # This is much better than doing iterative pd.concat calls.
    d = np.empty(distsz, dtype=object)
    rng = np.random.RandomState(seed)
    for x in range(distsz):
        d[x] = la._chunk_mean(dist.sample(n=chunksz, random_state=rng), chunksz)
    return pd.concat(d)

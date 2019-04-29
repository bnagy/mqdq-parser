import random
import scipy.stats
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy
from mqdq import counter_factory as cf

__A_BIT = numpy.finfo(numpy.float64).tiny
def calc_obs_exp(o_cntr, e_cntr):
    
    # Given two pattern counters, produce two arrays for the 
    # observations, one of observed counts and one of expected counts.
    # These are suitable for passing to scipy.stats.chisquare.
    #
    # In: Two counters, one of an observation, one of
    #     the 'expected' counts per pattern
    # Out: Two numeric arrays, obs and exp
    
    bins = list(set(e_cntr).union(set(o_cntr)))
    obs = []
    exp = []
    e_n = sum(e_cntr.values())
    o_n = sum(o_cntr.values())
    for b in bins:
        # how many we saw
        obs.append(o_cntr[b])
        # how many we expect based on the freqs in e_cntr
        # plus a little bit so we don't divide by zero
        exp.append((o_n*(e_cntr[b]/e_n))+__A_BIT)
    return (obs, exp, bins)

def o_e(o_cntr, e_cntr):
    
    # Given two pattern counters, produce two arrays for the 
    # observations, 
    #
    # In: Two counters
    # Out: 
    # - [obs],[exp] (ordered by the union of the counter keys)
    # - [bins] the combined counter keys
    
    bins = list(set(e_cntr).union(set(o_cntr)))
    obs = []
    exp = []
    for b in bins:
        obs.append(o_cntr[b])
        exp.append(e_cntr[b])
    return (obs, exp, bins)

def chisq(sample, comparison_data, obs_fn):

	# Compare one same with another using the given observation
	# function, and return the chi square result.
	#
	# In:
	# - sample, comparison_data - Lists of <lines>
	# - obs_fn a function that produces a Counter (the `counter_factory`
	#   module is full of these)
	# Out: a scipy.stats.chisquare Result

    comparison_counter = obs_fn(comparison_data)
    sample_counter = obs_fn(sample)
    sample_obs, sample_exp, _ = calc_obs_exp(sample_counter, comparison_counter)
    return scipy.stats.chisquare(sample_obs, sample_exp)

def chi2_contingency(sample, comparison_data, obs_fn):

	# Compare one same with another using the given observation
	# function, and return the chi square result.
	#
	# In:
	# - sample, comparison_data - Lists of <lines>
	# - obs_fn a function that produces a Counter (the `counter_factory`
	#   module is full of these)
	# Out: a scipy.stats.chi2_contingency Result

    comparison_counter = obs_fn(comparison_data)
    sample_counter = obs_fn(sample)
    sample_obs, sample_exp, _ = o_e(sample_counter, comparison_counter)
    return scipy.stats.chi2_contingency([sample_obs, sample_exp], correction=True)

def fisher(sample, comparison_data, indic_fn):

	# Perform the Fisher Exact Test, and return the probability (p-value) that
	# `sample` was drawn from the same distribution as `comparison_data` using
	# the supplied Boolean `indic_fn`
	#
	# In:
	# - sample, comparison_data: Lists of <line>s
	# Out: Float, the p-value

	# TODO this code feels janky, and we should validate the indic_fn return value
	o = indic_fn(sample)
	ot, of = o[True], o[False]
	c = indic_fn(comparison_data)
	ct, cf = c[True], c[False]
	return scipy.stats.fisher_exact([[ot,of],[ct,cf]])[1]

def random_histogram(sample, comparison_data, count, obs_fn, contig=False, seed=42):
    
    # Compare a sample with another set of data, by taking many random
    # subsamples of the comparison_data and computing the chi-square
    # statistic for each using Pearson's goodness of fit test. The chi-square
    # of the sample can then be ploted on this histogram to visualise how 'abnormal'
    # it is.
    #
    # In:
    #    sample - the sample we are analysing
    #    comparison_data - what we are comparing it to
    #    count - how many random observations to take from the comparison_data
    #    obs_fn - a function or lamba with one argument, which will return a 
    #             Counter of patterns. Eg for metre, one pattern is 'SSSS', and
    #             for ictus conflicts, one pattern is '6'
    #    contig_sample: Take samples of contiguous lines instead of at random
    # Out: A triple:
    #    output - an array of chi-square statistics to plot
    #    highlight_chisq - the chi-square stat of the sample (to highlight in the plot)
    #    sample_p - the p-value for the sample
    
    if seed:
    	random.seed(seed)

    output = []
    sample_chisq = chisq(sample, comparison_data, obs_fn)
    s_len = len(sample)
    if s_len > len(comparison_data):
        raise ValueError("Sample is longer than comparison data??")
    for i in range(count-1):
        # count-1 so that when we include our sample it's a nice round number
        if contig:
            start = random.randint(0,len(comparison_data)-(s_len+1))
            s = clean_lines[start:start+s_len]
        else:
            s = random.sample(comparison_data, s_len)
        obs, exp, _ = calc_obs_exp(obs_fn(s), comparison_counter)
        output.append(scipy.stats.chisquare(obs,exp).statistic)
    # don't forget to include our actual sample! If not, the bins
    # generated by pyplot might not include our sample chisq (eg
    # if the sample is very different to the comparison data)
    output.append(sample_chisq.statistic)
    return (output, sample_chisq.statistic, sample_chisq.pvalue)


def plot_histogram(data, sample_chisq, sample_p, title_string, facecolor='g'):
    
    # Plot the output from random_histogram.
    #
    # In:
    #   data - an array of chi-square scores
    #   sample_chisq - the score to highlight in the histogram
    #   sample_p - the p-value of the sample
    #   title_string - the plot title, as per matplotlib syntax.
    # Out: a matplotlib.pyplot
    
    x = data
    n, bins, patches = plt.hist(x, 50, density=True, facecolor=facecolor)
    # the bins array contains the left edge, then all the right edges of the bins,
    # so if we find the first entry that is greater than our score, we are in the
    # previous bin. If we don't find one, we're in the last bin.
    addit_idx = next((x[0] for x in enumerate(bins) if x[1] > sample_chisq),0) - 1
    # highlight that bar
    patches[addit_idx].set_fc('r')
    m, sd = numpy.mean(x), numpy.std(x)
    plt.xlabel('Chisq')
    plt.ylabel('Probability')
    plt.title(title_string)
    # draw in the mean etc in the top right somewhere.
    _, xmax, _, ymax = plt.axis()
    plt.text(
    	xmax*0.65,
    	ymax*0.75,
    	'$\chi^{2}=%.2f$\n$\mu=%.1f,\ \sigma=%.2f$\nn=%d, p=%.3f' % (sample_chisq,m,sd,len(x),sample_p)
    )
    return plt

def compare(a, b, counter_fn):

	# Print a comparative analysis of the counts obtained from two
	# sets of lines, using the supplied `counter_fn` (see `counter_factory`)
	# Also prints a percentage delta, which is calculated as simply
	# the frequency in a minus the frequency in b.
	#
	# In:
	# - a, b lists of <line>s
	# - counter_fn a function that takes lists of lines and returns a Counter
	# Out: (no return value) Prints the comparison

	o_ary,e_ary,bins = calc_obs_exp(counter_fn(a), counter_fn(b))
	results = list(zip(zip(o_ary,e_ary),bins))
	results.sort(key=lambda x: x[1])
	o_sum, e_sum = sum(o_ary), sum(e_ary)
	# get the length of the longest number string in the observations
	obs_max_len=max([len(str(d)) for d in o_ary])
	exp_max_len=max([len("%.2f"%d) for d in e_ary])
	for (o,e),b in results:
		try:
			diff = o/o_sum - e/e_sum
		except ArithmeticError:
			raise RuntimeError("BUG: Expected values contained a zero entry?")
		print(
			"%-*s| Obs: %*d Exp: %*.2f ( %7.2f%% )" % (
				max([len(str(s)) for s in bins])+1,
				b,
				obs_max_len,
				o,
				exp_max_len,
				e,
				diff*100,
				)
			)

def summarize(a, counter_fn):
	
	# Print a quick summary of the relative frequencies of the
	# bins in a, using the supplied counter_fn. Cf `compare`
	#
	# In:
	# - a, a list of <line>s
	# - counter_fn a function that takes lists of lines and returns a Counter
	# Out: (no return value) Prints the summary.

	ctr = counter_fn(a)
	bins = list(set(ctr))
	bins.sort()
	obs_max_len = max([len(str(d)) for d in ctr.values()])
	o_sum = sum(ctr.values())
	for b in bins:
		print(
			"%-*s| Obs: %*d ( %7.2f%% )" % (
				max([len(str(s)) for s in bins])+1,
				b,
				obs_max_len,
				ctr[b],
				ctr[b]*100/o_sum
				)
			)

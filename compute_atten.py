#!/usr/bin/env python

import sys
import numpy as np
from matplotlib import pyplot as plt
import cPickle

fp = open(sys.argv[1], 'rb')
cal_raw = cPickle.load(fp)
#for att_idx in xrange(len(raw['atten_vals'])):
#    plt.plot(raw['raw'][:, att_idx], label=f+' '+str(raw['atten_vals'][att_idx]))
fp.close()

for f in sys.argv[2:]:
    fp = open(f, 'rb')
    raw_test = cPickle.load(fp)
    for att_idx in xrange(len(raw_test['atten_vals'])):
	vals = []
	#plt.plot(raw['raw'][:, att_idx], label=f+' '+str(raw['atten_vals'][att_idx]))
	for x in xrange(raw_test['raw'][:, att_idx].shape[0]):
	    for cal_att_idx in xrange(len(cal_raw['atten_vals'])-1):
		if raw_test['raw'][:, att_idx][x] < cal_raw['raw'][:, cal_att_idx][x] and (
		    raw_test['raw'][:, att_idx][x] > cal_raw['raw'][:, cal_att_idx+1][x]):

		    dv = (raw_test['raw'][:, att_idx][x] - cal_raw['raw'][:, cal_att_idx+1][x])
		    da = (cal_raw['atten_vals'][cal_att_idx+1] - cal_raw['atten_vals'][cal_att_idx])
		    dr = (cal_raw['raw'][:, cal_att_idx][x] - cal_raw['raw'][:, cal_att_idx+1][x])
		    vals.append(cal_raw['atten_vals'][cal_att_idx+1] -  dv * da / dr)
		    
		    #print cal_raw['raw'][:, cal_att_idx][x],cal_raw['atten_vals'][cal_att_idx],raw_test['raw'][:, att_idx][x], cal_raw['raw'][:, cal_att_idx+1][x],cal_raw['atten_vals'][cal_att_idx+1], vals[-1], dv, da, dr

	plt.plot(vals, label = f+ ' ' + format(np.mean(vals), '.2f'))
	
    fp.close()


plt.legend()
plt.show()

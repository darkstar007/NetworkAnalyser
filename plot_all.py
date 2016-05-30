#!/usr/bin/env python

import sys
import numpy as np
from matplotlib import pyplot as plt
import cPickle

for f in sys.argv[1:]:
    fp = open(f, 'rb')
    raw = cPickle.load(fp)
    for att_idx in xrange(len(raw['atten_vals'])):
	plt.plot(raw['raw'][:, att_idx], label=f+' '+str(raw['atten_vals'][att_idx]))

plt.legend()
plt.show()


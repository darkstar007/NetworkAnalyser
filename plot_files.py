#!/usr/bin/env python

import numpy as np
import sys

from matplotlib import pyplot as plt

import cPickle

fp = open(sys.argv[1], 'rb')
data = cPickle.load(fp)
fp.close()

ax = plt.axes()
plt.plot(data['Latest']['freqs'], data['Mean']['data'], label='data - cal')
plt.plot(data['Latest']['freqs'], data['Cal Data']['data'], label='Raw cal')
plt.plot(data['Latest']['freqs'], data['Mean']['data'] + data['Cal Data']['data'], label='Data + cal')
ax.grid()
plt.xlabel('Freq ('+data['Latest']['freq_units']+')')
plt.ylabel('Amplitude')
plt.legend()
plt.show()



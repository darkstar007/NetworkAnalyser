#!/usr/bin/env python

import numpy as np
import sys

from matplotlib import pyplot as plt

import cPickle

ax = plt.axes()
default_cal_slope = 3.3 / (1024.0 * 16.44e-3)      # 16.44mV/dB, 3.3 V supply to ADC, 10 bit ADC
default_cal_icept = -80.0                       # 0 ADC value = -80dBm

#default_cal_slope = 1.0
#default_cal_icept = 0.0

baseline = None
for f in sys.argv[1:]:
    fp = open(f, 'rb')
    data = cPickle.load(fp)
    fp.close()
    if baseline is None:
        baseline = data['Mean']['data'] * default_cal_slope + default_cal_icept
        plt.plot(data['Latest']['freqs'], data['Mean']['data'] * default_cal_slope + default_cal_icept, label=f)
    else:
        delta = np.mean(data['Mean']['data'] * default_cal_slope + default_cal_icept - baseline)
        
        plt.plot(data['Latest']['freqs'], data['Mean']['data'] * default_cal_slope + default_cal_icept,
                 label=f + ' ('+format(delta, '+.1f')+'dB)')
        
    #plt.plot(data['Latest']['freqs'], data['Cal Data']['data'], label='Raw cal')
    #plt.plot(data['Latest']['freqs'], data['Mean']['data'] + data['Cal Data']['data'], label='Data + cal')
ax.grid()
plt.xlabel('Freq ('+data['Latest']['freq_units']+')')
plt.ylabel('Power (dBm)')
plt.legend()
plt.show()



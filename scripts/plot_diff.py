#!/usr/bin/env python

import numpy as np
import sys

from matplotlib import pyplot as plt

import pickle

#fig = plt.figure()

ax1 = plt.subplot(211)
ax2 = plt.subplot(212, sharex=ax1)

#ax = plt.axes()

default_cal_slope = 3.3 / (1024.0 * 16.44e-3)      # 16.44mV/dB, 3.3 V supply to ADC, 10 bit ADC
default_cal_icept = -89.0                       # 0 ADC value = -80dBm

#default_cal_slope = 1.0
#default_cal_icept = 0.0

baseline = None
for f in sys.argv[1:]:
    fp = open(f, 'rb')
    data = pickle.load(fp)
    fp.close()
    if baseline is None:
        baseline = data['Mean']['data'] * default_cal_slope + default_cal_icept
        ax1.plot(data['Latest']['freqs'], data['Mean']['data'] * default_cal_slope + default_cal_icept, label=f)
    else:
        delta = data['Mean']['data'] * default_cal_slope + default_cal_icept - baseline
        
        ax1.plot(data['Latest']['freqs'], data['Mean']['data'] * default_cal_slope + default_cal_icept,
                 label=f + ' ('+format(np.mean(delta), '+.1f')+'dB)')
        ax2.plot(data['Latest']['freqs'], delta, label=f)
        
    #plt.plot(data['Latest']['freqs'], data['Cal Data']['data'], label='Raw cal')
    #plt.plot(data['Latest']['freqs'], data['Mean']['data'] + data['Cal Data']['data'], label='Data + cal')
ax1.grid()
ax2.grid()
ax1.axes.set_xlabel('Freq ('+data['Latest']['freq_units']+')')
ax2.axes.set_xlabel('Freq ('+data['Latest']['freq_units']+')')
ax1.axes.set_ylabel('Power (dBm)')
ax2.axes.set_ylabel('Delta Power (dBm)')
ax1.legend()
ax2.legend()
plt.show()



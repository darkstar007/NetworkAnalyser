#!/usr/bin/env python

import numpy as np
import cPickle
from matplotlib import pyplot as plt
import sys

atten = []
atten_delog = []
att_vals = {}
att_vals_delog = {}

for f in sys.argv[1:]:
    print f
    fp = open(f, 'rb')
    data = cPickle.load(fp)
    atten.append(-int(f.split('.')[0].split('n')[1].split('db')[0]))
    atten_delog.append(10.0 ** (atten[-1]/10.0))

    att_vals[str(atten[-1])] = data['Mean']['data'][:]
    att_vals_delog[str(atten[-1])] = 10.0 ** (data['Mean']['data'][:] / 10.0)
    dlen = data['Mean']['data'].shape[0]

for a in atten:
    plt.plot(att_vals[str(a)], label=str(a))

plt.legend()
plt.show()

deg = 1

fdata = np.zeros((dlen, deg+1))

for x in xrange(dlen):
    y = []
    for a in atten:
        y.append(att_vals_delog[str(a)][x])

    fdata[x, :] = np.polyfit(atten_delog, y, deg)

    pp = np.poly1d(fdata[x, :])

    if x > 325:
        plt.plot(10.0 * np.log10(atten_delog), 10.0 * np.log10(y), '+')
        tvals = np.arange(-50.0, 0, 0.1)
        plt.plot(tvals, 10.0 * np.log10(pp(10.0 ** (tvals / 10.0))))
        plt.show()

for d in xrange(fdata.shape[1]):
    plt.plot(fdata[:, d], label=str(d))

plt.legend()
plt.show()

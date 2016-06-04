#!/usr/bin/env python

import time
import serial
import struct
import numpy as np
import cPickle
import sys

def empty_buffer(bg7_fp):
    time.sleep(3.0)
    print 'BG7: EmptyBuffer: in waiting', bg7_fp.inWaiting()
    while bg7_fp.inWaiting() > 0:
	pants = bg7_fp.read(bg7_fp.inWaiting())
	time.sleep(1.5)
	print 'BG7: trying to empty buff', bg7_fp.inWaiting()
    print 'BG7: Finished empty_buffer'

if len(sys.argv) < 2:
    print 'Usage:   test_bg7.py  <save filename> [<atten val 1> [<atten val 2> [......]]]'
    sys.exit(1)
    
do_var_atten = False

bg7 = serial.Serial('/dev/ttyUSB0', 57600, timeout=4)
if do_var_atten:
    fp_micro = serial.Serial('/dev/ttyACM0', 115200, timeout=4)
    
time.sleep(4)

empty_buffer(bg7)

raw_data = {}


raw_data['start_freq'] = 1.32e9
raw_data['num_samples'] = 6000
raw_data['bandwidth'] = 200e6
raw_data['step_size'] = raw_data['bandwidth'] / raw_data['num_samples']
raw_data['log'] = 'x'
raw_data['cycle_count'] = 15

if do_var_atten:
    raw_data['atten_vals'] = map(int, sys.argv[2:])
else:
    raw_data['atten_vals'] = [53]
    
#raw_data['atten_vals'] = [0, 1, 2, 4, 5, 8, 10, 14, 18, 20, 24, 30]
#raw_data['atten_vals'] = [0, 1, 2, 3, 6, 10, 15, 20, 30]
#raw_data['atten_vals'] = [0, 10, 20, 30]

raw_data['raw'] = np.zeros((raw_data['num_samples'], len(raw_data['atten_vals'])))

for atten_idx in xrange(len(raw_data['atten_vals'])):
    if do_var_atten:
	fp_micro.write(str(raw_data['atten_vals'][atten_idx] * 2) + '\n')
	time.sleep(1)
	print 'Read micro',
	while fp_micro.inWaiting() > 0:
	    print fp_micro.read(),

	print 'Done read micro'

    for count in xrange(raw_data['cycle_count']):
	bg7.write('\x8f' + raw_data['log'] + format(int(raw_data['start_freq']/10.0), '09')+
		  format(int(raw_data['step_size']/10.0), '08')+
		  format(int(raw_data['num_samples']), '04'))
	
	data = bytes('')
	time.sleep(2)
    
	while bg7.inWaiting() > 0:
	    data += bg7.read(bg7.inWaiting())
	    print '  so far got', len(data)
	    time.sleep(2)
	
	time.sleep(1)
    
	print 'Got', len(data), count
	if len(data) == 4 * raw_data['num_samples']:
	    raw_data['raw'][:, atten_idx] += np.array(struct.unpack('<'+str(raw_data['num_samples'] * 2) + 'H', data)[::2])

    
raw_data['raw'] /= float(raw_data['cycle_count'])

fp_save = open(sys.argv[1], 'wb')
cPickle.dump(raw_data, fp_save)
fp_save.close()

from matplotlib import pyplot as plt

for atten_idx in xrange(len(raw_data['atten_vals'])):
    plt.plot((np.arange(raw_data['num_samples']) * raw_data['step_size'] + raw_data['start_freq'] ) / 1e9,
	     raw_data['raw'][:, atten_idx], '-+',
	     label=str(raw_data['atten_vals'][atten_idx]) + 'dB')

plt.legend()
plt.show()


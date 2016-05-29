#!/usr/bin/env python

import sys
import numpy as np


import getopt


class Cal(QObject):
    def __init__(self, start_freq, bandwidth, numpts, max_hold, bg7dev, mdev):
	QObject.__init__(self)
	self.bg7 = BG7(start_freq, bandwidth, numpts, sport=bg7dev)

	self.reset_data()

        self.bg7.measurement_progress.connect(self.measurement_progress)
        self.bg7.measurement_complete.connect(self.measurement_complete)

        self.bg7.start()

    def reset_data(self):
        self.count_data = 0
        self.raw_data = {}
        self.raw_data['Latest'] = {}
        self.raw_data['Max'] = {}
        self.raw_data['Mean'] = {}
        self.raw_data['Max']['data'] = None
        self.raw_data['Logged'] = self.bg7.log_mode
	
    def measurement_progress(self, val):
        pass
        
    def measurement_complete(self, data, start_freq, step_size, num_samples):
        print 'cback', start_freq, step_size
        #data, start_freq, step_size, num_samples = cback_data
        if data is not None:
	    if 'Cal Data' in self.raw_data.keys():
		self.raw_data['Latest']['data'] = data[:] - self.raw_data['Cal Data']['data']
	    else:
		self.raw_data['Latest']['data'] = data[:]
            self.raw_data['Latest']['freqs'] = (np.arange(num_samples) * step_size) + start_freq
            self.raw_data['Latest']['freq_units'] = 'MHz'
            if self.raw_data['Latest']['freqs'][num_samples/2] > 1e9:
                self.raw_data['Latest']['freqs'] /= 1e9
                self.raw_data['Latest']['freq_units'] = 'GHz'
            else:
                self.raw_data['Latest']['freqs'] /= 1e6

            self.curvewidget.plot.set_axis_unit(BasePlot.X_BOTTOM,
						self.raw_data['Latest']['freq_units'])
	    self.show_data('Latest')

            if self.count_data == 0:
                self.raw_data['Mean']['data'] = self.raw_data['Latest']['data'] * 1.0
            else:
                self.raw_data['Mean']['data'] = (((self.raw_data['Mean']['data'] * self.count_data) +
						  self.raw_data['Latest']['data']) / (self.count_data + 1.0))
            self.count_data += 1

            self.show_data('Mean')
        
        self.bg7.start()

def usage():
    print 'calibrate.py [options]'
    print '-r/--reset                  Reset the defaults'
    print '-s/--start_freq <freq>      Set the start frequency'
    print '-b/--bandwidth <freq>       Set the bandwidth'
    print '-n/--numpts <number>        Set the number of points in the sweep'
    print '-m/--max_hold               Turn on max hold'
    print '-d/--device <device>        Use BG7 device <device>, default /dev/ttyUSB0'
    print '-M/--micro <device>         Use teensy device <device>, default /dev/ttyUSB1'
    return

if __name__ == '__main__':
    from guidata import qapplication
    try:
        optlist,args = getopt.getopt(sys.argv[1:], 'rs:b:n:md:',
                                     ['reset', 'start_freq=', 'bandwidth=', 'numpts=',
                                      'max_hold', 'device='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    reset = False
    start_freq = None
    bandwidth = None
    numpts = None
    max_hold = None
    bg7dev = '/dev/ttyUSB0'
    mdev = '/dev/ttyUSB1'
    
    for o,a in optlist:
        if o in ('-r', '--reset'):
            reset = True
        elif o in ('-s', '--start_freq'):
            start_freq = float(a)
        elif o in ('-b', '--bandwidth'):
            bandwidth = float(a)
        elif o in ('-n', '--numpts'):
            numpts = int(a)
        elif o in ('-m', '--max_hold'):
            max_hold = True
        elif o in ('-d', '--device'):
	    bg7dev = a[:]
        elif o in ('-M', '--micro'):
	    mdev = a[:]
	
    app = qapplication()

    

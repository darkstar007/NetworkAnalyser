#!/usr/bin/env python3

import os
import os.path as osp
from guidata.qt import QtGui
from guidata.qt import QtCore
from guidata.qt.QtGui import QMainWindow, QMessageBox, QSplitter, QListWidget, QSpinBox

from guidata.qt.QtGui import QFont, QDesktopWidget, QFileDialog, QProgressBar
from guidata.qt.QtCore import QSettings, QThread, QTimer, QObject
from guidata.configtools import get_icon
from guidata.qthelpers import create_action, add_actions, get_std_icon
from guidata.utils import update_dataset
from guidata.qt.QtCore import (QSize, QT_VERSION_STR, PYQT_VERSION_STR, Qt,
                               Signal, pyqtSignal)
from guiqwt.config import _

import serial
import sys
import numpy as np
import getopt
import time

from BG7 import BG7

APP_NAME = _("Network Analyser Calibration")
VERS = '0.0.1'

class Cal(QMainWindow):
    def __init__(self, start_freq, bandwidth, numpts, bg7dev, mdev, max_cycle_count=5, atten_step=2):
	QMainWindow.__init__(self)

	self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(APP_NAME + ' ' + VERS + ' Running on ' + bg7dev + ' & ' + mdev)
        dt = QDesktopWidget()
        print(dt.numScreens(), dt.screenGeometry())
        sz = dt.screenGeometry()


        self.resize(QSize(sz.width()*6/10, 256))
        
        # Welcome message in statusbar:
        status = self.statusBar()
        status.showMessage(_("Welcome to the NetworkAnalyser Calibration application!"), 5000)
        
        self.prog = QProgressBar(self)
        self.prog.setMaximumHeight(32)
        self.mainwidget = self.prog
	self.prog.show()
	
	self.bg7 = BG7(start_freq, bandwidth, numpts, sport=bg7dev)

	self.reset_data()

	self.fp_micro = serial.Serial(mdev, 115200, timeout=4)
	
        self.bg7.measurement_progress.connect(self.measurement_progress)
        self.bg7.measurement_complete.connect(self.measurement_complete)

	self.fname = 'cal_' + str(start_freq) + '_' + str(bandwidth) + '_' + str(numpts) + '.pkl'
	
	self.max_cycle_count = max_cycle_count

	self.max_atten_val = 62
	self.atten_val = 0
	self.atten_step = atten_step
	self.update_atten()
	
        self.count_data = 0
	self.show()
	self.bg7.start()
	print('done BG7 start')
	
    def reset_data(self):
        self.raw_data = {}
        self.raw_data['Latest'] = {}
        self.raw_data['Mean'] = {}
        self.raw_data['Logged'] = self.bg7.log_mode
	
    def measurement_progress(self, val):
	print('progress', val)
        self.prog.setValue(int(val))
        
    def measurement_complete(self, data, start_freq, step_size, num_samples):
        print('cback', start_freq, step_size, num_samples)
        #data, start_freq, step_size, num_samples = cback_data
        if data is not None:
	    if 'Cal Data' in list(self.raw_data.keys()):
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

            if self.count_data == 0:
                self.raw_data['Mean'][str(self.atten_val)] = self.raw_data['Latest']['data'] * 1.0
            else:
                self.raw_data['Mean'][str(self.atten_val)] = (((self.raw_data['Mean'][str(self.atten_val)] * self.count_data) +
							       self.raw_data['Latest']['data']) / (self.count_data + 1.0))
            self.count_data += 1
	    while self.fp_micro.inWaiting() > 0:
	    	print(self.fp_micro.read())

	    if self.count_data == self.max_cycle_count:
		print('Atten', self.atten_val)
		self.atten_val += self.atten_step
		if self.atten_val > self.max_atten_val:
		    fp = open(self.fname, 'wb')
		    cPickle.dump(self.raw_data, fp)
		    fp.close()
		    sys.exit(0)
		self.update_atten()
		self.count_data = 0
		
        self.bg7.start()
	print('done BG7 start')

    def update_atten(self):
	print('Setting Atten', self.atten_val)
	self.fp_micro.write(str(self.atten_val) + '\n')
	time.sleep(1)
	while self.fp_micro.inWaiting() > 0:
	    print('Read micro', self.fp_micro.read())
	print('Done')
	
def usage():
    print('calibrate.py [options]')
    #print '-r/--reset                  Reset the defaults'
    print('-s/--start_freq <freq>      Set the start frequency')
    print('-b/--bandwidth <freq>       Set the bandwidth')
    print('-n/--numpts <number>        Set the number of points in the sweep')
    print('-d/--device <device>        Use BG7 device <device>, default /dev/ttyUSB0')
    print('-M/--micro <device>         Use teensy device <device>, default /dev/ttyUSB1')
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
    numpts = 6000
    bg7dev = '/dev/ttyUSB0'
    mdev = '/dev/ttyACM0'
    
    for o,a in optlist:
        if o in ('-r', '--reset'):
            reset = True
        elif o in ('-s', '--start_freq'):
            start_freq = float(a)
        elif o in ('-b', '--bandwidth'):
            bandwidth = float(a)
        elif o in ('-n', '--numpts'):
            numpts = int(a)
        elif o in ('-d', '--device'):
	    bg7dev = a[:]
        elif o in ('-M', '--micro'):
	    mdev = a[:]
	
    app = qapplication()

    c = Cal(start_freq, bandwidth, numpts, bg7dev, mdev)
    
    app.exec_()
    

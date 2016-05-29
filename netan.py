#!/usr/bin/env python

#
# This code is licenced under the GPL version 2, a copy of which is attached
# in the files called 'LICENSE'
#
#
# Copyright Matt Nottingham, 2015, 2016
#
#

import os
import os.path as osp
from guidata.qt import QtGui
from guidata.qt import QtCore
from guidata.qt.QtGui import QMainWindow, QMessageBox, QSplitter, QListWidget, QSpinBox

from guidata.qt.QtGui import QFont, QDesktopWidget, QFileDialog, QProgressBar
from guidata.qt.QtCore import QSettings, QThread, QTimer, QObject

from guiqwt.plot import CurveDialog, CurveWidget, BasePlot
from guiqwt.builder import make
from guiqwt.image import ImageItem
from guiqwt.styles import ImageParam
from guiqwt.annotations import AnnotatedPoint
from guiqwt.shapes import PointShape, Marker
from guiqwt.styles import AnnotationParam, ShapeParam, SymbolParam
import guidata

import guiqwt.curve
from guidata.configtools import get_icon
from guidata.qthelpers import create_action, add_actions, get_std_icon
from guidata.utils import update_dataset
from guidata.qt.QtCore import (QSize, QT_VERSION_STR, PYQT_VERSION_STR, Qt,
                               Signal, pyqtSignal)
from guiqwt.config import _
from guiqwt.plot import ImageWidget

import guiqwt.signals

from guiqwt.plot import ImageDialog
from guiqwt.builder import make

import numpy as np
import sys
import platform
import cPickle

import serial
import struct
import datetime
import time
from BG7 import BG7

APP_NAME = _("Network Analyser")
VERS = '0.3.0'

class CentralWidget(QSplitter):
    def __init__(self, parent, settings, toolbar, start_freq, bandwidth, numpts, dev):
        QSplitter.__init__(self, parent)
        self.setContentsMargins(10, 10, 10, 10)
        self.setOrientation(Qt.Vertical)
        self.curvewidget = CurveWidget(self)
        self.item = {} 
        self.points = []
        self.max_hold = False
        self.do_log = True
        self.colours = ['b', 'r', 'c', 'y']
        self.legend = None
        self.settings = settings
        
        self.curvewidget.add_toolbar(toolbar, "default")
        self.curvewidget.register_all_image_tools()
        self.curvewidget.plot.set_axis_title(BasePlot.X_BOTTOM, 'Frequency')
        
        self.addWidget(self.curvewidget)
        self.prog = QProgressBar()
        self.prog.setMaximumHeight(32)
        self.addWidget(self.prog)
        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 0)
        self.setStretchFactor(2, 1)
        self.setHandleWidth(10)
        self.setSizes([1, 5, 1])

        if start_freq == None:
            start_freq = float(self.settings.value('spectrum/start_freq', 190e6))

        if bandwidth == None:
            bandwidth = float(self.settings.value('spectrum/bandwidth', 50e6))

        if numpts == None:
            numpts = int(self.settings.value('spectrum/num_samps', 6000))
            
        print start_freq, bandwidth, numpts

        self.settings.setValue('spectrum/start_freq', start_freq)
        self.settings.setValue('spectrum/bandwidth', bandwidth)
        self.settings.setValue('spectrum/num_samps', numpts)

        
        self.bg7 = BG7(start_freq, bandwidth, numpts, sport=dev)

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
        self.prog.setValue(int(val))
        
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
        
            if self.max_hold:
                if self.raw_data['Max']['data'] == None:
                    self.raw_data['Max']['data'] = self.raw_data['Latest']['data']
                else:
                    self.raw_data['Max']['data'][:] = np.maximum(self.raw_data['Max']['data'],
								 self.raw_data['Latest']['data'])
                self.show_data('Max')

	    if 'Cal Data' in self.raw_data.keys():
		self.show_data('Cal Data')
		
        self.bg7.start()

    def save_cal_data(self, fname):
	fp = open(fname, 'wb')
	cPickle.dump(self.raw_data, fp)
	fp.close()
        self.settings.setValue('spectrum/file_dir', os.path.dirname(fname))

    def load_cal_data(self, fname):
	fp = open(fname, 'rb')
	cal_data = cPickle.load(fp)
	# Add some checks to make sure cal data is valid for our current setup
	self.raw_data['Cal Data'] = {}
	self.raw_data['Cal Data']['data'] = cal_data['Mean']['data'][:]
	fp.close()
	self.settings.setValue('spectrum/file_dir', os.path.dirname(fname))

    def axes_changed(self, plot):
        pass

    def show_data(self, label):
        data = self.raw_data[label]['data']
        xaxis = self.raw_data['Latest']['freqs']
        print 'xmin', np.min(xaxis), np.max(xaxis)
        
        self.dshape = data.shape[0]

        vals = np.log10(data.shape[0])
        if vals > 4:
            fact = 10**int(vals - 4)
            n = int(data.shape[0] / fact)
            print 'Factor', fact,'N', n

            s = data[0:n*fact].reshape(n, fact)
            data = np.mean(s, axis=1)

            s = xaxis[0:n*fact].reshape(n, fact)
            xaxis = np.mean(s, axis=1)
            
        print 'Min', np.min(data), 'Max', np.max(data), data.shape
        print 'dshape', self.dshape
        if label in self.item.keys():
            if self.do_log:
                self.item[label].set_data(xaxis, data)
            else:
                self.item[label].set_data(xaxis, np.log10(data))
        else:
            if self.do_log:
                self.item[label] = make.curve(xaxis, data, color=self.colours[len(self.item) % len(self.colours)], title=label)
            else:
                self.item[label] = make.curve(xaxis, data, color=self.colours[len(self.item) % len(self.colours)], title=label)
                
            self.curvewidget.plot.add_item(self.item[label])
            self.curvewidget.plot.set_antialiasing(True)
            if self.legend == None:
                self.legend = make.legend("TR")
                self.curvewidget.plot.add_item(self.legend)
            
        self.item[label].plot().replot()


    def rescan(self):
        print self.curvewidget.plot.get_axis_limits(BasePlot.X_BOTTOM)
        ax = self.curvewidget.plot.get_axis_limits(BasePlot.X_BOTTOM)
        un = self.curvewidget.plot.get_axis_unit(BasePlot.X_BOTTOM)
        if un == 'MHz':
            factor = 1e6
        elif un == 'GHz':
            factor = 1e9
        else:
            factor = 1.0
            
        self.reset_data()
        
        self.bg7.setParams(ax[0] * factor, (ax[1]-ax[0]) * factor)

        self.settings.setValue('spectrum/start_freq', ax[0] * factor)
        self.settings.setValue('spectrum/bandwidth', (ax[1] - ax[0]) * factor)
 
        #self.bg7.start()
        
    def do_max_hold(self):
        self.max_hold = not self.max_hold
        self.settings.setValue('gui/max_hold', self.max_hold)

    def do_log_lin(self, new_state):
        self.bg7.do_log(new_state)
	self.reset_data()
	
        #self.settings.setValue('gui/log_lin', new_state)
        
class MainWindow(QMainWindow):
    def __init__(self, reset=False, start_freq=None,
		 bandwidth=None, numpts=None, max_hold=None,
		 dev='/dev/ttyUSB0'):
        QMainWindow.__init__(self)
        self.settings = QSettings("Darkstar007", "networkanalyser")
        if reset:
            self.settings.clear()
            
	self.file_dir = self.settings.value('spectrum/file_dir', os.getenv('HOME'))
	print 'File dir', self.file_dir
	self.dev = dev
	
        self.setup(start_freq, bandwidth, numpts, max_hold)
        
    def setup(self, start_freq, bandwidth, numpts, max_hold):
        """Setup window parameters"""
        self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(APP_NAME + ' ' + VERS + ' Ruuning on ' + self.dev)
        dt = QDesktopWidget()
        print dt.numScreens(), dt.screenGeometry()
        sz = dt.screenGeometry()


        self.resize(QSize(sz.width()*9/10, sz.height()*9/10))
        
        # Welcome message in statusbar:
        status = self.statusBar()
        status.showMessage(_("Welcome to the NetworkAnalyser application!"), 5000)
        
        # File menu
        file_menu = self.menuBar().addMenu(_("File"))

        open_action = create_action(self, _("Save"),
                                    shortcut="Ctrl+S",
                                    icon=get_std_icon("DialogSaveButton"),
                                    tip=_("Save a Cal File"),
                                    triggered=self.saveFileDialog)

        load_action = create_action(self, _("Load"),
                                    shortcut="Ctrl+L",
                                    icon=get_std_icon("FileIcon"),
                                    tip=_("Load a cal File"),
                                    triggered=self.loadFileDialog)

        quit_action = create_action(self, _("Quit"),
                                    shortcut="Ctrl+Q",
                                    icon=get_std_icon("DialogCloseButton"),
                                    tip=_("Quit application"),
                                    triggered=self.close)
        add_actions(file_menu, (open_action, load_action, None, quit_action))
        
        # Help menu - prolly should just say "you're on your own..."!!
        help_menu = self.menuBar().addMenu("Help")
        about_action = create_action(self, _("About..."),
                                     icon=get_std_icon('MessageBoxInformation'),
                                     triggered=self.about)
        add_actions(help_menu, (about_action,))
        
        main_toolbar = self.addToolBar("Main")
        #add_actions(main_toolbar, (new_action, open_action, ))

        rescan_action = create_action(self, _("Rescan"),
                                      shortcut="Ctrl+R",
                                      icon=get_std_icon("BrowserReload"),
                                      tip=_("Rescan the current frequency selection"),
                                      checkable = False,
                                      triggered=self.do_scan)

        max_hold_action = create_action(self, _("Max Hold"),
                                        shortcut="Ctrl+M",
                                        icon=get_std_icon("ArrowUp"),
                                        tip=_("Display the maximum value encountered"),
                                        checkable = True,
                                        triggered=self.do_max_hold)

        log_lin_action = create_action(self, _("Log/Lin"),
				       shortcut="Ctrl+L",
				       icon=get_std_icon("ArrowRight"),
				       tip=_("Use linear power receive mode"),
				       checkable = True,
				       triggered=self.do_log_lin)

        if max_hold == None:
            max_hold = self.settings.value('gui/max_hold', False)
            print 'Got max_hold', max_hold
	    if type(max_hold) != bool:
		if max_hold in ['y', 'Y', 'T', 'True', 'true', '1']:
		    max_hold = True
		else:
		    max_hold = False
        max_hold_action.setChecked(max_hold)

        
        # Calibration action?
        add_actions(main_toolbar, (open_action, load_action, rescan_action,
				   max_hold_action, log_lin_action))
        
        # Set central widget:

        toolbar = self.addToolBar("Image")
        self.mainwidget = CentralWidget(self, self.settings, toolbar, start_freq, bandwidth, numpts, self.dev)
        self.setCentralWidget(self.mainwidget)
        
        if max_hold:
            self.do_max_hold()

    def do_scan(self):
        self.mainwidget.rescan()

    def do_max_hold(self):
        self.mainwidget.do_max_hold()
        
    def do_log_lin(self):
        self.mainwidget.do_log_lin()
        
    def saveFileDialog(self):
        print 'Save f dialog'
        fileName = QFileDialog.getSaveFileName(self, _("Save Cal Data"), self.file_dir)
        print fileName
        self.mainwidget.save_cal_data(fileName)
        
    def loadFileDialog(self):
        print 'load f dialog'
        fileName = QFileDialog.getOpenFileName(self, _("Open Cal Data"), self.file_dir)
        print fileName
        self.mainwidget.load_cal_data(fileName)
        
    def about(self):
        QMessageBox.about( self, _("About ")+APP_NAME,
              """<b>%s</b> v%s<p>%s Matt Nottingham
              <br>Copyright &copy; 2015 Matt Nottingham
              <p>Python %s, Qt %s, PyQt %s %s %s""" % \
              (APP_NAME, VERS, _("Developped by"), platform.python_version(),
               QT_VERSION_STR, PYQT_VERSION_STR, _("on"), platform.system()) )

import getopt

def usage():
    print 'netan.py [options]'
    print '-r/--reset                  Reset the defaults'
    print '-s/--start_freq <freq>      Set the start frequency'
    print '-b/--bandwidth <freq>       Set the bandwidth'
    print '-n/--numpts <number>        Set the number of points in the sweep'
    print '-m/--max_hold               Turn on max hold'
    print '-d/--device <device>        Use device <device>, default /dev/ttyUSB0'
    
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
    dev = '/dev/ttyUSB0'
    
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
	    dev = a[:]

    app = qapplication()
    window = MainWindow(reset=reset, start_freq=start_freq,
                        bandwidth=bandwidth, numpts=numpts,
                        max_hold = max_hold, dev = dev)
    window.show()
    app.exec_()


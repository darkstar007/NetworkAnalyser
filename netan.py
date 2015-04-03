#!/usr/bin/env python

#
# This code is licenced under the GPL version 2, a copy of which is attached
# in the files called 'LICENSE'
#
#
# Copyright Matt Nottingham, 2015
#
#

import os
import os.path as osp
from PyQt4 import QtGui
from PyQt4 import QtCore
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
                               SIGNAL)
from guiqwt.config import _
from guiqwt.plot import ImageWidget
from guiqwt.signals import SIG_LUT_CHANGED

from guiqwt.plot import ImageDialog
from guiqwt.builder import make
import numpy as np
import sys
import platform
from scipy.ndimage import gaussian_filter
import h5py
import serial
import struct
import datetime

APP_NAME = _("Network Analyser")
VERS = '0.0.1'

class BG7(QThread):
    def __init__(self, start_freq, bandwidth, num_samps, sport='/dev/ttyUSB0'):
        QThread.__init__(self)

        
        self.start_freq = start_freq
        self.num_samples = num_samps
        self.step_size = bandwidth / float(num_samps)
        
        if self.num_samples > 9999:
            raise ValueError('Too many samples requested')
        
        self.timer = QTimer()
        self.timer.setInterval(100)

        self.timeout_timer = QTimer()
        self.timeout_timer.setInterval(3000)

        self.data = bytes('')
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.check_serial)        
        self.connect(self.timeout_timer, QtCore.SIGNAL('timeout()'), self.timeout_serial)        
        self.fp = None
        self.restart = False
        self.do_debug = False
        
        self.sport = sport
        try:
            self.reconnect()
        except Exception, e:
            print e

        self.empty_buffer()

    def empty_buffer(self):
        while self.fp.inWaiting() > 0:
            self.fp.read(self.fp.inWaiting())
            time.sleep(0.25)
            
        print 'Finished empty_buffer'
                         
    def timeout_serial(self):
        print 'Timeout serial'
        self.timeout_timer.stop()
        self.reconnect()
        self.run()
        
    def setParams(self, start_freq, bw, num_samples=-1):
        self.tmp_start_freq = start_freq
        if num_samples < 0:
            self.tmp_num_samples = self.num_samples
        else:
            self.tmp_num_samples = num_samples
        
        self.tmp_step_size = bw / self.tmp_num_samples
        self.restart = True
        print 'Restart', self.tmp_start_freq, self.tmp_num_samples,self.tmp_step_size
        
    def reconnect(self):
        if self.fp != None:
            try:
                self.fp.close()
            except Exception, e:
                print e

        try:
            self.fp = serial.Serial(self.sport, 57600, timeout=4)
        except Exception, e:
            print e
            raise e

    def __del__(self):
        self.wait()
        
    def run(self):
        if self.fp != None:
            if self.restart:
                self.restart = False
                self.start_freq = self.tmp_start_freq
                self.num_samples = self.tmp_num_samples
        
                self.step_size = self.tmp_step_size
                
            print 'Sending command'
            self.fp.write('\x8f\x78'+format(int(self.start_freq/10.0), '09')+
                          format(int(self.step_size/10.0), '08')+
                          format(int(self.num_samples), '04'))
            self.start_time = datetime.datetime.now()
            self.data = bytes('')
            self.timer.start()
            self.timeout_timer.start()
            
    def check_serial(self):
        #print 'Check', self.fp.inWaiting(), self.restart
        if self.fp.inWaiting() > 0:
            self.data += self.fp.read(self.fp.inWaiting())
            #print 'Data', len(self.data), hex(ord(self.data[0])), hex(ord(self.data[1])), hex(ord(self.data[2])), hex(ord(self.data[3]))
            self.emit(QtCore.SIGNAL('measurement_progress(PyQt_PyObject)'),
                                    float(len(self.data) * 100.0) / float(4 * self.num_samples))
            self.timeout_timer.stop()

            if len(self.data) > 4 * self.num_samples:
                print 'Got too much data!'
                
            if len(self.data) == 4 * self.num_samples:
                diff = datetime.datetime.now() - self.start_time
                print 'Time taken', diff
                print 'Time per sample', diff.total_seconds() / self.num_samples
                if self.do_debug:
                    tmp = np.array(struct.unpack('<'+str(self.num_samples*4)+'B', self.data))
                    np.save('raw_dump', tmp)
                                   
                
                if not self.restart:
                    self.emit(QtCore.SIGNAL('measurement_complete(PyQt_PyObject)'),
                              (np.array(struct.unpack('<'+str(self.num_samples*2)+'H', self.data)[::2]),
                               self.start_freq, self.step_size, self.num_samples))
                else:
                    self.emit(QtCore.SIGNAL('measurement_complete(PyQt_PyObject)'),
                              (None, None, None, None))
                self.timer.stop()
            else:
                self.timeout_timer.start()

class CentralWidget(QSplitter):
    def __init__(self, parent, settings, toolbar, start_freq, bandwidth, numpts):
        QSplitter.__init__(self, parent)
        self.setContentsMargins(10, 10, 10, 10)
        self.setOrientation(Qt.Vertical)
        self.curvewidget = CurveWidget(self)
        self.item = {} 
        self.points = []
        self.max_hold = False
        self.do_log = True
        self.reset_data()
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
        self.connect(self.curvewidget.plot,
                     guiqwt.signals.SIG_PLOT_AXIS_CHANGED, self.axes_changed)

        if start_freq == None:
            start_freq = self.settings.value('spectrum/start_freq', 190e6).toFloat()[0]

        if bandwidth == None:
            bandwidth = self.settings.value('spectrum/bandwidth', 50e6).toFloat()[0]

        if numpts == None:
            numpts = self.settings.value('spectrum/num_samps', 6000).toInt()[0]
            
        print start_freq, bandwidth, numpts

        self.settings.setValue('spectrum/start_freq', start_freq)
        self.settings.setValue('spectrum/bandwidth', bandwidth)
        self.settings.setValue('spectrum/num_samps', numpts)

        
        self.bg7 = BG7(start_freq, bandwidth, numpts)
        self.connect(self.bg7, QtCore.SIGNAL('measurement_progress(PyQt_PyObject)'),
                     self.measurement_progress)
        self.connect(self.bg7, QtCore.SIGNAL('measurement_complete(PyQt_PyObject)'),
                     self.measurement_complete)
        self.bg7.start()

    def reset_data(self):
        self.count_data = 0
        self.raw_data = {}
        self.raw_data['latest'] = {}
        self.raw_data['max'] = {}
        self.raw_data['mean'] = {}
        self.raw_data['max']['data'] = None
        
    def measurement_progress(self, val):
        self.prog.setValue(int(val))
        
    def measurement_complete(self, cback_data):
        print 'cback'
        data, start_freq, step_size, num_samples = cback_data
        if data != None:
            self.raw_data['latest']['data'] = data[:]
            self.raw_data['latest']['freqs'] = (np.arange(num_samples) * step_size) + start_freq
            units = 'MHz'
            if self.raw_data['latest']['freqs'][num_samples/2] > 1e9:
                self.raw_data['latest']['freqs'] /= 1e9
                units = 'GHz'
            else:
                self.raw_data['latest']['freqs'] /= 1e6

            self.curvewidget.plot.set_axis_unit(BasePlot.X_BOTTOM, units)
                
            self.show_data('latest')

            if self.count_data == 0:
                self.raw_data['mean']['data'] = data[:] * 1.0
            else:
                self.raw_data['mean']['data'] = (((self.raw_data['mean']['data'] * self.count_data) + data[:]) /
                                                 (self.count_data + 1.0))
            self.count_data += 1

            self.show_data('mean')
        
            if self.max_hold:
                if self.raw_data['max']['data'] == None:
                    self.raw_data['max']['data'] = data[:]
                else:
                    self.raw_data['max']['data'][:] = np.maximum(self.raw_data['max']['data'], data)
                self.show_data('max')

        self.bg7.start()
        
    def axes_changed(self, plot):
        pass

    def show_data(self, label):
        data = self.raw_data[label]['data']
        xaxis = self.raw_data['latest']['freqs']
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
        
class MainWindow(QMainWindow):
    def __init__(self, reset=False, start_freq=None,
                        bandwidth=None, numpts=None, max_hold=None):
        QMainWindow.__init__(self)
        self.settings = QSettings("Darkstar007", "networkanalyser")
        if reset:
            self.settings.clear()
            
        self.setup(start_freq, bandwidth, numpts, max_hold)
        
    def setup(self, start_freq, bandwidth, numpts, max_hold):
        """Setup window parameters"""
        self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(APP_NAME)
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
                                    icon=get_std_icon("FileIcon"),
                                    tip=_("Save a File"),
                                    triggered=self.saveFileDialog)

        quit_action = create_action(self, _("Quit"),
                                    shortcut="Ctrl+Q",
                                    icon=get_std_icon("DialogCloseButton"),
                                    tip=_("Quit application"),
                                    triggered=self.close)
        add_actions(file_menu, (open_action, None, quit_action))
        
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

        if max_hold == None:
            max_hold = self.settings.value('gui/max_hold', False).toBool()
            print 'Got max_hold', max_hold
        max_hold_action.setChecked(max_hold)

        
        # Calibration action?
        add_actions(main_toolbar, (open_action, rescan_action, max_hold_action))
        
        # Set central widget:

        toolbar = self.addToolBar("Image")
        self.mainwidget = CentralWidget(self, self.settings, toolbar, start_freq, bandwidth, numpts)
        self.setCentralWidget(self.mainwidget)
        
        if max_hold:
            self.do_max_hold()


    def do_scan(self):
        self.mainwidget.rescan()

    def do_max_hold(self):
        self.mainwidget.do_max_hold()
        
    def saveFileDialog(self):
        print 'Save f dialog'
        fileName = QFileDialog.getOpenFileName(self, _("Open Image"), os.getenv('HOME'),
                                               _("Image Files (*.png *.jpg *.bmp)"))
        print fileName
        # Now do something!....
        
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
    
    return

if __name__ == '__main__':
    from guidata import qapplication
    try:
        optlist,args = getopt.getopt(sys.argv[1:], 'rs:b:n:m',
                                     ['reset', 'start_freq=', 'bandwidth=', 'numpts=',
                                      'max_hold'])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    reset = False
    start_freq = None
    bandwidth = None
    numpts = None
    max_hold = None
    
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
            
    app = qapplication()
    window = MainWindow(reset=reset, start_freq=start_freq,
                        bandwidth=bandwidth, numpts=numpts,
                        max_hold = max_hold)
    window.show()
    app.exec_()


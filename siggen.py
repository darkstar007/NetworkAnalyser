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
from guidata.qt.QtCore import QSize, QT_VERSION_STR, PYQT_VERSION_STR, Qt
                               
from guiqwt.config import _
from guiqwt.plot import ImageWidget

from guiqwt.plot import ImageDialog
from guiqwt.builder import make
import numpy as np
import sys
import platform

import serial
import struct
import datetime
import time

APP_NAME = _("Signal Generator")
VERS = '0.0.1'

class BG7(QThread):
    def __init__(self, freq, sport='/dev/ttyUSB0'):
        QThread.__init__(self)
        
        self.freq = freq

        self.timeout_timer = QTimer()
        self.timeout_timer.setInterval(3000)

        #self.connect(self.timeout_timer, QtCore.SIGNAL('timeout()'), self.timeout_serial)        
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
        pass
    
    def timeout_serial(self):
        print 'Timeout serial'
        self.timeout_timer.stop()
        self.reconnect()
        self.run()
        
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
                #self.freq = self.freq
                
            print 'Sending command', self.freq
            self.fp.write('\x8f' + 'f' + format(int(self.freq/10.0), '09'))
	    

        
class MainWindow(QMainWindow):
    def __init__(self, reset=False, start_freq=None,
                        bandwidth=None, numpts=None, max_hold=None):
        QMainWindow.__init__(self)
        self.settings = QSettings("Darkstar007", "signal_generator")
        if reset:
            self.settings.clear()
            
        self.setup(start_freq, bandwidth, numpts, max_hold)
        
    def setup(self, start_freq, bandwidth, numpts, max_hold):
        """Setup window parameters"""
        self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(APP_NAME)
        #dt = QDesktopWidget()
        #print dt.numScreens(), dt.screenGeometry()
        #sz = dt.screenGeometry()

        #self.resize(QSize(sz.width()*9/10, sz.height()*9/10))
        
        # Welcome message in statusbar:
        status = self.statusBar()
        status.showMessage(_("Welcome to the Signal Generator application!"), 5000)
        
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
        
        # Calibration action?
        add_actions(main_toolbar, (open_action, ))
        
        # Set central widget:

        toolbar = self.addToolBar("Image")

        self.setCentralWidget(self.mainwidget)
        
        if max_hold:
            self.do_max_hold()


    def about(self):
        QMessageBox.about( self, _("About ")+APP_NAME,
              """<b>%s</b> v%s<p>%s Matt Nottingham
              <br>Copyright &copy; 2015 Matt Nottingham
              <p>Python %s, Qt %s, PyQt %s %s %s""" % \
              (APP_NAME, VERS, _("Developped by"), platform.python_version(),
               QT_VERSION_STR, PYQT_VERSION_STR, _("on"), platform.system()) )

import getopt

def usage():
    print 'siggen.py [options]'
    print '-r/--reset                  Reset the defaults'
    print '-f/--freq <freq>            Set the frequency'
    
    return

if __name__ == '__main__':
    from guidata import qapplication
    try:
        optlist,args = getopt.getopt(sys.argv[1:], 'rf:',
                                     ['reset', 'freq='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    reset = False
    freq = 1.1e9

    
    for o,a in optlist:
        if o in ('-f', '--freq'):
            freq = float(a)
            
    #app = qapplication()
    #window = MainWindow(reset=reset, start_freq=start_freq,
    #                    bandwidth=bandwidth, numpts=numpts)
    #window.show()
    #app.exec_()
    d = BG7(freq)
    d.run()
    


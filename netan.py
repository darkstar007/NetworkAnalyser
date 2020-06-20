#!/usr/bin/env python3

#
# This code is licenced under the GPL version 2, a copy of which is attached
# in the files called 'LICENSE'
#
#
# Copyright Matt Nottingham, 2015, 2016, 2017
#
#

import os
import sys
import platform
import pickle

import struct
import datetime
import time
import getopt

import serial
import numpy as np

try:
    import PyQt5
    from PyQt5.QtWidgets import QSplitter, QApplication, QMainWindow, QDesktopWidget, QFileDialog, QStyle, QAction, QProgressBar
    from PyQt5.QtCore import QSettings, QSize, Qt, QLocale
    from PyQt5.QtGui import QGuiApplication
except ImportError:
    import PySide
    from PySide.QtCore import QSettings, QSize, Qt, QLocale
    from PySide.QtGui import QSplitter, QApplication, QMainWindow, QDesktopWidget, QFileDialog, QMessageBox

import pyqtgraph as pg

from BG7 import BG7

APP_NAME = "Network Analyser"
VERS = '0.4.0'

def get_std_icon(parent, name):
    return parent.style().standardIcon(getattr(QStyle, 'SP_' + name))

def create_action(parent, name,
                  shortcut=None,
                  icon=None,
                  tip=None,
                  triggered=None,
                  checkable=False):

    butt = None

    if icon is not None:
        butt = QAction(icon, name, parent)
    else:
        butt = QAction(name, parent)

    if shortcut is not None:
        butt.setShortcut(shortcut)

    if tip is not None:
        butt.setStatusTip(tip)

    if checkable:
        butt.setCheckable(True)

    if triggered is not None:
        butt.triggered.connect(triggered)

    return butt

def add_actions(parent, action_list):

    for a in action_list:
        if a is None:
            parent.addSeparator()
        else:
            parent.addAction(a)

class AnnotatedPoint():
    def __init__(self, x,y,param):
        pass
    
class MarkerAnnotatedPoint(AnnotatedPoint):
    def __init__(self, x = 0, y = 0, annotationparam=None, manager=None):
        AnnotatedPoint.__init__(self, x, y, annotationparam)
        self.manager = manager

        
    def get_infos(self):
        xt, yt = self.apply_transform_matrix(*self.shape.points[0])
        if self.manager != None:
            #info = self.manager.parent().getPointInfo(xt, yt)
            info_str = ''
            #for x in info.keys():
            #    info_str += x + ': ' + str(info[x]) + '<br>'
            
        else:
            info_str = 'Info:  N/A'
        if self.manager != None:
            xtxt = format(xt, '.3f') + self.manager.parent().curvewidget.plot.get_axis_unit(self.xAxis())
            ytxt = format(yt, '.3f') + self.manager.parent().curvewidget.plot.get_axis_unit(self.yAxis())
            lab = xtxt + ' ' + ytxt
        else:
            lab = 'No graph!'
        return  lab
    
class AnnotatedPointTool():
    def __init__(self):
        pass

class MarkerAnnotatedPointTool(AnnotatedPointTool):
    def create_shape(self):
        annotation = MarkerAnnotatedPoint(0, 0, manager=self.manager)
        self.set_shape_style(annotation)
        return annotation, 0, 0


class PlotWidget(QSplitter):
    def __init__(self, parent, settings, toolbar, start_freq, bandwidth, numpts, dev, lo, atten):
        QSplitter.__init__(self, parent)
        self.setContentsMargins(10, 10, 10, 10)
        self.setOrientation(Qt.Vertical)
        self.item = {}
        self.points = []
        self.max_hold = False
        self.do_log = True
        self.colours = ['b', 'r', 'c', 'y']
        self.legend = None
        self.settings = settings
        self.lo = lo
        self.atten = atten
        print('pw', self.atten)
        self.glw = pg.GraphicsLayoutWidget()
        self.curvewidget = self.glw.addPlot()
        self.curvewidget.showGrid(x=True, y=True, alpha=0.7)
        #self.curvewidget.add_toolbar(toolbar, "default")
        #self.curvewidget.register_all_image_tools()
        #self.curvewidget.add_tool(MarkerAnnotatedPointTool)

        #self.curvewidget.plot.set_axis_title(BasePlot.X_BOTTOM, 'Frequency')
        #self.curvewidget.plot.set_axis_title(BasePlot.Y_LEFT, 'Power')

        #self.curvewidget.plot.set_axis_unit(BasePlot.Y_LEFT, 'dBm')

        self.addWidget(self.glw)
        self.prog = QProgressBar()
        self.prog.setMaximumHeight(32)
        self.addWidget(self.prog)
        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 0)
        self.setStretchFactor(2, 1)
        self.setHandleWidth(10)
        self.setSizes([1, 5, 1])

        if start_freq is None:
            start_freq = float(self.settings.value('spectrum/start_freq', 190e6))

        if bandwidth is None:
            bandwidth = float(self.settings.value('spectrum/bandwidth', 50e6))

        if numpts is None:
            numpts = int(self.settings.value('spectrum/num_samps', 6000))

        print(start_freq, bandwidth, numpts, self.atten)

        default_cal_slope = 3.3 / (1024.0 * 16.44e-3)      # 16.44mV/dB, 3.3 V supply to ADC, 10 bit ADC
        default_cal_icept = -89.0                       # 0 ADC value = -89dBm

        self.cal_slope = self.settings.value('spectrum/cal_slope', default_cal_slope)
        self.cal_icept = self.settings.value('spectrum/cal_icept', default_cal_icept)
        
        self.settings.setValue('spectrum/start_freq', start_freq)
        self.settings.setValue('spectrum/bandwidth', bandwidth)
        self.settings.setValue('spectrum/num_samps', numpts)
        self.settings.setValue('spectrum/offset_freq', lo)

        #self.settings.setValue('spectrum/cal_slope', self.cal_slope)
        #self.settings.setValue('spectrum/cal_icept', self.cal_icept)
        print('Atten =', self.atten)
        
        self.bg7 = BG7(start_freq, bandwidth, numpts, self.atten, sport=dev)

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
        print('cback', start_freq, step_size)
        # data, start_freq, step_size, num_samples = cback_data
        if data is not None:
            if 'Cal Data' in list(self.raw_data.keys()):
                self.raw_data['Latest']['data'] = data[:] - self.raw_data['Cal Data']['data'] #+ self.atten
            else:
                self.raw_data['Latest']['data'] = data[:] #+ self.atten
            self.raw_data['Latest']['freqs'] = (np.arange(num_samples) * step_size) + start_freq + self.lo
            #self.raw_data['Latest']['freq_units'] = 'MHz'
            #if self.raw_data['Latest']['freqs'][int(num_samples/2)] > 1e9:
            #    self.raw_data['Latest']['freqs'] /= 1e9
            #    self.raw_data['Latest']['freq_units'] = 'GHz'
            #else:
            #    self.raw_data['Latest']['freqs'] /= 1e6
                
            #self.curvewidget.plot.set_axis_unit(BasePlot.X_BOTTOM,
            #                                    self.raw_data['Latest']['freq_units'])
            self.curvewidget.setLabel('bottom', text='Frequency', units='Hz') #self.raw_data['Latest']['freq_units'])
            self.show_data('Latest')

            if self.count_data == 0:
                self.raw_data['Mean']['data'] = self.raw_data['Latest']['data'] * 1.0
            else:
                if self.do_log:
                    self.raw_data['Mean']['data'] = 10.0 * np.log10((((10.0 ** (0.1 * self.raw_data['Mean']['data']) * self.count_data) +
                                                                      10.0 ** (0.1 * self.raw_data['Latest']['data'])) / (self.count_data + 1.0)))
                else:
                    self.raw_data['Mean']['data'] = (((self.raw_data['Mean']['data'] * self.count_data) +
                                                      self.raw_data['Latest']['data']) / (self.count_data + 1.0))
            self.count_data += 1

            self.show_data('Mean')

            if self.max_hold:
                if self.raw_data['Max']['data'] is None:
                    self.raw_data['Max']['data'] = self.raw_data['Latest']['data']
                else:
                    self.raw_data['Max']['data'][:] = np.maximum(self.raw_data['Max']['data'],
                                                                 self.raw_data['Latest']['data'])
                    self.show_data('Max')

            if 'Cal Data' in list(self.raw_data.keys()):
                self.show_data('Cal Data')

        self.bg7.start()

    def save_cal_data(self, fname):
        fp = open(fname, 'wb')
        pickle.dump(self.raw_data, fp)
        fp.close()
        self.settings.setValue('spectrum/file_dir', os.path.dirname(fname))

    def load_cal_data(self, fname):
        fp = open(fname, 'rb')
        cal_data = pickle.load(fp)
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
        print('xmin', np.min(xaxis), np.max(xaxis))

        self.dshape = data.shape[0]

        vals = np.log10(data.shape[0])
        if vals > 4:
            fact = 10**int(vals - 4)
            n = int(data.shape[0] / fact)
            print('Factor', fact,'N', n)

            s = data[0:n*fact].reshape(n, fact)
            data = np.mean(s, axis=1)

            s = xaxis[0:n*fact].reshape(n, fact)
            xaxis = np.mean(s, axis=1)

        print('Min', np.min(data), 'Max', np.max(data), data.shape)
        print('dshape', self.dshape)
        if label in list(self.item.keys()):
            if self.do_log:
                self.item[label].setData(xaxis, self.cal_slope * data + self.cal_icept)
            else:
                self.item[label].setData(xaxis, data)
        else:
            if self.do_log:
                self.item[label] = self.curvewidget.plot(xaxis, self.cal_slope * data + self.cal_icept,
                                                         color=self.colours[len(self.item) % len(self.colours)],
                                                         antialias=True, symbol='o', symbolSize=4,
                                                         symbolPen=self.colours[(len(self.item)) % len(self.colours)],
                                                         name=label, clickable=True)
            else:
                self.item[label] = self.curvewidget.plot(xaxis, data,
                                                         color=self.colours[len(self.item) % len(self.colours)],
                                                         antialias=True, symbol='o', symbolSize=4,
                                                         symbolPen=self.colours[(len(self.item)) % len(self.colours)],
                                                         name=label, clickable=True)
            #self.item[label].sigClicked.connect(self.plot_selected)

            #self.curvewidget.plot.add_item(self.item[label])
            #self.curvewidget.plot.set_antialiasing(True)
            #if self.legend is None:
            #    self.legend = make.legend("TR")
            #    self.curvewidget.plot.add_item(self.legend)

        #self.item[label].plot().replot()

    def rescan(self):
        print('Rescan', self.curvewidget.getAxis('bottom'))
        ax = self.curvewidget.getAxis('bottom')
        print(ax, ax.range, ax.labelUnits, ax.labelUnitPrefix)

        self.reset_data()

        self.bg7.setParams(ax.range[0], ax.range[1] - ax.range[0])

        self.settings.setValue('spectrum/start_freq', ax.range[0])
        self.settings.setValue('spectrum/bandwidth', (ax.range[1] - ax.range[0]))

        #self.bg7.start()

    def do_max_hold(self):
        self.max_hold = not self.max_hold
        self.settings.setValue('gui/max_hold', self.max_hold)

    def do_log_lin(self, new_state):
        if new_state:
            self.curvewidget.plot.set_axis_unit(BasePlot.Y_LEFT, 'dBm')
        else:
            self.curvewidget.plot.set_axis_unit(BasePlot.Y_LEFT, '?')

        self.bg7.do_log(new_state)
        self.reset_data()

        # self.settings.setValue('gui/log_lin', new_state)

    def do_new_plot(self):
        pass

class MainWindow(QMainWindow):
    def __init__(self, reset=False, start_freq=None,
                 bandwidth=None, numpts=None, max_hold=None, atten=0,
                 dev='/dev/ttyUSB0', offset=0.0):
        QMainWindow.__init__(self)
        self.settings = QSettings("Darkstar007", "networkanalyser")
        if reset:
            self.settings.clear()

        self.file_dir = self.settings.value('spectrum/file_dir', os.getenv('HOME'))
        print('File dir', self.file_dir)
        self.dev = dev
        self.lo = offset
        self.setup(start_freq, bandwidth, numpts, max_hold, atten)

    def setup(self, start_freq, bandwidth, numpts, max_hold, atten):
        """Setup window parameters"""
        #self.setWindowIcon(get_icon('python.png'))
        self.setWindowTitle(APP_NAME + ' ' + VERS + ' Running on ' + self.dev)

        # Work around Qt4/Qt5 moving classes around and their function
        try:
            screens = QGuiApplication.screens()
            print(len(screens), screens[0])
            sz = screens[0].availableGeometry()
        except NameError:
            dt = QDesktopWidget()
            print(dt.numScreens(), dt.screenGeometry())
            sz = dt.screenGeometry()

        self.resize(QSize(int(sz.width()*9/10), int(sz.height()*9/10)))

        # Welcome message in statusbar:
        status = self.statusBar()
        status.showMessage("Welcome to the NetworkAnalyser application!", 5000)

        # File menu
        file_menu = self.menuBar().addMenu("File")

        open_action = create_action(self, "Save",
                                    shortcut="Ctrl+S",
                                    icon=get_std_icon(self, "DialogSaveButton"),
                                    tip="Save a Cal File",
                                    triggered=self.saveFileDialog)

        load_action = create_action(self, "Load",
                                    shortcut="Ctrl+L",
                                    icon=get_std_icon(self, "FileIcon"),
                                    tip="Load a cal File",
                                    triggered=self.loadFileDialog)

        quit_action = create_action(self, "Quit",
                                    shortcut="Ctrl+Q",
                                    icon=get_std_icon(self, "DialogCloseButton"),
                                    tip="Quit application",
                                    triggered=self.close)
        add_actions(file_menu, (open_action, load_action, None, quit_action))

        # Help menu - prolly should just say "you're on your own..."!!
        help_menu = self.menuBar().addMenu("Help")
        about_action = create_action(self, "About...",
                                     icon=get_std_icon(self, 'MessageBoxInformation'),
                                     triggered=self.about)
        add_actions(help_menu, (about_action,))

        main_toolbar = self.addToolBar("Main")
        # add_actions(main_toolbar, (new_action, open_action, ))

        rescan_action = create_action(self, "Rescan",
                                      shortcut="Ctrl+R",
                                      icon=get_std_icon(self, "BrowserReload"),
                                      tip="Rescan the current frequency selection",
                                      checkable=False,
                                      triggered=self.do_scan)

        max_hold_action = create_action(self, "Max Hold",
                                        shortcut="Ctrl+M",
                                        icon=get_std_icon(self, "ArrowUp"),
                                        tip="Display the maximum value encountered",
                                        checkable=True,
                                        triggered=self.do_max_hold)

        log_lin_action = create_action(self, "Log/Lin",
                                       shortcut="Ctrl+L",
                                       icon=get_std_icon(self, "ArrowRight"),
                                       tip="Use linear power receive mode",
                                       checkable=True,
                                       triggered=self.do_log_lin)

        new_plot_action = create_action(self, "New Plot",
                                        shortcut="Ctrl+N",
                                        icon=get_std_icon(self, "ArrowLeft"),
                                        tip="Creates a new labeled plot",
                                        checkable=False,
                                        triggered=self.do_new_plot)
        
        if max_hold is None:
            max_hold = self.settings.value('gui/max_hold', False)
            print('Got max_hold', max_hold)
            if type(max_hold) != bool:
                if max_hold in ['y', 'Y', 'T', 'True', 'true', '1']:
                    max_hold = True
                else:
                    max_hold = False
        max_hold_action.setChecked(max_hold)

        # Calibration action?
        add_actions(main_toolbar, (open_action, load_action, rescan_action,
                                   max_hold_action, log_lin_action, new_plot_action))

        # Set central widget:

        toolbar = self.addToolBar("Image")
        self.mainwidget = PlotWidget(self, self.settings, toolbar, start_freq, bandwidth,
                                     numpts, self.dev, self.lo, atten)
        self.setCentralWidget(self.mainwidget)

        if max_hold:
            self.do_max_hold()

    def do_scan(self):
        self.mainwidget.rescan()

    def do_new_plot(self):
        self.mainwidget.do_new_plot()

    def do_max_hold(self):
        self.mainwidget.do_max_hold()

    def do_log_lin(self):
        self.mainwidget.do_log_lin()

    def saveFileDialog(self):
        print('Save f dialog')
        fileName = QFileDialog.getSaveFileName(self, "Save Cal Data", self.file_dir)
        print(fileName)
        self.mainwidget.save_cal_data(fileName)

    def loadFileDialog(self):
        print('load f dialog')
        fileName = QFileDialog.getOpenFileName(self, "Open Cal Data", self.file_dir)
        print(fileName)
        self.mainwidget.load_cal_data(fileName)

    def about(self):
        QMessageBox.about(self, _("About ")+APP_NAME,
                          """<b>%s</b> v%s<p>%s Matt Nottingham
                          <br>Copyright &copy; 2015-2017 Matt Nottingham
                          <p>Python %s, Qt %s, PyQt %s %s %s""" %
                          (APP_NAME, VERS, _("Developped by"), platform.python_version(),
                           QT_VERSION_STR, PYQT_VERSION_STR, _("on"), platform.system()) )


def usage():
    print('netan.py [options]')
    print('-r/--reset                  Reset the defaults')
    print('-s/--start_freq <freq>      Set the start frequency (mut excl to centre_freq option)')
    print('-c/--centre_freq <freq>     Set the centre frequency (mut excl to start_freq option)')
    print('-b/--bandwidth <freq>       Set the bandwidth')
    print('-n/--numpts <number>        Set the number of points in the sweep')
    print('-m/--max_hold               Turn on max hold')
    print('-d/--device <device>        Use device <device>, default /dev/ttyUSB0')
    print('-o/--offset <freq>          When displaying graph add on this (LO) freq offset')
    print('-a/--atten <value>          Set the attenuator value to this')
    return


if __name__ == '__main__':
    from guidata import qapplication
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'rs:b:n:md:c:o:a:',
                                      ['reset', 'start_freq=', 'bandwidth=', 'numpts=',
                                       'max_hold', 'device=', 'centre_freq=', 'offset=',
                                       'atten='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    reset = False
    start_freq = None
    bandwidth = None
    numpts = None
    max_hold = None
    centre_freq = None
    atten = 0
    dev = '/dev/ttyUSB0'
    offset = 0.0
    
    for o, a in optlist:
        if o in ('-r', '--reset'):
            reset = True
        elif o in ('-s', '--start_freq'):
            start_freq = float(a)
        elif o in ('-c', '--centre_freq'):
            centre_freq = float(a)
        elif o in ('-b', '--bandwidth'):
            bandwidth = float(a)
        elif o in ('-n', '--numpts'):
            numpts = int(a)
        elif o in ('-m', '--max_hold'):
            max_hold = True
        elif o in ('-d', '--device'):
            dev = a[:]
        elif o in ('-o', '--offset'):
            offset = float(a)
        elif o in ('-a', '--atten'):
            atten = int(a)

    print('atten top level', atten)
    if centre_freq is not None and start_freq is not None:
        print('Only one of start_freq or centre_freq can be set')
        raise ValueError('Invalid option set')

    if centre_freq is not None:
        if bandwidth is None:
            raise ValueError('Need to set a bandwidth if setting the centre freq')            
        else:
            start_freq = centre_freq - bandwidth / 2.0
    app = qapplication()
    window = MainWindow(reset=reset, start_freq=start_freq,
                        bandwidth=bandwidth, numpts=numpts,
                        max_hold=max_hold, dev=dev, atten=atten,
                        offset=offset)
    window.show()
    app.exec_()



#
# This code is licenced under the GPL version 2, a copy of which is attached
# in the files called 'LICENSE'
#
#
# Copyright Matt Nottingham, 2015, 2016
#
#

#from guidata.qt.QtCore import QSettings, QThread, QTimer, QObject
#from guidata.qt.QtCore import (QSize, QT_VERSION_STR, PYQT_VERSION_STR, Qt,
#                               Signal, pyqtSignal)

try:
    import PyQt5
    from PyQt5.QtWidgets import QSplitter, QApplication, QMainWindow, QDesktopWidget, QFileDialog, QStyle, QAction, QProgressBar
    from PyQt5.QtCore import QSettings, QSize, Qt, QLocale,QThread,pyqtSignal
    from PyQt5.QtGui import QGuiApplication
except ImportError:
    import PySide
    from PySide.QtCore import QSettings, QSize, Qt, QLocale
    from PySide.QtGui import QSplitter, QApplication, QMainWindow, QDesktopWidget, QFileDialog, QMessageBox

import time
import datetime
import serial
import struct
import numpy as np

class BG7(QThread):
    measurement_progress = pyqtSignal(float)
    measurement_complete = pyqtSignal(object, object, object, object)

    def __init__(self, start_freq, bandwidth, num_samps, atten=0, sport='/dev/ttyUSB0'):
        QThread.__init__(self)

        self.vers = -1
        self.start_freq = start_freq
        self.atten = atten
        print('Freq', start_freq)
        self.num_samples = num_samps
        self.step_size = bandwidth / float(num_samps)
        self.log = None
        self.log_mode = True
        self.do_log(self.log_mode)   # Set the data to be collected in log mode by default

        if self.num_samples > 9999:
            raise ValueError('Too many samples requested')
        
        #self.timer = QTimer()
        #self.timer.setInterval(300)

        #self.timeout_timer = QTimer()
        #self.timeout_timer.setInterval(5000)

        self.data = bytes('', encoding='utf8')

        #self.timer.timeout.connect(self.check_serial)
        #self.timeout_timer.timeout.connect(self.timeout_serial)

        self.fp = None
        self.restart = False
        self.do_debug = False

        self.sport = sport

        self.next_atten = None
        self.next_start_freq = None
        self.next_num_samples = None
        self.next_step_size = None

        try:
            self.reconnect()
        except Exception as e:
            print(e)

        self.empty_buffer()

        self.get_version()
        self.get_status()

    def atten_test(self):
        for x in range(255):
            print( 'Doing', x)
            self.fp.write(('\x8f' + 'r' + format(x, '02x')).encode())
            self.get_status()
            
    def do_log(self, state):
        if state:
            self.log = 'x'
            self.log_mode = True
        else:
            self.log = 'w'
            self.lof_mode = False
	    
    def empty_buffer(self):
        time.sleep(3.0)
        print('BG7: EmptyBuffer: in waiting', self.fp.inWaiting())
        while self.fp.inWaiting() > 0:
            pants = self.fp.read(self.fp.inWaiting())
            time.sleep(1.5)
            print('BG7: trying to empty buff', self.fp.inWaiting())
        print('BG7: Finished empty_buffer')
                         
    def timeout_serial(self):
        print('BG7: Timeout serial')
        self.timeout_timer.stop()
        self.reconnect()
        self.run()
        
    def setParams(self, start_freq, bw, atten=None, num_samples=-1):
        self.next_start_freq = start_freq
        if num_samples < 0:
            self.next_num_samples = self.num_samples
        else:
            self.next_num_samples = num_samples
        
        self.next_step_size = bw / self.next_num_samples

        if atten is not None:
            self.next_atten = atten
        else:
            self.next_atten = self.atten
            
        self.restart = True
        print('BG7: Restart', self.next_start_freq, self.next_num_samples,self.next_step_size, self.next_atten)
        
    def reconnect(self):
        if self.fp != None:
            try:
                self.fp.close()
            except Exception as e:
                print(e)

        try:
            self.fp = serial.Serial(self.sport, 57600, timeout=4)
        except Exception as e:
            print(e)
            raise e

    def __del__(self):
        self.wait()

    def get_status(self):
        self.fp.write(('\x8f' + 's').encode())
        while self.fp.inWaiting() < 4:
            time.sleep(0.1)
        data = self.fp.read(self.fp.inWaiting())
        if len(data) != 4:
            print('Got', len(data), 'bytes back from status command!')
        if len(data) >= 4:
            print(data[0], data[1], data[2], data[3])
            print('   version', data[0])
            print('   anten', data[1])
            print('   other', struct.unpack('<1H', data[2:])[0])

    def get_version(self):
        self.fp.write(('\x8f' + 'v').encode())
        while self.fp.inWaiting() < 1:
            time.sleep(0.1)
        self.vers = self.fp.read(self.fp.inWaiting())
        print('Got', len(self.vers), 'bytes back from version command')
        if len(self.vers) == 1:
            print('Firmware version', ord(self.vers))
        else:
            print('Got wrong length of data returned for get_version')

    def run(self):
        #freq = 1.23e9
        #print('Sending CW command', freq)
        #self.fp.write('\x8f' + 'f' + format(int(freq/10.0), '09'))
        if self.restart:
            self.restart = False
            self.start_freq = self.next_start_freq
            self.num_samples = self.next_num_samples

            self.step_size = self.next_step_size
            self.atten = self.next_atten

        if self.atten != 0:
            print('BG7: Sending command', '\x8f' + 'r' + format(int(self.atten), '02x'))
            self.fp.write(('\x8f' + 'r' + format(int(self.atten), '02x')).encode())

        print('BG7: Sending command', '\x8f' + self.log + format(int(self.start_freq/10.0), '09')+ format(int(self.step_size/10.0), '08')+ format(int(self.num_samples), '04'))
        self.fp.write(('\x8f' + self.log + format(int(self.start_freq/10.0), '09')+
                      format(int(self.step_size/10.0), '08')+
                       format(int(self.num_samples), '04')).encode())
        self.start_time = datetime.datetime.now()
        self.data = bytes('', encoding='utf8' )
        time.sleep(1)
        while self.fp.inWaiting() > 0:
            self.data += self.fp.read(self.fp.inWaiting())
            print('  so far got', len(self.data))
            self.measurement_progress.emit(
                float(len(self.data) * 100.0) / float(4 * self.num_samples))
            time.sleep(1)

        if len(self.data) == 4 * self.num_samples:
            diff = datetime.datetime.now() - self.start_time
            print('BG7: Time taken', diff)
            print('BG7: Time per sample', diff.total_seconds() / self.num_samples)
            if self.do_debug:
                tmp = np.array(struct.unpack('<'+str(self.num_samples*4)+'B', self.data))
                np.save('raw_dump', tmp)                                   

            if not self.restart:
                self.measurement_complete.emit(
                    np.array(struct.unpack('<'+str(self.num_samples*2)+'H', self.data)[::2]),
                    self.start_freq, self.step_size, self.num_samples)
            else:
                self.measurement_complete.emit(None, None, None, None)
        else:
            self.measurement_complete.emit(None, None, None, None)
	    

    def run_old(self):
        if self.fp != None:
            if self.restart:
                self.restart = False
                self.start_freq = self.next_start_freq
                self.num_samples = self.next_num_samples
        
                self.step_size = self.next_step_size
                self.atten = self.next_atten
                
            print('BG7: Sending command', '\x8f' + self.log + format(int(self.start_freq/10.0), '09')+ format(int(self.step_size/10.0), '08')+ format(int(self.num_samples), '04'))
            self.fp.write(('\x8f' + self.log + format(int(self.start_freq/10.0), '09')+
                           format(int(self.step_size/10.0), '08')+
                           format(int(self.num_samples), '04')).encode())
            self.start_time = datetime.datetime.now()
            self.data = bytes('', encoding='utf8')
            self.timer.start()
            self.timeout_timer.start()
            print('BG7: started timers & sent commands', self.timer.isActive(), self.timeout_timer.isActive())
	    
    def check_serial(self):
        print('Check', self.fp.inWaiting(), len(self.data), self.restart, self.timer.isActive(), self.timeout_timer.isActive())
        if self.fp.inWaiting() > 0:
            self.data += self.fp.read(self.fp.inWaiting())
            #print('Data', len(self.data), hex(ord(self.data[0])), hex(ord(self.data[1])), hex(ord(self.data[2])), hex(ord(self.data[3])))
            self.measurement_progress.emit(
		float(len(self.data) * 100.0) / float(4 * self.num_samples))
            self.timeout_timer.stop()

            if len(self.data) > 4 * self.num_samples:
                print('BG7: Got too much data!', len(self.data))
                self.timer.stop()
                self.timeout_timer.stop()
                self.empty_buffer()
                self.run()
                
            if len(self.data) == 4 * self.num_samples:
                diff = datetime.datetime.now() - self.start_time
                print('BG7: Time taken', diff)
                print('BG7: Time per sample', diff.total_seconds() / self.num_samples)
                if self.do_debug:
                    tmp = np.array(struct.unpack('<'+str(self.num_samples*4)+'B', self.data))
                    np.save('raw_dump', tmp)                                   
                
                if not self.restart:
                    self.measurement_complete.emit(
			np.array(struct.unpack('<'+str(self.num_samples*2)+'H', self.data)[::2]),
			self.start_freq, self.step_size, self.num_samples)
                else:
                    self.measurement_complete.emit(None, None, None, None)
		    
                self.timer.stop()
            else:
                self.timeout_timer.start()

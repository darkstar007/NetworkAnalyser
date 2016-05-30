

#
# This code is licenced under the GPL version 2, a copy of which is attached
# in the files called 'LICENSE'
#
#
# Copyright Matt Nottingham, 2015, 2016
#
#

from guidata.qt.QtCore import QSettings, QThread, QTimer, QObject
from guidata.qt.QtCore import (QSize, QT_VERSION_STR, PYQT_VERSION_STR, Qt,
                               Signal, pyqtSignal)
import time
import datetime
import serial
import struct
import numpy as np

class BG7(QThread):
    measurement_progress = pyqtSignal(float)
    measurement_complete = pyqtSignal(object, object, object, object)

    def __init__(self, start_freq, bandwidth, num_samps, sport='/dev/ttyUSB0'):
        QThread.__init__(self)

	
        self.start_freq = start_freq

	print 'Freq', start_freq
        self.num_samples = num_samps
        self.step_size = bandwidth / float(num_samps)
        self.log = None
        self.log_mode = True
	self.do_log(self.log_mode)   # Set the data to be collected in log mode by default
	
        if self.num_samples > 9999:
            raise ValueError('Too many samples requested')
        
        self.timer = QTimer()
        self.timer.setInterval(300)

        self.timeout_timer = QTimer()
        self.timeout_timer.setInterval(5000)

        self.data = bytes('')

	self.timer.timeout.connect(self.check_serial)
	self.timeout_timer.timeout.connect(self.timeout_serial)

        self.fp = None
        self.restart = False
        self.do_debug = False
        
        self.sport = sport
        try:
            self.reconnect()
        except Exception, e:
            print e
	    
        self.empty_buffer()

    def do_log(self, state):
	if state:
	    self.log = 'x'
	    self.log_mode = True
	else:
	    self.log = 'w'
	    self.lof_mode = False
	    
    def empty_buffer(self):
	time.sleep(3.0)
        print 'BG7: EmptyBuffer: in waiting', self.fp.inWaiting()
        while self.fp.inWaiting() > 0:
            pants = self.fp.read(self.fp.inWaiting())
            time.sleep(1.5)
            print 'BG7: trying to empty buff', self.fp.inWaiting()
        print 'BG7: Finished empty_buffer'
                         
    def timeout_serial(self):
        print 'BG7: Timeout serial'
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
        print 'BG7: Restart', self.tmp_start_freq, self.tmp_num_samples,self.tmp_step_size
        
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
                
            print 'BG7: Sending command', '\x8f' + self.log + format(int(self.start_freq/10.0), '09')+ format(int(self.step_size/10.0), '08')+ format(int(self.num_samples), '04')
            self.fp.write('\x8f' + self.log + format(int(self.start_freq/10.0), '09')+
                          format(int(self.step_size/10.0), '08')+
                          format(int(self.num_samples), '04'))
            self.start_time = datetime.datetime.now()
            self.data = bytes('')
            self.timer.start()
            self.timeout_timer.start()
            print 'BG7: started timers & sent commands', self.timer.isActive(), self.timeout_timer.isActive()
	    
    def check_serial(self):
        print 'Check', self.fp.inWaiting(), len(self.data), self.restart, self.timer.isActive(), self.timeout_timer.isActive()
        if self.fp.inWaiting() > 0:
            self.data += self.fp.read(self.fp.inWaiting())
            #print 'Data', len(self.data), hex(ord(self.data[0])), hex(ord(self.data[1])), hex(ord(self.data[2])), hex(ord(self.data[3]))
            self.measurement_progress.emit(
		float(len(self.data) * 100.0) / float(4 * self.num_samples))
            self.timeout_timer.stop()

            if len(self.data) > 4 * self.num_samples:
                print 'BG7: Got too much data!', len(self.data)
                self.timer.stop()
                self.timeout_timer.stop()
                self.empty_buffer()
                self.run()
                
            if len(self.data) == 4 * self.num_samples:
                diff = datetime.datetime.now() - self.start_time
                print 'BG7: Time taken', diff
                print 'BG7: Time per sample', diff.total_seconds() / self.num_samples
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

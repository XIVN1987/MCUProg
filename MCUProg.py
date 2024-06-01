#! python3
import os
import sys
import collections
import configparser

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QFileDialog

import jlink
import xlink
import device


os.environ['PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libusb-1.0.24/MinGW64/dll') + os.pathsep + os.environ['PATH']


zero_if = lambda i: 0 if i == -1 else i


'''
from MCUProg_UI import Ui_MCUProg
class MCUProg(QWidget, Ui_MCUProg):
    def __init__(self, parent=None):
        super(MCUProg, self).__init__(parent)
        
        self.setupUi(self)
'''
class MCUProg(QWidget):
    def __init__(self, parent=None):
        super(MCUProg, self).__init__(parent)
        
        uic.loadUi('MCUProg.ui', self)

        self.prgInfo.setVisible(False)

        self.initSetting()

        self.tmrDAP = QtCore.QTimer()
        self.tmrDAP.setInterval(1000)
        self.tmrDAP.timeout.connect(self.on_tmrDAP_timeout)
        self.tmrDAP.start()

    def initSetting(self):
        if not os.path.exists('setting.ini'):
            open('setting.ini', 'w', encoding='utf-8')
        
        self.conf = configparser.ConfigParser()
        self.conf.read('setting.ini', encoding='utf-8')
        
        if not self.conf.has_section('globals'):
            self.conf.add_section('globals')
            self.conf.set('globals', 'mcu',  'NUM480')
            self.conf.set('globals', 'addr', '0 K')
            self.conf.set('globals', 'size', '16 K')
            self.conf.set('globals', 'link', '')
            self.conf.set('globals', 'dllpath', '')
            self.conf.set('globals', 'hexpath', '[]')

        self.cmbMCU.addItems(device.Devices.keys())
        self.cmbMCU.setCurrentIndex(zero_if(self.cmbMCU.findText(self.conf.get('globals', 'mcu'))))

        self.cmbAddr.setCurrentIndex(zero_if(self.cmbAddr.findText(self.conf.get('globals', 'addr'))))
        self.cmbSize.setCurrentIndex(zero_if(self.cmbSize.findText(self.conf.get('globals', 'size'))))
        
        self.cmbDLL.addItem(self.conf.get('globals', 'dllpath'))
        self.on_tmrDAP_timeout()    # add DAPLink

        self.cmbDLL.setCurrentIndex(zero_if(self.cmbDLL.findText(self.conf.get('globals', 'link'))))

        self.cmbHEX.addItems(eval(self.conf.get('globals', 'hexpath')))
    
    def on_tmrDAP_timeout(self):
        if not self.isEnabled():    # link working
            return

        try:
            from pyocd.probe import aggregator
            self.daplinks = aggregator.DebugProbeAggregator.get_all_connected_probes()
            if len(self.daplinks) != self.cmbDLL.count() - 1:
                for i in range(1, self.cmbDLL.count()):
                    self.cmbDLL.removeItem(i)
                for i, daplink in enumerate(self.daplinks):
                    self.cmbDLL.addItem(daplink.product_name)
        except Exception as e:
            pass

    def connect(self):
        try:
            if self.cmbDLL.currentIndex() == 0:
                self.xlk = xlink.XLink(jlink.JLink(self.cmbDLL.currentText(), device.Devices[self.cmbMCU.currentText()].CHIP_CORE))

            else:
                from pyocd.coresight import dap, ap, cortex_m
                daplink = self.daplinks[self.cmbDLL.currentIndex() - 1]
                daplink.open()

                _dp = dap.DebugPort(daplink, None)
                _dp.init()
                _dp.power_up_debug()

                _ap = ap.AHB_AP(_dp, 0)
                _ap.init()

                self.xlk = xlink.XLink(cortex_m.CortexM(None, _ap))

            self.dev = device.Devices[self.cmbMCU.currentText()](self.xlk)

        except Exception as e:
            QMessageBox.critical(self, '连接失败', str(e), QMessageBox.Yes)

            return False

        return True

    @pyqtSlot()
    def on_btnErase_clicked(self):
        if self.connect():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            self.threadErase = ThreadAsync(self.dev.sect_erase, self.addr, self.size)
            self.threadErase.taskFinished.connect(self.on_btnErase_finished)
            self.threadErase.start()
        
    def on_btnErase_finished(self):
        QMessageBox.information(self, '擦除完成', '        芯片擦除完成        ', QMessageBox.Yes)

        self.xlk.reset()
        self.xlk.close()

        self.setEnabled(True)
        self.prgInfo.setVisible(False)

    @pyqtSlot()
    def on_btnWrite_clicked(self):
        if self.connect():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            if self.cmbHEX.currentText().endswith('.hex'):
                data = parseHex(self.cmbHEX.currentText())
            else:
                data = open(self.cmbHEX.currentText(), 'rb').read()

            if len(data)%self.dev.PAGE_SIZE:
                data += b'\xFF' * (self.dev.PAGE_SIZE - len(data)%self.dev.PAGE_SIZE)
            
            self.threadWrite = ThreadAsync(self.dev.chip_write, self.addr, data)
            self.threadWrite.taskFinished.connect(self.on_btnWrite_finished)
            self.threadWrite.start()

    def on_btnWrite_finished(self):
        QMessageBox.information(self, '烧写完成', '        程序烧写完成        ', QMessageBox.Yes)

        self.xlk.reset()
        self.xlk.close()

        self.setEnabled(True)
        self.prgInfo.setVisible(False)

    @pyqtSlot()
    def on_btnRead_clicked(self):
        if self.connect():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            self.buff = []      # bytes 无法 extend，因此用 list

            self.threadRead = ThreadAsync(self.dev.chip_read, self.addr, self.size, self.buff)
            self.threadRead.taskFinished.connect(self.on_btnRead_finished)
            self.threadRead.start()

    def on_btnRead_finished(self):
        binpath, filter = QFileDialog.getSaveFileName(caption='将读取到的数据保存到文件', filter='程序文件 (*.bin)')
        if binpath:
            with open(binpath, 'wb') as f:
                f.write(bytes(self.buff))

        self.xlk.reset()
        self.xlk.close()

        self.setEnabled(True)
        self.prgInfo.setVisible(False)

    @property
    def addr(self):
        return int(self.cmbAddr.currentText().split()[0]) * 1024

    @property
    def size(self):
        return int(self.cmbSize.currentText().split()[0]) * 1024

    @pyqtSlot(int)
    def on_cmbMCU_currentIndexChanged(self, index):
        dev = device.Devices[self.cmbMCU.currentText()](None)

        addr = self.cmbAddr.currentText()

        self.cmbAddr.clear()
        for i in range(dev.CHIP_SIZE // dev.SECT_SIZE):
            if (dev.SECT_SIZE * i) % 1024 == 0:
                self.cmbAddr.addItem('%d K' %(dev.SECT_SIZE * i     // 1024))

        self.cmbAddr.setCurrentIndex(zero_if(self.cmbAddr.findText(addr)))

    @pyqtSlot(int)
    def on_cmbAddr_currentIndexChanged(self, index):
        if self.cmbAddr.currentText() == '': return

        dev = device.Devices[self.cmbMCU.currentText()](None)

        size = self.cmbSize.currentText()
        
        self.cmbSize.clear()
        for i in range((dev.CHIP_SIZE - self.addr) // dev.SECT_SIZE):
            if (dev.SECT_SIZE * (i+1)) % 1024 == 0:
                self.cmbSize.addItem('%d K' %(dev.SECT_SIZE * (i+1) // 1024))

        self.cmbSize.setCurrentIndex(zero_if(self.cmbSize.findText(size)))

    @pyqtSlot()
    def on_btnDLL_clicked(self):
        dllpath, filter = QFileDialog.getOpenFileName(caption='JLink_x64.dll 路径', filter='动态链接库 (*.dll)', directory=self.cmbDLL.itemText(0))
        if dllpath:
            self.cmbDLL.setItemText(0, dllpath)

    @pyqtSlot()
    def on_btnHEX_clicked(self):
        hexpath, filter = QFileDialog.getOpenFileName(caption='程序文件路径', filter='程序文件 (*.bin *.hex)', directory=self.cmbHEX.currentText())
        if hexpath:
            self.cmbHEX.insertItem(0, hexpath)
            self.cmbHEX.setCurrentIndex(0)
    
    def closeEvent(self, evt):
        self.conf.set('globals', 'mcu',  self.cmbMCU.currentText())
        self.conf.set('globals', 'addr', self.cmbAddr.currentText())
        self.conf.set('globals', 'size', self.cmbSize.currentText())
        self.conf.set('globals', 'link', self.cmbDLL.currentText())
        self.conf.set('globals', 'dllpath', self.cmbDLL.itemText(0))

        hexpath = [self.cmbHEX.currentText()] + [self.cmbHEX.itemText(i) for i in range(self.cmbHEX.count())]
        self.conf.set('globals', 'hexpath', repr(list(collections.OrderedDict.fromkeys(hexpath))))    # 保留顺序去重    

        self.conf.write(open('setting.ini', 'w', encoding='utf-8'))


class ThreadAsync(QThread):
    taskFinished = pyqtSignal()

    def __init__(self, func, *args):
        super(ThreadAsync, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.func(*self.args)
        self.taskFinished.emit()


def parseHex(file):
    ''' 解析 .hex 文件，提取出程序代码，没有值的地方填充0xFF '''
    data = ''
    currentAddr = 0
    extSegAddr  = 0     # 扩展段地址
    for line in open(file, 'rb').readlines():
        line = line.strip()
        if len(line) == 0: continue
        
        len_ = int(line[1:3],16)
        addr = int(line[3:7],16) + extSegAddr
        type = int(line[7:9],16)
        if type == 0x00:
            if currentAddr != addr:
                if currentAddr != 0:
                    data += '\xFF' * (addr - currentAddr)
                currentAddr = addr
            for i in range(len_):
                data += chr(int(line[9+2*i:11+2*i], 16))
            currentAddr += len_
        elif type == 0x02:
            extSegAddr = int(line[9:9+4], 16) * 16
        elif type == 0x04:
            extSegAddr = int(line[9:9+4], 16) * 65536
    
    return data.encode('latin')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mcu = MCUProg()
    mcu.show()
    app.exec()

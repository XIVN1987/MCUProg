#! python3
import os
import re
import sys
import collections
import configparser

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QFileDialog

import jlink
import xlink
import device
import device.chip


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

        self.table.setVisible(False)
        self.resize(self.width(), 160)
        self.table.horizontalHeader().setStretchLastSection(True)

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
        
        if not self.conf.has_section('link'):
            self.conf.add_section('link')
            self.conf.set('link', 'mode', 'ARM SWD')
            self.conf.set('link', 'speed', '4 MHz')
            self.conf.set('link', 'jlink', 'path/to/JLink_x64.dll')
            self.conf.set('link', 'select', '')

        self.cmbMode.setCurrentIndex(zero_if(self.cmbMode.findText(self.conf.get('link', 'mode'))))
        self.cmbSpeed.setCurrentIndex(zero_if(self.cmbSpeed.findText(self.conf.get('link', 'speed'))))

        self.cmbDLL.addItem(self.conf.get('link', 'jlink'), 'jlink')
        self.cmbDLL.addItem('OpenOCD', 'openocd')
        self.on_tmrDAP_timeout()    # add DAPLink

        self.cmbDLL.setCurrentIndex(zero_if(self.cmbDLL.findText(self.conf.get('link', 'select'))))

        if not self.conf.has_section('target'):
            self.conf.add_section('target')
            self.conf.set('target', 'mcu',  'NUM480')
            self.conf.set('target', 'addr', '0 K')
            self.conf.set('target', 'size', '16 K')
            self.conf.set('target', 'hexpath', '[]')
            self.conf.set('target', 'savpath', '')

        self.cmbMCU.addItems(self.parse_devices())
        self.cmbMCU.setCurrentIndex(zero_if(self.cmbMCU.findText(self.conf.get('target', 'mcu'))))

        self.cmbAddr.setCurrentIndex(zero_if(self.cmbAddr.findText(self.conf.get('target', 'addr'))))
        self.cmbSize.setCurrentIndex(zero_if(self.cmbSize.findText(self.conf.get('target', 'size'))))
        
        self.cmbHEX.addItems(eval(self.conf.get('target', 'hexpath')))

        self.savPath = self.conf.get('target', 'savpath')
    
    def parse_devices(self):
        cwd = os.getcwd()
        try:
            for line in open(os.path.join(cwd, 'devices.txt')):
                match = re.match(r'(\w+)\s+(.+)\n', line)
                if match:
                    name = match.group(1)
                    addr = 0x20000000
                    size = 0x1000
                    path = os.path.join(cwd, match.group(2).strip())
                    device.Devices[name] = (name, addr, size, path)

                match = re.match(r'(\w+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(.+)\n', line)
                if match:
                    name = match.group(1)
                    addr = int(match.group(2), 16)
                    size = int(match.group(3), 16)
                    path = os.path.join(cwd, match.group(4).strip())
                    device.Devices[name] = (name, addr, size, path)

        except Exception as e:
            print(e)

        return device.Devices.keys()

    def on_tmrDAP_timeout(self):
        if not self.isEnabled():    # link working
            return

        try:
            from pyocd.probe import aggregator
            self.daplinks = aggregator.DebugProbeAggregator.get_all_connected_probes()
        except Exception as e:
            self.daplinks = []

        if len(self.daplinks) != self.cmbDLL.count() - 2:
            for i in range(2, self.cmbDLL.count()):
                self.cmbDLL.removeItem(2)

            for i, daplink in enumerate(self.daplinks):
                self.cmbDLL.addItem(f'{daplink.product_name} ({daplink.unique_id})', i)

    def device(self, name, xlink):
        dev = device.Devices[name]

        if isinstance(dev, tuple):
            return device.chip.Chip(xlink, dev)

        else:
            return dev(xlink)

    def link_open(self):
        mode = self.cmbMode.currentText()
        mode = mode.replace('RISC-V', 'RV').replace(' SWD', '').replace(' cJTAG', '').replace(' JTAG', 'J').lower()
        core = self.device(self.cmbMCU.currentText(), None).CHIP_CORE
        speed= int(self.cmbSpeed.currentText().split()[0]) * 1000 # KHz
        try:
            item_data = self.cmbDLL.currentData()

            if item_data == 'jlink':
                self.xlk = xlink.XLink(jlink.JLink(self.cmbDLL.currentText(), mode, core, speed))

            elif item_data == 'openocd':
                import openocd
                self.xlk = xlink.XLink(openocd.OpenOCD(mode=mode, core=core, speed=speed))

            else:
                from pyocd.coresight import dap, ap, cortex_m
                daplink = self.daplinks[item_data]
                daplink.open()

                _dp = dap.DebugPort(daplink, None)
                _dp.init()
                _dp.power_up_debug()
                _dp.set_clock(speed * 1000)

                _ap = ap.AHB_AP(_dp, 0)
                _ap.init()

                self.xlk = xlink.XLink(cortex_m.CortexM(None, _ap))

            self.dev = self.device(self.cmbMCU.currentText(), self.xlk)

        except Exception as e:
            QMessageBox.critical(self, '连接失败', str(e), QMessageBox.Yes)

            return False

        return True

    def link_close(self):
        self.xlk.reset()

        self.xlk.close()

    @pyqtSlot()
    def on_btnChipErase_clicked(self):
        if self.link_open():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            self.threadErase = ThreadAsync(self.dev.chip_erase)
            self.threadErase.taskFinished.connect(self.on_btnErase_finished)
            self.threadErase.start()

    @pyqtSlot()
    def on_btnErase_clicked(self):
        if self.link_open():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            self.threadErase = ThreadAsync(self.dev.sect_erase, self.addr, self.size)
            self.threadErase.taskFinished.connect(self.on_btnErase_finished)
            self.threadErase.start()
        
    def on_btnErase_finished(self):
        QMessageBox.information(self, '擦除完成', '        芯片擦除完成        ', QMessageBox.Yes)

        self.link_close()

        self.setEnabled(True)
        self.prgInfo.setVisible(False)

    @pyqtSlot()
    def on_btnWrite_clicked(self):
        if self.link_open():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            fpath = self.cmbHEX.currentText()
            if not os.path.exists(fpath):
                QMessageBox.warning(self, '文件不存在', fpath, QMessageBox.Yes)
                return

            if fpath.endswith('.ini'):
                self.wrdata = []
                for i in range(self.table.rowCount()):
                    if self.table.item(i, 0).checkState():
                        fpath = self.table.item(i, 2).text()
                        if not os.path.exists(fpath):
                            QMessageBox.warning(self, '文件不存在', fpath, QMessageBox.Yes)
                            return

                        addr = int(self.table.item(i, 1).text(), 16) - self.dev.CHIP_BASE

                        if fpath.endswith('.hex'):
                            self.wrdata.append((addr, parseHex(fpath)))

                        else:
                            self.wrdata.append((addr, open(fpath, 'rb').read()))
            
            elif fpath.endswith('.hex'):
                self.wrdata = [(self.addr, parseHex(fpath))]

            else:
                self.wrdata = [(self.addr, open(fpath, 'rb').read())]
            
            self.threadWrite = ThreadAsync(self.dev.chip_write, *self.wrdata.pop())
            self.threadWrite.taskFinished.connect(self.on_btnWrite_finished)
            self.threadWrite.start()

    def on_btnWrite_finished(self):
        if len(self.wrdata):
            self.threadWrite.args = self.wrdata.pop()
            self.threadWrite.start()

            return

        QMessageBox.information(self, '烧写完成', '        程序烧写完成        ', QMessageBox.Yes)

        self.link_close()

        self.setEnabled(True)
        self.prgInfo.setVisible(False)

    @pyqtSlot()
    def on_btnRead_clicked(self):
        if self.link_open():
            self.setEnabled(False)
            self.prgInfo.setVisible(True)

            self.rdbuff = []    # bytes 无法 extend，因此用 list

            self.threadRead = ThreadAsync(self.dev.chip_read, self.addr, self.size, self.rdbuff)
            self.threadRead.taskFinished.connect(self.on_btnRead_finished)
            self.threadRead.start()

    def on_btnRead_finished(self):
        binpath, filter = QFileDialog.getSaveFileName(caption='将读取到的数据保存到文件', filter='程序文件 (*.bin)', directory=self.savPath)
        if binpath:
            self.savPath = binpath
            with open(binpath, 'wb') as f:
                f.write(bytes(self.rdbuff))

        self.link_close()

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
        dev = self.device(self.cmbMCU.currentText(), None)

        addr = self.cmbAddr.currentText()

        self.cmbAddr.clear()
        for i in range(dev.SECT_SKIP // dev.SECT_SIZE, dev.CHIP_SIZE // dev.SECT_SIZE):
            if (dev.SECT_SIZE * i) % 1024 == 0:
                self.cmbAddr.addItem('%d K' %(dev.SECT_SIZE * i     // 1024))

        self.cmbAddr.setCurrentIndex(zero_if(self.cmbAddr.findText(addr)))

        if dev.falgo['pc_EraseChip'] > 0xFFFFFFFF:
            self.btnChipErase.setEnabled(False)
        else:
            self.btnChipErase.setEnabled(True)

    @pyqtSlot(int)
    def on_cmbAddr_currentIndexChanged(self, index):
        if self.cmbAddr.currentText() == '': return

        dev = self.device(self.cmbMCU.currentText(), None)

        size = self.cmbSize.currentText()
        
        self.cmbSize.clear()
        for i in range((dev.CHIP_SIZE - self.addr) // dev.SECT_SIZE):
            if (dev.SECT_SIZE * (i+1)) % 1024 == 0:
                self.cmbSize.addItem('%d K' %(dev.SECT_SIZE * (i+1) // 1024))

        self.cmbSize.setCurrentIndex(zero_if(self.cmbSize.findText(size)))

    @pyqtSlot()
    def on_btnDLL_clicked(self):
        dllpath, filter = QFileDialog.getOpenFileName(caption='JLink_x64.dll 路径', filter='动态链接库 (*.dll *.so)', directory=self.cmbDLL.itemText(0))
        if dllpath:
            self.cmbDLL.setItemText(0, dllpath)

    @pyqtSlot()
    def on_btnHEX_clicked(self):
        hexpath, filter = QFileDialog.getOpenFileName(caption='程序文件路径', filter='程序文件 (*.bin *.hex *.ini);;任意文件 (*.*)', directory=self.cmbHEX.currentText())
        if hexpath:
            self.cmbHEX.insertItem(0, hexpath)
            self.cmbHEX.setCurrentIndex(0)

    @pyqtSlot(str)
    def on_cmbHEX_currentIndexChanged(self, text):
        if text.endswith('.ini'):
            self.table.setVisible(True)
            self.resize(self.width(), 270)

            conf = configparser.ConfigParser()
            conf.read(text, encoding='utf-8')
            self.table.setRowCount(len(conf.sections()))
            for i,section in enumerate(conf.sections()):
                checkbox = QtWidgets.QTableWidgetItem(section)
                checkbox.setCheckState(QtCore.Qt.Checked)
                self.table.setItem(i, 0, checkbox)
                self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(conf.get(section, 'addr')))
                self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(conf.get(section, 'path')))
        
        else:
            self.table.setVisible(False)
            self.resize(self.width(), 160)

    @pyqtSlot(int, int)
    def on_table_cellDoubleClicked(self, row, column):
        if column != 2: # 只能设置文件路径
            return

        hexpath, filter = QFileDialog.getOpenFileName(caption='程序文件路径', filter='程序文件 (*.bin *.hex);;任意文件 (*.*)', directory=self.table.item(row, column).text())
        if hexpath:
            self.table.setItem(row, column, QtWidgets.QTableWidgetItem(hexpath))

            conf = configparser.ConfigParser()
            conf.read(self.cmbHEX.currentText(), encoding='utf-8')
            conf.set(self.table.item(row, 0).text(), 'path', hexpath)
            conf.write(open(self.cmbHEX.currentText(), 'w', encoding='utf-8'))
    
    def closeEvent(self, evt):
        self.conf.set('link',  'mode', self.cmbMode.currentText())
        self.conf.set('link',  'speed', self.cmbSpeed.currentText())
        self.conf.set('link',  'jlink', self.cmbDLL.itemText(0))
        self.conf.set('link',  'select', self.cmbDLL.currentText())

        self.conf.set('target', 'mcu', self.cmbMCU.currentText())
        self.conf.set('target', 'addr', self.cmbAddr.currentText())
        self.conf.set('target', 'size', self.cmbSize.currentText())
        self.conf.set('target', 'savpath', self.savPath)

        hexpath = [self.cmbHEX.currentText()] + [self.cmbHEX.itemText(i) for i in range(self.cmbHEX.count())]
        self.conf.set('target', 'hexpath', repr(list(collections.OrderedDict.fromkeys(hexpath))))    # 保留顺序去重    

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

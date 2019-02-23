#coding: utf-8
"""
 mbed CMSIS-DAP debugger
 Copyright (c) 2006-2015 ARM Limited
"""
import os
import sys
import struct


# 用于计算扇区CRC的程序，可运行于Cortex-M处理器；此代码是可重定位的，只需要4字节便捷对齐
# 下面的可执行代码为200字节，执行还需要1024字节crc表，总共1224字节；内存中需要为crc运算总共保留0x600字节存储空间，每页需要4字节保存crc结果
analyzer = (
    0x2180468c, 0x2600b5f0, 0x4f2c2501, 0x447f4c2c, 0x1c2b0049, 0x425b4033, 0x40230872, 0x085a4053,
    0x425b402b, 0x40534023, 0x402b085a, 0x4023425b, 0x085a4053, 0x425b402b, 0x40534023, 0x402b085a,
    0x4023425b, 0x085a4053, 0x425b402b, 0x40534023, 0x402b085a, 0x4023425b, 0x085a4053, 0x425b402b,
    0x40534023, 0xc7083601, 0xd1d2428e, 0x2b004663, 0x4663d01f, 0x46b4009e, 0x24ff2701, 0x44844d11,
    0x1c3a447d, 0x88418803, 0x4351409a, 0xd0122a00, 0x22011856, 0x780b4252, 0x40533101, 0x009b4023,
    0x0a12595b, 0x42b1405a, 0x43d2d1f5, 0x4560c004, 0x2000d1e7, 0x2200bdf0, 0x46c0e7f8, 0x000000b6,
    0xedb88320, 0x00000044,
)


class Flash(object):
    def __init__(self, jlink, flash):
        self.jlink = jlink

        self.flash = flash
        
        # perform a reset and stop the core on the reset handler
        self.jlink.setTargetState("PROGRAM")

        self.jlink.write_reg('r9', self.flash['static_base'])
        self.jlink.write_reg('sp', self.flash['begin_stack'])

        # 将Flash算法下载到RAM
        self.jlink.write_mem_U32(self.flash['load_address'], self.flash['instructions'])
        if self.flash['analyzer_supported']: self.jlink.write_mem_U32(self.flash['analyzer_address'], analyzer)
    
    def Init(self, addr, clk, func):    # func: 1 - Erase, 2 - Program, 3 - Verify
        res = self.callFunctionAndWait(self.flash['pc_Init'], addr, clk, func)
        
        if res != 0: print 'Init() error: %i' %res

    def UnInit(self, func):
        res = self.callFunctionAndWait(self.flash['pc_UnInit'], func)
        
        if res != 0: print 'UnInit() error: %i' %res

    def EraseSector(self, addr):
        res = self.callFunctionAndWait(self.flash['pc_EraseSector'], addr)

        if res != 0: print 'EraseSector(0x%08X) error: %i' %(addr, res)

    def ProgramPage(self, addr, data):
        self.jlink.write_mem(self.flash['begin_data'], data) # 将要烧写的数据传入单片机RAM

        res = self.callFunctionAndWait(self.flash['pc_ProgramPage'], addr, len(data), self.flash['begin_data'])

        if res != 0: print 'ProgramPage(0x%08X) error: %i' %(addr, res)

    def Verify(self, addr, data):
        self.jlink.write_mem(self.flash['begin_data'], data) # 将要校验的数据传入单片机RAM

        res = self.callFunctionAndWait(self.flash['pc_Verify'], addr, len(data), self.flash['begin_data'])

        if res != addr+len(data): print 'Verify(0x%08X) error: %i' %(addr, res)

    def EraseChip(self):
        res = self.callFunctionAndWait(self.flash['pc_EraseChip'])

        if res != 0: print 'EraseChip() error: %i' %res

    def BlankCheck(self, addr, size, value):
        res = self.callFunctionAndWait(self.flash['pc_BlankCheck'], addr, size, value)

        if res != 0: print 'BlankCheck(0x%08X) error: %i' %(addr, res)

    def Read(self, addr, size):
        res = self.callFunctionAndWait(self.flash['pc_Read'], addr, size, self.flash['begin_data'])

        if res != addr+size: print 'Read(0x%08X) error: %i' %(addr, res)

    def callFunction(self, pc, r0=None, r1=None, r2=None, r3=None):
        print '%08X' %pc
        self.jlink.write_reg('pc', pc)
        if r0 is not None: self.jlink.write_reg('r0', r0)
        if r1 is not None: self.jlink.write_reg('r1', r1)
        if r2 is not None: self.jlink.write_reg('r2', r2)
        if r3 is not None: self.jlink.write_reg('r3', r3)
        self.jlink.write_reg('lr', self.flash['load_address'] + 1)
        
        self.jlink.go()        

    def callFunctionAndWait(self, pc, r0=None, r1=None, r2=None, r3=None):
        self.callFunction(pc, r0, r1, r2, r3)
        
        # Wait until the breakpoint is hit
        while(self.jlink.getState() == self.jlink.TARGET_RUNNING): pass

        return self.jlink.read_reg('r0')

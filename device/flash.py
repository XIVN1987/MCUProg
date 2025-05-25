"""
 mbed CMSIS-DAP debugger
 Copyright (c) 2006-2015 ARM Limited
"""
import os
import sys
import struct


class Flash(object):
    def __init__(self, xlink, falgo):
        self.xlink = xlink

        self.falgo = falgo
        
        if self.xlink.mode.startswith('arm'):
            # perform a reset and stop the core on the reset handler
            self.xlink.setTargetState("PROGRAM")

            self.xlink.write_reg('r9', self.falgo['static_base'])
            self.xlink.write_reg('sp', self.falgo['begin_stack'])

        elif self.xlink.mode.startswith('rv'):
            self.xlink.reset()

            self.xlink.write_reg('gp', self.falgo['static_base'])
            self.xlink.write_reg('sp', self.falgo['begin_stack'])

        # 将Flash算法下载到RAM
        self.xlink.write_mem_U32(self.falgo['load_address'], self.falgo['instructions'])

    def Init(self, addr, clk, func):    # func: 1 - Erase, 2 - Program, 3 - Verify
        print(f'Init {func}')
        
        res = self.callFunctionAndWait(self.falgo['pc_Init'], addr, clk, func)
        
        if res != 0: print(f'Init() error: {res}')

    def UnInit(self, func):
        print(f'UnInit {func}')

        res = self.callFunctionAndWait(self.falgo['pc_UnInit'], func)
        
        if res != 0: print(f'UnInit() error: {res}')

    def EraseSector(self, addr):
        print(f'Erase @ 0x{addr:08X}')

        res = self.callFunctionAndWait(self.falgo['pc_EraseSector'], addr)

        if res != 0: print(f'EraseSector({addr:08X}) error: {res}')

    def ProgramPage(self, addr, data):
        print(f'Write @ 0x{addr:08X}')

        self.xlink.write_mem(self.falgo['begin_data'], data) # 将要烧写的数据传入单片机RAM

        res = self.callFunctionAndWait(self.falgo['pc_ProgramPage'], addr, len(data), self.falgo['begin_data'])

        if res != 0: print(f'ProgramPage({addr:08X}) error: {res}')

    def Verify(self, addr, data):
        print(f'Verify @ 0x{addr:08X}')

        self.xlink.write_mem(self.falgo['begin_data'], data) # 将要校验的数据传入单片机RAM

        res = self.callFunctionAndWait(self.falgo['pc_Verify'], addr, len(data), self.falgo['begin_data'])

        if res != addr+len(data): print(f'Verify({addr:08X}) error: {res}')

    def EraseChip(self):
        res = self.callFunctionAndWait(self.falgo['pc_EraseChip'])

        if res != 0: print(f'EraseChip() error: {res}')

    def BlankCheck(self, addr, size, value):
        res = self.callFunctionAndWait(self.falgo['pc_BlankCheck'], addr, size, value)

        if res != 0: print(f'BlankCheck({addr:08X}) error: {res}')

    def Read(self, addr, size):
        print(f'Read @ 0x{addr:08X}')

        res = self.callFunctionAndWait(self.falgo['pc_Read'], addr, size, self.falgo['begin_data'])

        if res != addr+size: print(f'Read({addr:08X}) error: {res}')

    def callFunction(self, pc, r0=None, r1=None, r2=None, r3=None):
        self.xlink.write_reg('pc', pc)

        if self.xlink.mode.startswith('arm'):
            if r0 is not None: self.xlink.write_reg('r0', r0)
            if r1 is not None: self.xlink.write_reg('r1', r1)
            if r2 is not None: self.xlink.write_reg('r2', r2)
            if r3 is not None: self.xlink.write_reg('r3', r3)
            self.xlink.write_reg('lr', self.falgo['load_address'] + 1)

        elif self.xlink.mode.startswith('rv'):
            if r0 is not None: self.xlink.write_reg('a0', r0)
            if r1 is not None: self.xlink.write_reg('a1', r1)
            if r2 is not None: self.xlink.write_reg('a2', r2)
            if r3 is not None: self.xlink.write_reg('a3', r3)
            self.xlink.write_reg('ra', self.falgo['load_address'] + 1)
        
        self.xlink.go()

    def callFunctionAndWait(self, pc, r0=None, r1=None, r2=None, r3=None):
        self.callFunction(pc, r0, r1, r2, r3)
        
        # Wait until the breakpoint is hit
        while self.xlink.running(): pass

        if self.xlink.mode.startswith('arm'):
            return self.xlink.read_reg('r0')

        elif self.xlink.mode.startswith('rv'):
            return self.xlink.read_reg('a0')

import os
import time
import ctypes
import operator


import jlink
import openocd


class XLink(object):
    def __init__(self, xlk):
        self.xlk = xlk

    def open(self, mode, core, speed):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.open(mode, core, speed)
        else:
            self.xlk.ap.dp.link.open()

    @property
    def mode(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.mode
        else:
            return 'arm'
    
    def write_U8(self, addr, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_U8(addr, val)
        else:
            self.xlk.write8(addr, val)

    def write_U16(self, addr, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_U16(addr, val)
        else:
            self.xlk.write16(addr, val)

    def write_U32(self, addr, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_U32(addr, val)
        else:
            self.xlk.write32(addr, val)

    def write_mem_U8(self, addr, data):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_mem_U8(addr, data)
        else:
            self.xlk.write_memory_block8(addr, data)

    def write_mem_U32(self, addr, data):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_mem_U32(addr, data)
        else:
            self.xlk.write_memory_block32(addr, data)

    def read_mem_U8(self, addr, count):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_mem_U8(addr, count)
        else:
            return self.xlk.read_memory_block8(addr, count)

    def read_mem_U16(self, addr, count):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_mem_U16(addr, count)
        else:
            return [self.xlk.read16(addr+i*2) for i in range(count)]

    def read_mem_U32(self, addr, count):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_mem_U32(addr, count)
        else:
            return self.xlk.read_memory_block32(addr, count)

    def read_U32(self, addr):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_U32(addr)
        else:
            return self.xlk.read32(addr)

    def read_reg(self, reg):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_reg(reg)
        else:
            return self.xlk.read_core_register_raw(reg.upper())

    def read_regs(self, rlist):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_regs(rlist)
        else:
            return dict(zip(rlist, self.xlk.read_core_registers_raw(rlist)))

    def write_reg(self, reg, val):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.write_reg(reg, val)
        else:
            self.xlk.write_core_register_raw(reg, val)

    def reset(self):
        self.xlk.reset()

        if self.mode.startswith('rv'):
            self.xlk.write_reg('pc', 0)     # OpenOCD: resume from current code position.
            self.xlk.write_reg('dpc', 0)    # When resuming, PC is updated to value in dpc.
            self.go()
    
    def halt(self):
        self.xlk.halt()

    def step(self):
        self.xlk.step()

    def go(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.go()
        else:
            self.xlk.resume()

    def halted(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.halted()
        else:
            return self.xlk.is_halted()

    def close(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            self.xlk.close()
        else:
            self.xlk.ap.dp.link.close()

    def read_core_type(self):
        if isinstance(self.xlk, (jlink.JLink, openocd.OpenOCD)):
            return self.xlk.read_core_type()
        else:
            self.xlk._read_core_type()
            from pyocd.coresight import cortex_m
            return cortex_m.CORE_TYPE_NAME[self.xlk.core_type]

    def reset_and_halt(self):
        if isinstance(self.xlk, openocd.OpenOCD):
            self.xlk.reset(halt=True)

        elif isinstance(self.xlk, jlink.JLink):
            if self.mode.startswith('rv'):
                self.xlk.reset()

            else:   # arm
                self.resetStopOnReset()
                self.write_reg('xpsr', 0x1000000)   # set thumb bit in case the reset handler points to an ARM address

        else:       # daplink only support arm
            self.resetStopOnReset()
            self.write_reg('xpsr', 0x1000000)


    #####################################################################

    # Debug Halting Control and Status Register
    DHCSR = 0xE000EDF0
    C_DEBUGEN   = (1 <<  0)
    C_HALT      = (1 <<  1)
    C_STEP      = (1 <<  2)
    S_REGRDY    = (1 << 16)
    S_HALT      = (1 << 17)
    S_SLEEP     = (1 << 18)
    S_LOCKUP    = (1 << 19)
    S_RETIRE_ST = (1 << 24)     # 1: At least one instruction retired since last DHCSR read.
    S_RESET_ST  = (1 << 25)     # 1: At least one reset since last DHCSR read.

    # Debug Exception and Monitor Control Register
    DEMCR = 0xE000EDFC
    DEMCR_TRCENA       = (1 << 24)
    DEMCR_VC_HARDERR   = (1 << 10)  # Enable halting debug trap on a HardFault exception.
    DEMCR_VC_CORERESET = (1 <<  0)  # Enable Reset Vector Catch. This causes a Local reset to halt a running system.

    def resetStopOnReset(self):
        ''' perform a reset and stop the core on the reset handler '''
        self.halt()

        demcr = self.read_U32(self.DEMCR)

        self.write_U32(self.DEMCR, demcr | self.DEMCR_VC_CORERESET)

        self.reset()
        self.waitReset()
        while not self.halted():
            time.sleep(0.001)

        self.write_U32(self.DEMCR, demcr)

    def waitReset(self):
        ''' wait for the system to come out of reset '''
        startTime = time.time()
        while time.time() - startTime < 2.0:
            try:
                dhcsr = self.read_U32(self.DHCSR)
                if (dhcsr & self.S_RESET_ST) == 0: break
            except Exception as e:
                time.sleep(0.01)

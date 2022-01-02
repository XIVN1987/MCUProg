import os
import time
import ctypes
import operator


import jlink


class XLink(object):
    def __init__(self, xlk):
        self.xlk = xlk

    def open(self, mcucore):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.open(mcucore)
        else:
            self.xlk.ap.dp.link.open()

    def close(self, mcucore):
        if isinstance(self.xlk, jlink.JLink):
            pass
        else:
            self.xlk.ap.dp.link.close()

    def write_U8(self, addr, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_U8(addr, val)
        else:
            self.xlk.write8(addr, val)

    def write_U16(self, addr, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_U16(addr, val)
        else:
            self.xlk.write16(addr, val)

    def write_U32(self, addr, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_U32(addr, val)
        else:
            self.xlk.write32(addr, val)

    def write_mem(self, addr, data):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_mem(addr, data)
        else:
            self.xlk.write_memory_block8(addr, data)

    def write_mem_U32(self, addr, data):
        if isinstance(self.xlk, jlink.JLink):
            byte = []
            for x in data: byte.extend([x&0xFF, (x>>8)&0xFF, (x>>16)&0xFF, (x>>24)&0xFF])
            self.xlk.write_mem(addr, byte)
        else:
            self.xlk.write_memory_block32(addr, data)

    def read_mem(self, addr, count):
        return self.read_mem_U8(addr, count)

    def read_mem_U8(self, addr, count):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_mem_U8(addr, count)
        else:
            return self.xlk.read_memory_block8(addr, count)

    def read_mem_U16(self, addr, count):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_mem_U16(addr, count)
        else:
            return [self.xlk.read16(addr+i*2) for i in range(count)]

    def read_mem_U32(self, addr, count):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_mem_U32(addr, count)
        else:
            return [self.xlk.read32(addr+i*4) for i in range(count)]

    def read_U32(self, addr):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_U32(addr)
        else:
            return self.xlk.read32(addr)

    def read_reg(self, reg):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_reg(reg)
        else:
            return self.xlk.read_core_register_raw(reg.upper())

    def read_regs(self, rlist):
        rlist = [r.upper() for r in rlist]
        
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_regs(rlist)
        else:
            return dict(zip(rlist, self.xlk.read_core_registers_raw(rlist)))

    def write_reg(self, reg, val):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.write_reg(reg, val)
        else:
            self.xlk.write_core_register_raw(reg, val)

    def reset(self):
        NVIC_AIRCR = 0xE000ED0C
        NVIC_AIRCR_VECTKEY      = (0x5FA << 16)
        NVIC_AIRCR_VECTRESET    = (1 << 0)
        NVIC_AIRCR_SYSRESETREQ  = (1 << 2)

        try:
            self.write_U32(NVIC_AIRCR, NVIC_AIRCR_VECTKEY | NVIC_AIRCR_SYSRESETREQ)
        except Exception as e:
            print(e)
    
    def halt(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.halt()
        else:
            self.xlk.halt()

    def go(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.go()
        else:
            self.xlk.resume()

    def halted(self):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.halted()
        else:
            return self.xlk.is_halted()

    def close(self):
        if isinstance(self.xlk, jlink.JLink):
            self.xlk.close()
        else:
            self.xlk.ap.dp.link.close()

    def read_core_type(self):
        if isinstance(self.xlk, jlink.JLink):
            return self.xlk.read_core_type()
        else:
            self.xlk._read_core_type()
            from pyocd.coresight import cortex_m
            return cortex_m.CORE_TYPE_NAME[self.xlk.core_type]


    #####################################################################
    TARGET_RUNNING  = 1  # Core is executing code.
    TARGET_HALTED   = 2  # Core is halted in debug mode.
    TARGET_RESET    = 3  # Core is being held in reset.
    TARGET_SLEEPING = 4  # Core is sleeping due to a wfi or wfe instruction.
    TARGET_LOCKUP   = 5  # Core is locked up.

    # Debug Halting Control and Status Register
    DHCSR = 0xE000EDF0
    C_DEBUGEN   = (1 << 0)
    C_HALT      = (1 << 1)
    C_STEP      = (1 << 2)
    C_MASKINTS  = (1 << 3)
    C_SNAPSTALL = (1 << 5)
    S_REGRDY    = (1 << 16)
    S_HALT      = (1 << 17)
    S_SLEEP     = (1 << 18)
    S_LOCKUP    = (1 << 19)
    S_RETIRE_ST = (1 << 24)
    S_RESET_ST  = (1 << 25)

    # Debug Exception and Monitor Control Register
    DEMCR = 0xE000EDFC
    DEMCR_TRCENA       = (1 << 24)
    DEMCR_VC_HARDERR   = (1 << 10)
    DEMCR_VC_BUSERR    = (1 << 8)
    DEMCR_VC_CORERESET = (1 << 0)

    DBGKEY = (0xA05F << 16)

    def getState(self):
        dhcsr = self.read_U32(self.DHCSR)
        if dhcsr & self.S_RESET_ST:
            newDhcsr = self.read_U32(self.DHCSR)
            if (newDhcsr & self.S_RESET_ST) and not (newDhcsr & self.S_RETIRE_ST):
                return self.TARGET_RESET
        if dhcsr & self.S_LOCKUP:
            return self.TARGET_LOCKUP
        elif dhcsr & self.S_SLEEP:
            return self.TARGET_SLEEPING
        elif dhcsr & self.S_HALT:
            return self.TARGET_HALTED
        else:
            return self.TARGET_RUNNING

    def running(self):
        return self.getState() == self.TARGET_RUNNING

    def setTargetState(self, state):
        if state == 'PROGRAM':
            self.resetStopOnReset()
            # Write the thumb bit in case the reset handler points to an ARM address
            self.write_reg('xpsr', 0x1000000)

    def resetStopOnReset(self):
        ''' perform a reset and stop the core on the reset handler '''
        self.halt()

        demcr = self.read_U32(self.DEMCR)

        self.write_U32(self.DEMCR, demcr | self.DEMCR_VC_CORERESET) # enable the vector catch

        self.reset()
        self.waitReset()
        while self.running(): pass

        self.write_U32(self.DEMCR, demcr)

    def waitReset(self):
        ''' Now wait for the system to come out of reset '''
        startTime = time.time()
        while time.time() - startTime < 2.0:
            try:
                dhcsr = self.read_U32(self.DHCSR)
                if (dhcsr & self.S_RESET_ST) == 0: break
            except Exception as e:
                time.sleep(0.01)

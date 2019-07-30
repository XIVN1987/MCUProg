#coding: utf-8
import time
import ctypes


class JLink(object):
    def __init__(self, dllpath, coretype):
        self.jlk = ctypes.cdll.LoadLibrary(dllpath)

        err_buf = (ctypes.c_char * 64)()
        self.jlk.JLINKARM_ExecCommand('Device = %s' %coretype, err_buf, 64)

        self.jlk.JLINKARM_TIF_Select(1)
        self.jlk.JLINKARM_SetSpeed(4000)
        self.jlk.JLINKARM_Reset()

    def write_U32(self, addr, val):
        self.jlk.JLINKARM_WriteU32(addr, val)

    def write_U16(self, addr, val):
        self.jlk.JLINKARM_WriteU16(addr, val)

    def read_U32(self, addr):
        buf = (ctypes.c_uint32 * 1)()
        self.jlk.JLINKARM_ReadMemU32(addr, 1, buf, 0)

        return buf[0]

    def write_mem(self, addr, data):
        if type(data) == list: data = ''.join([chr(x) for x in data])
        buf = ctypes.create_string_buffer(data)
        self.jlk.JLINKARM_WriteMem(addr, len(data), buf)

    def read_mem(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        self.jlk.JLINKARM_ReadMem(addr, size, buf)

        return buf

    def write_mem_U32(self, addr, data):
        byte = []
        for x in data:
            byte.extend([x&0xFF, (x>>8)&0xFF, (x>>16)&0xFF, (x>>24)&0xFF])
        self.write_mem(addr, byte)

    NVIC_AIRCR = 0xE000ED0C
    NVIC_AIRCR_VECTKEY      = (0x5FA << 16)
    NVIC_AIRCR_VECTRESET    = (1 << 0)
    NVIC_AIRCR_SYSRESETREQ  = (1 << 2)

    def reset(self, hardware_reset=False):
        if hardware_reset:
            raise NotImplemented()
        else:
            try:
                self.write_U32(self.NVIC_AIRCR, self.NVIC_AIRCR_VECTKEY | self.NVIC_AIRCR_SYSRESETREQ)
            except Exception:
                pass

    def halt(self):
        self.jlk.JLINKARM_Halt()

    def go(self):
        self.jlk.JLINKARM_Go()

    CORE_REGISTER = {
        'r0'  : 0,
        'r1'  : 1,
        'r2'  : 2,
        'r3'  : 3,
        'r4'  : 4,
        'r5'  : 5,
        'r6'  : 6,
        'r7'  : 7,
        'r8'  : 8,
        'r9'  : 9,
        'r10' : 10,
        'r11' : 11,
        'r12' : 12,
        'sp'  : 13,
        'r13' : 13,
        'lr'  : 14,
        'r14' : 14,
        'pc'  : 15,
        'r15' : 15,
        'xpsr': 16,
    }

    def write_reg(self, reg, val):
        self.jlk.JLINKARM_WriteReg(self.CORE_REGISTER[reg], val)

    def read_reg(self, reg):
        return self.jlk.JLINKARM_ReadReg(self.CORE_REGISTER[reg])


    ###################################################
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

    def isRunning(self):
        return self.getState() == self.TARGET_RUNNING

    def isHalted(self):
        return self.getState() == self.TARGET_HALTED

    def setTargetState(self, state):
        if state == "PROGRAM":
            self.resetStopOnReset()
            # Write the thumb bit in case the reset handler points to an ARM address
            self.write_reg('xpsr', 0x1000000)

    def resetStopOnReset(self):
        """perform a reset and stop the core on the reset handler"""
        self.halt()

        demcr = self.read_U32(self.DEMCR)

        self.write_U32(self.DEMCR, demcr | self.DEMCR_VC_CORERESET) # enable the vector catch

        self.reset()
        self.waitReset()
        while self.isRunning(): pass

        self.write_U32(self.DEMCR, demcr)

    def waitReset(self):
        ''' Now wait for the system to come out of reset '''
        startTime = time.time()
        while time.time() - startTime < 2.0:
            try:
                dhcsr = self.read_U32(self.DHCSR)
                if (dhcsr & self.S_RESET_ST) == 0: break
            except DAPAccess.TransferError:
                time.sleep(0.01)

'''
OpenOCD telnet-protocol python wrapper.
'''
import re
import time
import struct
import telnetlib


class OpenOCD:
    def __init__(self, host="localhost", port=4444, mode='rv', core='risc-v', speed=4000):
        self.host = host
        self.port = port

        self.tnet = telnetlib.Telnet()
        
        self.open(mode, core, speed)

    def open(self, mode='rv', core='risc-v', speed=4000):
        self.mode = mode.lower()

        self.tnet.open(self.host, self.port, 2)
        self._read()

        self.get_registers()

    def _read(self):
        try:
            s = self.tnet.read_until(b'> ', 2).decode('latin-1')
        except:
            return ''
        
        return s[s.find('\n')+1:s.rfind('\n')]
    
    def _exec(self, cmd):
        self.tnet.write(f'{cmd}\n'.encode('latin-1'))
        return self._read()

    def get_registers(self):
        self.core_regs = {}  # 'name: index' pair
        for line in self._exec('reg').splitlines():
            match = re.match(r'\((\d+)\)\s+(\w+)\s+\(/(\d+)\)', line)
            if match:
                self.core_regs[match.group(2)] = match.group(1)
        
        def add_alias(regs, name1, name2, name3):
            if name1 in regs:
                regs[name2] = regs[name1]
                regs[name3] = regs[name1]
            elif name2 in regs:
                regs[name1] = regs[name2]
                regs[name3] = regs[name2]
            elif name3 in regs:
                regs[name1] = regs[name3]
                regs[name2] = regs[name3]
            else:
                raise Exception(f'cannot find {name1}, {name2} or {name3}')

        if self.mode.startswith('arm'):
            add_alias(self.core_regs, 'r13', 'sp', 'r13 (sp)')
            add_alias(self.core_regs, 'r14', 'lr', 'r14 (lr)')
            add_alias(self.core_regs, 'r15', 'pc', 'r15 (pc)')

        elif self.mode.startswith('rv'):
            add_alias(self.core_regs, 'x1',  'ra',  '')
            add_alias(self.core_regs, 'x2',  'sp',  '')
            add_alias(self.core_regs, 'x3',  'gp',  '')
            add_alias(self.core_regs, 'x4',  'tp',  '')
            add_alias(self.core_regs, 'x5',  't0',  '')
            add_alias(self.core_regs, 'x6',  't1',  '')
            add_alias(self.core_regs, 'x7',  't2',  '')
            add_alias(self.core_regs, 'x8',  's0',  'fp')
            add_alias(self.core_regs, 'x9',  's1',  '')
            add_alias(self.core_regs, 'x10', 'a0',  '')
            add_alias(self.core_regs, 'x11', 'a1',  '')
            add_alias(self.core_regs, 'x12', 'a2',  '')
            add_alias(self.core_regs, 'x13', 'a3',  '')
            add_alias(self.core_regs, 'x14', 'a4',  '')
            add_alias(self.core_regs, 'x15', 'a5',  '')
            add_alias(self.core_regs, 'x16', 'a6',  '')
            add_alias(self.core_regs, 'x17', 'a7',  '')
            add_alias(self.core_regs, 'x18', 's2',  '')
            add_alias(self.core_regs, 'x19', 's3',  '')
            add_alias(self.core_regs, 'x20', 's4',  '')
            add_alias(self.core_regs, 'x21', 's5',  '')
            add_alias(self.core_regs, 'x22', 's6',  '')
            add_alias(self.core_regs, 'x23', 's7',  '')
            add_alias(self.core_regs, 'x24', 's8',  '')
            add_alias(self.core_regs, 'x25', 's9',  '')
            add_alias(self.core_regs, 'x26', 's10', '')
            add_alias(self.core_regs, 'x27', 's11', '')
            add_alias(self.core_regs, 'x28', 't3',  '')
            add_alias(self.core_regs, 'x29', 't4',  '')
            add_alias(self.core_regs, 'x30', 't5',  '')
            add_alias(self.core_regs, 'x31', 't6',  '')

    def write_U8(self, addr, val):
        self._exec(f'mwb {addr:#x} {val:#x}')

    def write_U16(self, addr, val):
        self._exec(f'mwh {addr:#x} {val:#x}')

    def write_U32(self, addr, val):
        self._exec(f'mww {addr:#x} {val:#x}')

    def write_U64(self, addr, val):
        self._exec(f'mwd {addr:#x} {val:#x}')

    def write_mem_U8(self, addr, data):
        index = 0
        while index < len(data):
            s = ' '.join([f'{x:#x}' for x in data[index:index+256]])
            
            self._exec(f'write_memory {addr:#x} 8 {{{s}}}')

            addr += 256
            index += 256

    def write_mem_U32(self, addr, data):
        index = 0
        while index < len(data):
            s = ' '.join([f'{x:#x}' for x in data[index:index+64]])
            
            self._exec(f'write_memory {addr:#x} 32 {{{s}}}')

            addr += 64 * 4
            index += 64

    def read_mem_(self, addr, count, width):
        data = []
        index = 0
        while index < count:    # read too much one-time will cause timeout
            res = self._exec(f'read_memory {addr:#x} {width} 256')
            if res:
                data.extend([int(x, 16) for x in res.split()])

                addr += 256 * (width // 8)
                index += 256

            else:
                break

        return data

    def read_mem_U8(self, addr, count):
        return self.read_mem_(addr, count, 8)

    def read_mem_U16(self, addr, count):
        return self.read_mem_(addr, count, 16)
    
    def read_mem_U32(self, addr, count):
        return self.read_mem_(addr, count, 32)

    def read_mem_U64(self, addr, count):
        return self.read_mem_(addr, count, 64)

    def read_U32(self, addr):
        return self.read_mem_U32(addr, 1)[0]

    def read_U64(self, addr):
        return self.read_mem_U64(addr, 1)[0]

    def read_reg(self, reg):
        res = self._exec(f'reg {self.core_regs[reg.lower()]}')

        return int(res.split(':')[1].strip(), 16)

    def read_regs(self, rlist):
        regs = {}
        for reg in rlist:
            regs[reg] = self.read_reg(reg)

        return regs

    def write_reg(self, reg, val):
        self._exec(f'reg {self.core_regs[reg.lower()]} {val:#x}')

    # halt: immediately halt after reset
    def reset(self, halt=False):
        self._exec(f'reset {"halt" if halt else "run"}')

    def halt(self):
        self._exec('halt 500')

    def step(self, addr=None):
        if addr is None:
            self._exec('step')  # single-step the target at its current code position
        else:
            self._exec(f'step {addr:#x}')   # single-step the target from specified address

    def resume(self, addr=None):
        if addr is None:
            self._exec('resume')    # resume the target at its current code position
        else:
            self._exec(f'resume {addr:#x}') # resume the target to specified address

    def halted(self):
        res = self._exec('poll')

        return 'halted' in res

    def close(self):
        self.tnet.close()

        time.sleep(0.2)


    CORE_TYPE_NAME = {
        0xC20: "Cortex-M0",
        0xC21: "Cortex-M1",
        0xC23: "Cortex-M3",
        0xC24: "Cortex-M4",
        0xC27: "Cortex-M7",
        0xC60: "Cortex-M0+",
        0x132: "STAR"
    }

    def read_core_type(self):
        if self.mode.startswith('arm'):
            CPUID = 0xE000ED00
            CPUID_PARTNO_Pos = 4
            CPUID_PARTNO_Msk = 0x0000FFF0
            
            cpuid = self.read_U32(CPUID)

            core_type = (cpuid & CPUID_PARTNO_Msk) >> CPUID_PARTNO_Pos
            
            return self.CORE_TYPE_NAME[core_type]

        elif self.mode.startswith('rv'):
            halted = self.halted()
            if not halted: self.halt()
            isa = self.read_reg('MISA')
            if not halted: self.go()

            if ((isa >> 30) & 3) == 1:
                name = 'RV32'
            elif ((isa >> 62) & 3) == 2:
                name = 'RV64'
            else:
                return 'RISC-V'

            indx = lambda chr: ord(chr) - ord('A')

            if isa & (1 << indx('I')):
                name += 'I'
            else:
                name += 'E'

            if isa & (1 << indx('M')):
                name += 'M'

            if isa & (1 << indx('A')):
                name += 'A'

            if isa & (1 << indx('F')):
                name += 'F'

            if isa & (1 << indx('D')):
                name += 'D'

            if isa & (1 << indx('C')):
                name += 'C'

            if isa & (1 << indx('B')):
                name += 'B'

            name = name.replace('IMAFD', 'G')

            return name



if __name__ == '__main__':
    ocd = OpenOCD()
    ocd.halt()
    res = ocd.read_core_type()
    print(res)
    res = ocd.read_mem_U32(0x20000000, 4)
    print([f'{x:X}' for x in res])
    ocd.write_U32(0x20000000, 0x12345678)
    ocd.write_U32(0x20000004, 0x55555555)
    ocd.write_U32(0x20000008, 0xAAAAAAAA)
    ocd.write_U32(0x2000000C, 0x5A5A5A5A)
    res = ocd.read_mem_U32(0x20000000, 4)
    print([f'{x:X}' for x in res])

#coding: utf-8
import time

from .flash import Flash


FLASH_KR = 0x40022004
FLASH_SR = 0x4002200C
FLASH_CR = 0x40022010
FLASH_AR = 0x40022014

FLASH_KR_KEY1 = 0X45670123
FLASH_KR_KEY2 = 0XCDEF89AB

FLASH_SR_BUSY   = (1 << 0)

FLASH_CR_PWRITE = (1 << 0)  # Page  Write
FLASH_CR_SERASE = (1 << 1)  # Sect  Erase
FLASH_CR_CERASE = (1 << 2)  # Chip  Erase
FLASH_CR_ESTART = (1 << 6)  # Erase Start
FLASH_CR_LOCK   = (1 << 7)


class STM32F103C8(object):
    CHIP_CORE = 'Cortex-M3'
    
    PAGE_SIZE = 1024 * 1
    SECT_SIZE = 1024 * 1
    CHIP_SIZE = 1024 * 64

    def __init__(self, jlink):
        super(STM32F103C8, self).__init__()
        
        self.jlink = jlink

        self.flash = Flash(self.jlink, STM32F103C8_flash_algo)

    def unlock(self):
        self.jlink.write_U32(FLASH_KR, FLASH_KR_KEY1)
        self.jlink.write_U32(FLASH_KR, FLASH_KR_KEY2)

    def lock(self):
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_LOCK)

    def wait_ready(self):
        while self.jlink.read_U32(FLASH_SR) & FLASH_SR_BUSY:
            time.sleep(0.001)
    
    def sect_erase(self, addr, size):
        self.unlock()
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_SERASE)
        for i in range(0, (size + self.SECT_SIZE - 1) // self.SECT_SIZE):
            self.jlink.write_U32(FLASH_AR, 0x08000000 + addr + self.SECT_SIZE * i)
            self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_ESTART)
            self.wait_ready()
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) &~FLASH_CR_SERASE)
        self.lock()

    def chip_write(self, addr, data):
        data = data + [0xFF] * (self.PAGE_SIZE - len(data)%self.PAGE_SIZE)

        self.sect_erase(addr, len(data))

        self.flash.Init(0, 0, 2)
        for i in range(0, len(data)//self.PAGE_SIZE):
            self.flash.ProgramPage(0x08000000 + addr + self.PAGE_SIZE * i, data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)])
        self.flash.UnInit(2)

    def chip_read(self, addr, size, buff):
        data = self.jlink.read_mem(0x08000000 + addr, size)

        buff.extend([ord(x) for x in data])


class STM32F103RC(STM32F103C8):
    PAGE_SIZE = 1024 * 1
    SECT_SIZE = 1024 * 2
    CHIP_SIZE = 1024 * 256

    def __init__(self, jlink):
        super(STM32F103RC, self).__init__(jlink)

        self.flash = Flash(self.jlink, STM32F103RC_flash_algo)


STM32F103C8_flash_algo = {
    'load_address' : 0x20000000,
    'instructions' : [
        0xE00ABE00, 0x062D780D, 0x24084068, 0xD3000040, 0x1E644058, 0x1C49D1FA, 0x2A001E52, 0x4770D1F2,
        0x4603B510, 0x4C442000, 0x48446020, 0x48446060, 0x46206060, 0xF01069C0, 0xD1080F04, 0x5055F245,
        0x60204C40, 0x60602006, 0x70FFF640, 0x200060A0, 0x4601BD10, 0x69004838, 0x0080F040, 0x61104A36,
        0x47702000, 0x69004834, 0x0004F040, 0x61084932, 0x69004608, 0x0040F040, 0xE0036108, 0x20AAF64A,
        0x60084930, 0x68C0482C, 0x0F01F010, 0x482AD1F6, 0xF0206900, 0x49280004, 0x20006108, 0x46014770,
        0x69004825, 0x0002F040, 0x61104A23, 0x61414610, 0xF0406900, 0x61100040, 0xF64AE003, 0x4A2120AA,
        0x481D6010, 0xF01068C0, 0xD1F60F01, 0x6900481A, 0x0002F020, 0x61104A18, 0x47702000, 0x4603B510,
        0xF0201C48, 0xE0220101, 0x69004813, 0x0001F040, 0x61204C11, 0x80188810, 0x480FBF00, 0xF01068C0,
        0xD1FA0F01, 0x6900480C, 0x0001F020, 0x61204C0A, 0x68C04620, 0x0F14F010, 0x4620D006, 0xF04068C0,
        0x60E00014, 0xBD102001, 0x1C921C9B, 0x29001E89, 0x2000D1DA, 0x0000E7F7, 0x40022000, 0x45670123,
        0xCDEF89AB, 0x40003000, 0x00000000
    ],

    'pc_Init'            : 0x20000021,
    'pc_UnInit'          : 0x20000053,
    'pc_EraseSector'     : 0x2000009F,
    'pc_ProgramPage'     : 0x200000DD,
    'pc_Verify'          : 0x12000001F,
    'pc_EraseChip'       : 0x20000065,
    'pc_BlankCheck'      : 0x12000001F,
    'pc_Read'            : 0x12000001F,
    
    'static_base'        : 0x20000400,
    'begin_data'         : 0x20000800,
    'begin_stack'        : 0x20001000,

    'analyzer_supported' : False,

    # Relative region addresses and sizes
    'ro_start'           : 0x00000000,
    'ro_size'            : 0x00000128,
    'rw_start'           : 0x00000128,
    'rw_size'            : 0x00000004,
    'zi_start'           : 0x0000012C,
    'zi_size'            : 0x00000000,

    # Flash information
    'flash_start'        : 0x08000000,
    'flash_size'         : 0x00020000,
    'flash_page_size'    : 0x00000400,
    'sector_sizes': (
        (0x00000, 0x00400),
    )
}


STM32F103RC_flash_algo = { 
    'load_address' : 0x20000000,
    'instructions' : [
        0xE00ABE00, 0x062D780D, 0x24084068, 0xD3000040, 0x1E644058, 0x1C49D1FA, 0x2A001E52, 0x4770D1F2,
        0x4603B510, 0x4C442000, 0x48446020, 0x48446060, 0x46206060, 0xF01069C0, 0xD1080F04, 0x5055F245,
        0x60204C40, 0x60602006, 0x70FFF640, 0x200060A0, 0x4601BD10, 0x69004838, 0x0080F040, 0x61104A36,
        0x47702000, 0x69004834, 0x0004F040, 0x61084932, 0x69004608, 0x0040F040, 0xE0036108, 0x20AAF64A,
        0x60084930, 0x68C0482C, 0x0F01F010, 0x482AD1F6, 0xF0206900, 0x49280004, 0x20006108, 0x46014770,
        0x69004825, 0x0002F040, 0x61104A23, 0x61414610, 0xF0406900, 0x61100040, 0xF64AE003, 0x4A2120AA,
        0x481D6010, 0xF01068C0, 0xD1F60F01, 0x6900481A, 0x0002F020, 0x61104A18, 0x47702000, 0x4603B510,
        0xF0201C48, 0xE0220101, 0x69004813, 0x0001F040, 0x61204C11, 0x80188810, 0x480FBF00, 0xF01068C0,
        0xD1FA0F01, 0x6900480C, 0x0001F020, 0x61204C0A, 0x68C04620, 0x0F14F010, 0x4620D006, 0xF04068C0,
        0x60E00014, 0xBD102001, 0x1C921C9B, 0x29001E89, 0x2000D1DA, 0x0000E7F7, 0x40022000, 0x45670123,
        0xCDEF89AB, 0x40003000, 0x00000000
    ],

    'pc_Init'            : 0x20000021,
    'pc_UnInit'          : 0x20000053,
    'pc_EraseSector'     : 0x2000009F,
    'pc_ProgramPage'     : 0x200000DD,
    'pc_Verify'          : 0x12000001F,
    'pc_EraseChip'       : 0x20000065,
    'pc_BlankCheck'      : 0x12000001F,
    'pc_Read'            : 0x12000001F,
    
    'static_base'        : 0x20000400,
    'begin_data'         : 0x20000800,
    'begin_stack'        : 0x20001000,

    'analyzer_supported' : False,

    # Relative region addresses and sizes
    'ro_start'           : 0x00000000,
    'ro_size'            : 0x00000128,
    'rw_start'           : 0x00000128,
    'rw_size'            : 0x00000004,
    'zi_start'           : 0x0000012C,
    'zi_size'            : 0x00000000,

    # Flash information
    'flash_start'        : 0x08000000,
    'flash_size'         : 0x00080000,
    'flash_page_size'    : 0x00000400,
    'sector_sizes': (
        (0x00000, 0x00800),
    )
}

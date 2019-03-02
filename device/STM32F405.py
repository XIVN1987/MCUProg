#coding: utf-8
import time

from .flash import Flash


FLASH_KR = 0x40023C04
FLASH_SR = 0x40023C0C
FLASH_CR = 0x40023C10

FLASH_KR_KEY1 = 0x45670123
FLASH_KR_KEY2 = 0xCDEF89AB

FLASH_SR_BUSY   = (1 <<16)

FLASH_CR_WRITE  = (1 << 0)
FLASH_CR_SERASE = (1 << 1)  #Sect  Erase
FLASH_CR_CERASE = (1 << 2)  #Chip  Erase
FLASH_CR_ESTART = (1 <<16)  #Erase Start
FLASH_CR_LOCK   = (1 <<31)

FLASH_CR_SECT_MASK  = 0xFFFFFF07

FLASH_CR_PSIZE_MASK = 0xFFFFFCFF    # 烧写单位：字节、半字、字
FLASH_CR_PSIZE_BYTE = 0x00000000
FLASH_CR_PSIZE_HALF = 0x00000100
FLASH_CR_PSIZE_WORD = 0x00000200


class STM32F405RG(object):
    CHIP_CORE = 'Cortex-M4'

    PAGE_SIZE = 1024 * 1   
    SECT_SIZE = 1024 * 16   # 前4个扇区16K、第5个扇区64K、后面的扇区128K
    CHIP_SIZE = 1024 * 1024 # 1MByte

    @classmethod
    def addr2sect(cls, addr):
        if   addr < 1024 *  64:  return (addr             ) // (1024 *  16)
        elif addr < 1024 * 128:  return (addr - 1024 *  64) // (1024 *  64) + 4
        else:                    return (addr - 1024 * 128) // (1024 * 128) + 5

    def __init__(self, jlink):
        super(STM32F405RG, self).__init__()
        
        self.jlink  = jlink

        self.flash = Flash(self.jlink, STM32F405RG_flash_algo)

    def unlock(self):
        self.jlink.write_U32(FLASH_KR, FLASH_KR_KEY1)
        self.jlink.write_U32(FLASH_KR, FLASH_KR_KEY2)

    def lock(self):
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_LOCK)

    def wait_ready(self):
        while self.jlink.read_U32(FLASH_SR) & FLASH_SR_BUSY:
            pass
    
    def sect_erase(self, addr, size):
        self.unlock()
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) & FLASH_CR_PSIZE_MASK)
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_PSIZE_WORD)
        for i in range(self.addr2sect(addr), self.addr2sect(addr+size)):
            self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) & FLASH_CR_SECT_MASK)
            self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_SERASE | (i << 3))
            self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) | FLASH_CR_ESTART)
            self.wait_ready()
        self.jlink.write_U32(FLASH_CR, self.jlink.read_U32(FLASH_CR) &~FLASH_CR_SERASE)
        self.lock()

    def chip_write(self, addr, data):
        if len(data)%self.PAGE_SIZE:
            data = data + [0xFF] * (self.PAGE_SIZE - len(data)%self.PAGE_SIZE)

        self.sect_erase(addr, len(data))

        self.flash.Init(0, 0, 2)
        for i in range(0, len(data)//self.PAGE_SIZE):
            self.flash.ProgramPage(0x08000000 + addr + self.PAGE_SIZE * i, data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)])
        self.flash.UnInit(2)

    def chip_read(self, addr, size, buff):
        data = self.jlink.read_mem(0x08000000 + addr, size)

        buff.extend([ord(x) for x in data])


STM32F405RG_flash_algo = {
    'load_address' : 0x20000000,
    'instructions' : [
        0xE00ABE00, 0x062D780D, 0x24084068, 0xD3000040, 0x1E644058, 0x1C49D1FA, 0x2A001E52, 0x4770D1F2,
        0x0E000300, 0xD3022820, 0x1D000940, 0x28104770, 0x0900D302, 0x47701CC0, 0x47700880, 0x49414842,
        0x49426041, 0x21006041, 0x68C16001, 0x431122F0, 0x694060C1, 0xD4060680, 0x493D483E, 0x21066001,
        0x493D6041, 0x20006081, 0x48374770, 0x05426901, 0x61014311, 0x47702000, 0x4833B510, 0x24046901,
        0x61014321, 0x03A26901, 0x61014311, 0x4A314933, 0x6011E000, 0x03DB68C3, 0x6901D4FB, 0x610143A1,
        0xBD102000, 0xF7FFB530, 0x4927FFBB, 0x23F068CA, 0x60CA431A, 0x610C2402, 0x0700690A, 0x43020E40,
        0x6908610A, 0x431003E2, 0x48246108, 0xE0004A21, 0x68CD6010, 0xD4FB03ED, 0x43A06908, 0x68C86108,
        0x0F000600, 0x68C8D003, 0x60C84318, 0xBD302001, 0x4D15B570, 0x08891CC9, 0x008968EB, 0x433326F0,
        0x230060EB, 0x4B16612B, 0x692CE017, 0x612C431C, 0x60046814, 0x03E468EC, 0x692CD4FC, 0x00640864,
        0x68EC612C, 0x0F240624, 0x68E8D004, 0x60E84330, 0xBD702001, 0x1D121D00, 0x29001F09, 0x2000D1E5,
        0x0000BD70, 0x45670123, 0x40023C00, 0xCDEF89AB, 0x00005555, 0x40003000, 0x00000FFF, 0x0000AAAA,
        0x00000201, 0x00000000
    ],

    'pc_Init'            : 0x2000003D,
    'pc_UnInit'          : 0x2000006B,
    'pc_EraseSector'     : 0x200000A5,
    'pc_ProgramPage'     : 0x200000F1,
    'pc_Verify'          : 0x12000001F,
    'pc_EraseChip'       : 0x20000079,
    'pc_BlankCheck'      : 0x12000001F,
    'pc_Read'            : 0x12000001F,
    
    'static_base'        : 0x20000400,
    'begin_data'         : 0x20000800,
    'begin_stack'        : 0x20001000,

    'analyzer_supported' : False,

    # Relative region addresses and sizes
    'ro_start'           : 0x00000000,
    'ro_size'            : 0x00000144,
    'rw_start'           : 0x00000144,
    'rw_size'            : 0x00000004,
    'zi_start'           : 0x00000148,
    'zi_size'            : 0x00000000,

    # Flash information
    'flash_start'        : 0x08000000,
    'flash_size'         : 0x00100000,
    'flash_page_size'    : 0x00000400,
    'sector_sizes': (
        (0x00000, 0x04000),
        (0x10000, 0x10000),
        (0x20000, 0x20000),
    )
}

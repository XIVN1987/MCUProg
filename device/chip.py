import importlib

from . import flash
from . import flashAlgo


class Chip(object):
    CHIP_CORE = 'Cortex-M0'

    def __init__(self, xlink, falgo):
        super(Chip, self).__init__()

        if isinstance(falgo, tuple):
            name, addr, size, path = falgo

            self.falgo = flashAlgo.FlashAlgo(path, addr, size).flash_algo
            if self.falgo['arch'] == 'RISC-V':  self.CHIP_CORE = 'RISC-V'

        else:
            self.falgo = importlib.import_module(f'.{falgo}', 'FlashAlgo').flash_algo

        if not xlink:   # used for CHIP_SIZE, SECT_SIZE, PAGE_SIZE access
            return

        self.xlink = xlink

        self.flash = flash.Flash(self.xlink, self.falgo)

    @property
    def CHIP_BASE(self):
        return self.falgo['flash_start']

    @property
    def CHIP_SIZE(self):
        return self.falgo['flash_size']

    @property
    def SECT_SKIP(self):    # 有些 Flash 前几个扇区不能使用
        return 0

    @property
    def SECT_SIZE(self):
        starts, sizes = zip(*self.falgo['sector_sizes'])

        return min(sizes)   # 简化处理，大扇区多擦几次也不会出错

    @property
    def PAGE_SIZE(self):
        return self.falgo['flash_page_size']

    def chip_erase(self):
        self.flash.Init(0, 0, 1)
        self.flash.EraseChip()
        self.flash.UnInit(1)

    def sect_erase(self, addr, size):
        self.flash.Init(0, 0, 1)
        for i in range(size // self.SECT_SIZE):
            self.flash.EraseSector(self.CHIP_BASE + addr + self.SECT_SIZE * i)
        self.flash.UnInit(1)

    def chip_write(self, addr, data):
        data += b'\xFF' * (-len(data) % self.PAGE_SIZE)

        self.flash.Init(0, 0, 1)
        for i in range((len(data) + self.SECT_SIZE - 1) // self.SECT_SIZE):
            self.flash.EraseSector(self.CHIP_BASE + addr + self.SECT_SIZE * i)
        self.flash.UnInit(1)

        self.flash.Init(0, 0, 2)
        for i in range(len(data) // self.PAGE_SIZE):
            self.flash.ProgramPage(self.CHIP_BASE + addr + self.PAGE_SIZE * i, data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)])
        self.flash.UnInit(2)

        self.flash.Init(0, 0, 3)
        if self.falgo['pc_Verify'] >= 0xFFFFFFFF:
            for i in range(len(data) // self.PAGE_SIZE):
                print(f'Verify @ 0x{self.CHIP_BASE + addr + self.PAGE_SIZE * i:08X}')
                rdata = self.xlink.read_mem_U8(self.CHIP_BASE + addr + self.PAGE_SIZE * i, self.PAGE_SIZE)
                wdata = data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)]
                if bytes(rdata) != wdata:
                    for j in range(self.PAGE_SIZE):
                        if rdata[j] != wdata[j]:
                            print(f'byte @ 0x{self.CHIP_BASE + addr + self.PAGE_SIZE * i + j:08X} is 0x{rdata[j]:02X}, expected 0x{wdata[j]:02X}')
                    break
            else:
                print('Verify OK')

        else:
            for i in range(len(data) // self.PAGE_SIZE):
                self.flash.Verify(self.CHIP_BASE + addr + self.PAGE_SIZE * i, data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)])
        self.flash.UnInit(3)

    def chip_read(self, addr, size, buff):
        if self.falgo['pc_Read'] >= 0xFFFFFFFF:
            for i in range(size // self.PAGE_SIZE):
                print(f'Read @ 0x{self.CHIP_BASE + addr + self.PAGE_SIZE * i:08X}')
                data = self.xlink.read_mem_U8(self.CHIP_BASE + addr + self.PAGE_SIZE * i, self.PAGE_SIZE)

                buff.extend(data)

        else:
            for i in range(size // self.PAGE_SIZE):
                self.flash.Read(self.CHIP_BASE + addr + self.PAGE_SIZE * i, self.PAGE_SIZE)

                data = self.xlink.read_mem_U8(self.falgo['begin_data'], self.PAGE_SIZE)

                buff.extend(data)

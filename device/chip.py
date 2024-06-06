import math
import importlib

from . import flash


class Chip(object):
    CHIP_CORE = 'Cortex-M0'

    def __init__(self, xlink, falgo):
        super(Chip, self).__init__()

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
        self.flash.Init(0, 0, 1)
        for i in range(math.ceil(len(data) / self.SECT_SIZE)):
            self.flash.EraseSector(self.CHIP_BASE + addr + self.SECT_SIZE * i)
        self.flash.UnInit(1)

        self.flash.Init(0, 0, 2)
        for i in range(math.ceil(len(data) / self.PAGE_SIZE)):
            self.flash.ProgramPage(self.CHIP_BASE + addr + self.PAGE_SIZE * i, data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)])
        self.flash.UnInit(2)

        self.flash.Init(0, 0, 3)
        for i in range(math.ceil(len(data) / self.PAGE_SIZE)):
            self.flash.Verify(self.CHIP_BASE + addr + self.PAGE_SIZE * i, data[self.PAGE_SIZE*i : self.PAGE_SIZE*(i+1)])
        self.flash.UnInit(3)

    def chip_read(self, addr, size, buff):
        if self.falgo['pc_Read'] > 0xFFFFFFFF:
            c_char_Array = self.xlink.read_mem(self.CHIP_BASE + addr, size)

            buff.extend(list(bytes(c_char_Array)))

        else:
            for i in range(0, size // self.PAGE_SIZE):
                self.flash.Read(self.CHIP_BASE + addr + self.PAGE_SIZE * i, self.PAGE_SIZE)

                c_char_Array = self.xlink.read_mem(self.falgo['begin_data'], self.PAGE_SIZE)

                buff.extend(list(bytes(c_char_Array)))

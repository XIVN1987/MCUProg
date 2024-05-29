from . import chip


class NUM480(chip.Chip):
    def __init__(self, xlink):
        super(NUM480, self).__init__(xlink, 'M481_AP_512')


class MT7687(chip.Chip):
    def __init__(self, xlink):
        super(MT7687, self).__init__(xlink, 'MT7687_32M_MXIC')

    def chip_read(self, addr, size, buff):
        # 必须按一下复位键，然后执行以下三条语句，才能从内存空间读到值
        self.xlink.write_U32(0x8300F050, 0x76371688)
        self.xlink.write_U32(0x8300F050, 0x76371688)
        self.xlink.write_U32(0x8300F050, 0x76371688)

        super(MT7687, self).chip_read(addr, size, buff)

from . import chip


class AT32F435RG(chip.Chip):
    def __init__(self, xlink):
        super(AT32F435RG, self).__init__(xlink, 'AT32F435_1024')


class AT32F437VM(chip.Chip):
    def __init__(self, xlink):
        super(AT32F437VM, self).__init__(xlink, 'AT32F437_4032')

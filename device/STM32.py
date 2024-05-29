from . import chip


class STM32F103C8(chip.Chip):
    def __init__(self, xlink):
        super(STM32F103C8, self).__init__(xlink, 'STM32F10x_128')


class STM32F103RC(chip.Chip):
    def __init__(self, xlink):
        super(STM32F103RC, self).__init__(xlink, 'STM32F10x_512')


class STM32F405RG(chip.Chip):
    def __init__(self, xlink):
        super(STM32F405RG, self).__init__(xlink, 'STM32F4xx_1024')

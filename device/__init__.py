import collections

import STM32F103
import STM32F405
import NUM480
import MT7687

Devices = collections.OrderedDict([
    ('STM32F103C8', STM32F103.STM32F103C8),
    ('STM32F103RC', STM32F103.STM32F103RC),
    ('STM32F405RG', STM32F405.STM32F405RG),
    ('NUM480',      NUM480.NUM480),
    ('MT7687',      MT7687.MT7687),
])
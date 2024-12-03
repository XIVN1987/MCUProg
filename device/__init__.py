import collections

from . import MT7687
from . import STM32F103_LS
from . import STM32F405_LS


Devices = collections.OrderedDict([
    ('MT7687',         MT7687.MT7687),
    ('STM32F103C8-LS', STM32F103_LS.STM32F103C8),
   	('STM32F103RC-LS', STM32F103_LS.STM32F103RC),
    ('STM32F405RG-LS', STM32F405_LS.STM32F405RG),
])

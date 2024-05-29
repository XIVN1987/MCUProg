import collections

from . import AT32
from . import STM32
from . import XXM32
from . import STM32F103_LS
from . import STM32F405_LS


Devices = collections.OrderedDict([
    ('NUM480',         XXM32.NUM480),
    ('MT7687',         XXM32.MT7687),
    ('AT32F435RG',     AT32.AT32F435RG),
    ('AT32F437VM',     AT32.AT32F437VM),
    ('STM32F103C8',    STM32.STM32F103C8),
    ('STM32F103RC',    STM32.STM32F103RC),
    ('STM32F405RG',    STM32.STM32F405RG),
    ('STM32F103C8-LS', STM32F103_LS.STM32F103C8),
   	('STM32F103RC-LS', STM32F103_LS.STM32F103RC),
    ('STM32F405RG-LS', STM32F405_LS.STM32F405RG),
])

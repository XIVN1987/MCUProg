import collections

from . import AT32F435
from . import STM32F103
from . import STM32F103_LS
from . import STM32F405
from . import STM32F405_LS
from . import NUM480
from . import MT7687

Devices = collections.OrderedDict([
    ('AT32F435RG',     AT32F435.AT32F435RG),
    ('AT32F437VM',     AT32F435.AT32F437VM),
    ('STM32F103C8',    STM32F103.STM32F103C8),
    ('STM32F103C8-LS', STM32F103_LS.STM32F103C8),
    ('STM32F103RC',    STM32F103.STM32F103RC),
   	('STM32F103RC-LS', STM32F103_LS.STM32F103RC),
    ('STM32F405RG',    STM32F405.STM32F405RG),
    ('STM32F405RG-LS', STM32F405_LS.STM32F405RG),
    ('NUM480',         NUM480.NUM480),
    ('MT7687',         MT7687.MT7687),
])

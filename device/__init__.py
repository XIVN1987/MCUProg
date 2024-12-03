import collections

from . import MT7687
from . import STM32F103_LS
from . import STM32F405_LS


Devices = collections.OrderedDict([
    ('MT7687',         MT7687.MT7687),
])

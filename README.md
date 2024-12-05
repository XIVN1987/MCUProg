# MCUProg
MCU programmer for J-LINK and DAPLink, using Keil MDK's \*.FLM Flashing Algorithm

To run this software, you need python 3.6+ and pyqt5.

To use DAPLink, you need additional pyusb for CMSIS-DAPv2 and another usb-backend for CMSIS-DAPv1 (hidapi or pywinusb for windows, hidapi for mac, pyusb for linux).

``` shell
pip install PyQt5 pyusb hidapi six pyelftools
```

![](./%E6%88%AA%E5%9B%BE.jpg)

## add new chip
### Simple method
add chip's name and FLM file path in `devices.txt` as below:
```
STM32F103C8 FlashAlgo/STM32F10x_128.FLM
```
and then, MCUProg can erase/write STM32F103C8.

In the previous configuration, we assume that chip's RAM locates at 0x20000000, and FLM uses 4KB RAM.

If the default values do not apply to your chip, you can explicitly specify the address and size of RAM used by FLM as below:
```
NUM480      0x20000000  0x2000  FlashAlgo/M481_AP_512.FLM
```

### Powerful method
1. put new_chip.FLM to FlashAlgo folder
2. run FlashAlgo/flash_algo.py to generate new_chip_algo.py
3. add below code in device/new_chip.py file:
``` python
class new_chip(chip.Chip):
    def __init__(self, xlink):
        super(new_chip, self).__init__(xlink, 'new_chip_algo')
```
4. add below code in device/\_\_init__.py file:
``` python
('new_chip',       new_chip.new_chip),
```

In class new_chip, you can add arbitrary python code to do something FLM don't support, so i call it 'Powerful method'.

FlashAlgo/flash_algo.py is used to parse Keil MDK's \*.FLM file and extract code and its runing information into a python dict.

## multi file programming
By using `STM32_withBoot.ini` with content as below, you can write multi file to different address one-time for same flash algorithm.
``` ini
[BOOT]
addr = 0x00000
path = D:/work_dir/STM32-Boot-Demo/STM32_UserBoot/out/STM32_stdperiph_lib.hex

[APP]
addr = 0x10000
path = D:/work_dir/STM32-Boot-Demo/STM32_App/out/STM32_stdperiph_lib.bin
```

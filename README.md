# MCUProg
MCU programmer for J-LINK and DAPLink, using Keil MDK's \*.FLM Flashing Algorithm

To run this software, you need python 3.6 and pyqt5.

To use DAPLink, you need additional pyusb for CMSIS-DAPv2 and another usb-backend for CMSIS-DAPv1 (hidapi or pywinusb for windows, hidapi for mac, pyusb for linux).

![](./%E6%88%AA%E5%9B%BE.jpg)

FlashAlgo/flash_algo.py is used to parse Keil MDK's \*.FLM file and extract code and its runing information into a python dict. And then you can modify the generated code to add new device support.


## add new chip
1. put new_chip.FLM to FlashAlgo folder
2. run flash_algo.py in FlashAlgo folder, generate new_chip.py
3. add below code in device/XXM32.py file:
``` python
class new_chip(chip.Chip):
    def __init__(self, xlink):
        super(new_chip, self).__init__(xlink, 'new_chip')
```
4. add below code in device/\_\_init__.py file:
``` python
('new_chip',       XXM32.new_chip),
```


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

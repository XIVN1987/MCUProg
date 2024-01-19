# MCUProg
MCU programmer for J-LINK and DAPLink, using Keil MDK's \*.FLM Flashing Algorithm

To run this software, you need python 3.6 and pyqt5.

To use DAPLink, you need additional pyusb for CMSIS-DAPv2 and another usb-backend for CMSIS-DAPv1 (hidapi or pywinusb for windows, hidapi for mac, pyusb for linux).

![](./%E6%88%AA%E5%9B%BE.jpg)

FlashAlgo/flash_algo.py is used to parse Keil MDK's \*.FLM file and extract code and its runing information into a python dict. And then you can modify the generated code to add new device support.

# pyOCD debugger
# Copyright (c) 2019 Arm Limited
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .interface import Interface
from .common import (filter_device_by_class, is_known_cmsis_dap_vid_pid)
from ..dap_access_api import DAPAccessIntf
import logging
import os
import threading
import six
from time import sleep
import errno
import platform

LOG = logging.getLogger(__name__)

try:
    import usb.core
    import usb.util
except:
    IS_AVAILABLE = False
else:
    IS_AVAILABLE = True

class PyUSBv2(Interface):
    """!
    @brief CMSIS-DAPv2 interface using pyUSB.
    """

    isAvailable = IS_AVAILABLE

    def __init__(self):
        super(PyUSBv2, self).__init__()
        self.ep_out = None
        self.ep_in = None
        self.ep_swo = None
        self.dev = None
        self.intf_number = None
        self.serial_number = None
        self.kernel_driver_was_attached = False
        self.closed = True
        self.thread = None
        self.rx_stop_event = None
        self.swo_thread = None
        self.swo_stop_event = None
        self.rcv_data = []
        self.swo_data = []
        self.read_sem = threading.Semaphore(0)
        self.packet_size = 512
        self.is_swo_running = False
    
    @property
    def has_swo_ep(self):
        return self.ep_swo is not None

    def open(self):
        assert self.closed is True

        # Get device handle
        dev = usb.core.find(custom_match=HasCmsisDapv2Interface(self.serial_number))
        if dev is None:
            raise DAPAccessIntf.DeviceError("Device %s not found" %
                                            self.serial_number)

        # get active config
        config = dev.get_active_configuration()

        # Get CMSIS-DAPv2 interface
        interface = usb.util.find_descriptor(config, custom_match=_match_cmsis_dap_v2_interface)
        if interface is None:
            raise DAPAccessIntf.DeviceError("Device %s has no CMSIS-DAPv2 interface" %
                                            self.serial_number)
        interface_number = interface.bInterfaceNumber

        # Find endpoints. CMSIS-DAPv2 endpoints are in a fixed order.
        try:
            ep_out = interface.endpoints()[0]
            ep_in = interface.endpoints()[1]
            ep_swo = interface.endpoints()[2] if len(interface.endpoints()) > 2 else None
        except IndexError:
            raise DAPAccessIntf.DeviceError("CMSIS-DAPv2 device %s is missing endpoints" %
                                            self.serial_number)

        # Explicitly claim the interface
        try:
            usb.util.claim_interface(dev, interface_number)
        except usb.core.USBError as exc:
            raise six.raise_from(DAPAccessIntf.DeviceError("Unable to open device"), exc)

        # Update all class variables if we made it here
        self.ep_out = ep_out
        self.ep_in = ep_in
        self.ep_swo = ep_swo
        self.dev = dev
        self.intf_number = interface_number

        # Start RX thread as the last step
        self.closed = False
        self.start_rx()

    def start_rx(self):
        # Flush the RX buffers by reading until timeout exception
        try:
            while True:
                self.ep_in.read(self.ep_in.wMaxPacketSize, 1)
        except usb.core.USBError:
            # USB timeout expected
            pass

        # Start RX thread
        self.rx_stop_event = threading.Event()
        thread_name = "CMSIS-DAP receive (%s)" % self.serial_number
        self.thread = threading.Thread(target=self.rx_task, name=thread_name)
        self.thread.daemon = True
        self.thread.start()
    
    def start_swo(self):
        self.swo_stop_event = threading.Event()
        thread_name = "SWO receive (%s)" % self.serial_number
        self.swo_thread = threading.Thread(target=self.swo_rx_task, name=thread_name)
        self.swo_thread.daemon = True
        self.swo_thread.start()
        self.is_swo_running = True
    
    def stop_swo(self):
        self.swo_stop_event.set()
        self.swo_thread.join()
        self.swo_thread = None
        self.swo_stop_event = None
        self.is_swo_running = False

    def rx_task(self):
        try:
            while not self.rx_stop_event.is_set():
                self.read_sem.acquire()
                if not self.rx_stop_event.is_set():
                    self.rcv_data.append(self.ep_in.read(self.ep_in.wMaxPacketSize, 10 * 1000))
        finally:
            # Set last element of rcv_data to None on exit
            self.rcv_data.append(None)

    def swo_rx_task(self):
        try:
            while not self.swo_stop_event.is_set():
                try:
                    self.swo_data.append(self.ep_swo.read(self.ep_swo.wMaxPacketSize, 10 * 1000))
                except usb.core.USBError:
                    pass
        finally:
            # Set last element of swo_data to None on exit
            self.swo_data.append(None)

    @staticmethod
    def get_all_connected_interfaces():
        """! @brief Returns all the connected devices with a CMSIS-DAPv2 interface."""
        # find all cmsis-dap devices
        try:
            all_devices = usb.core.find(find_all=True, custom_match=HasCmsisDapv2Interface())
        except usb.core.NoBackendError:
            return []

        # iterate on all devices found
        boards = []
        for board in all_devices:
            new_board = PyUSBv2()
            new_board.vid = board.idVendor
            new_board.pid = board.idProduct
            new_board.product_name = board.product
            new_board.vendor_name = board.manufacturer
            new_board.serial_number = board.serial_number
            boards.append(new_board)

        return boards

    def write(self, data):
        """! @brief Write data on the OUT endpoint."""

        report_size = self.packet_size
        if self.ep_out:
            report_size = self.ep_out.wMaxPacketSize

        for _ in range(report_size - len(data)):
            data.append(0)

        self.read_sem.release()

        self.ep_out.write(data)
        #logging.debug('sent: %s', data)

    def read(self):
        """! @brief Read data on the IN endpoint."""
        while len(self.rcv_data) == 0:
            sleep(0)

        if self.rcv_data[0] is None:
            raise DAPAccessIntf.DeviceError("Device %s read thread exited unexpectedly" % self.serial_number)
        return self.rcv_data.pop(0)

    def read_swo(self):
        # Accumulate all available SWO data.
        data = bytearray()
        while len(self.swo_data):
            if self.swo_data[0] is None:
                raise DAPAccessIntf.DeviceError("Device %s SWO thread exited unexpectedly" % self.serial_number)
            data += self.swo_data.pop(0)
        
        return data

    def set_packet_count(self, count):
        # No interface level restrictions on count
        self.packet_count = count

    def set_packet_size(self, size):
        self.packet_size = size

    def get_serial_number(self):
        return self.serial_number

    def close(self):
        """! @brief Close the USB interface."""
        assert self.closed is False

        if self.is_swo_running:
            self.stop_swo()
        self.closed = True
        self.rx_stop_event.set()
        self.read_sem.release()
        self.thread.join()
        assert self.rcv_data[-1] is None
        self.rcv_data = []
        self.swo_data = []
        usb.util.release_interface(self.dev, self.intf_number)
        usb.util.dispose_resources(self.dev)
        self.ep_out = None
        self.ep_in = None
        self.ep_swo = None
        self.dev = None
        self.intf_number = None
        self.thread = None

def _match_cmsis_dap_v2_interface(interface):
    """! @brief Returns true for a CMSIS-DAP v2 interface.
    
    This match function performs several tests on the provided USB interface descriptor, to
    determine whether it is a CMSIS-DAPv2 interface. These requirements must be met by the
    interface:
    
    1. Have an interface name string containing "CMSIS-DAP".
    2. bInterfaceClass must be 0xff.
    3. bInterfaceSubClass must be 0.
    4. Must have bulk out and bulk in endpoints, with an optional extra bulk in endpoint, in
        that order.
    """
    try:
        interface_name = usb.util.get_string(interface.device, interface.iInterface)
        
        # This tells us whether the interface is CMSIS-DAP, but not whether it's v1 or v2.
        if (interface_name is None) or ("CMSIS-DAP" not in interface_name):
            return False

        # Now check the interface class to distinguish v1 from v2.
        if (interface.bInterfaceClass != 0xFF) or (interface.bInterfaceSubClass != 0):
            return False

        # Must have either 2 or 3 endpoints.
        if interface.bNumEndpoints not in (2, 3):
            return False
        
        check_ep = lambda interface, ep_index, ep_dir, ep_type: \
                    usb.util.endpoint_direction(interface[ep_index].bEndpointAddress) == ep_dir \
                and usb.util.endpoint_type(interface[ep_index].bmAttributes) == ep_type

        # Endpoint 0 must be bulk out.
        if not check_ep(interface, 0, usb.util.ENDPOINT_OUT, usb.util.ENDPOINT_TYPE_BULK):
            return False
        
        # Endpoint 1 must be bulk in.
        if not check_ep(interface, 1, usb.util.ENDPOINT_IN, usb.util.ENDPOINT_TYPE_BULK):
            return False
        
        # Endpoint 2 is optional. If present it must be bulk in.
        if (interface.bNumEndpoints == 3) \
            and not check_ep(interface, 2, usb.util.ENDPOINT_IN, usb.util.ENDPOINT_TYPE_BULK):
            return False
        
        # All checks passed, this is a CMSIS-DAPv2 interface!
        return True

    except (UnicodeDecodeError, IndexError):
        # UnicodeDecodeError exception can be raised if the device has a corrupted interface name.
        # Certain versions of STLinkV2 are known to have this problem. If we can't read the
        # interface name, there's no way to tell if it's a CMSIS-DAPv2 interface.
        #
        # IndexError can be raised if an endpoint is missing.
        print()
        return False

class HasCmsisDapv2Interface(object):
    """! @brief CMSIS-DAPv2 match class to be used with usb.core.find"""

    def __init__(self, serial=None):
        """! @brief Create a new FindDap object with an optional serial number"""
        self._serial = serial

    def __call__(self, dev):
        """! @brief Return True if this is a CMSIS-DAPv2 device, False otherwise"""
        # Check if the device class is a valid one for CMSIS-DAP.
        if filter_device_by_class(dev.idVendor, dev.idProduct, dev.bDeviceClass):
            return False
        
        try:
            config = dev.get_active_configuration()
            cmsis_dap_interface = usb.util.find_descriptor(config, custom_match=_match_cmsis_dap_v2_interface)
        except usb.core.USBError as error:
            # Produce a more helpful error message if we get a permissions error on Linux.
            if error.errno == errno.EACCES and platform.system() == "Linux":
                msg = ("%s while trying to interrogate a USB device "
                   "(VID=%04x PID=%04x). This can probably be remedied with a udev rule. "
                   "See <https://github.com/mbedmicro/pyOCD/tree/master/udev> for help." %
                   (error, dev.idVendor, dev.idProduct))
                # If we recognize this device as one that should be CMSIS-DAP, we can raise
                # the level of the log message since it's almost certainly a permissions issue.
                if is_known_cmsis_dap_vid_pid(dev.idVendor, dev.idProduct):
                    LOG.warning(msg)
                else:
                    LOG.debug(msg)
            elif error.errno == errno.ENOENT:
                # This error happens on devices that don't have an interface description string.
                pass
            else:
                LOG.debug("Error accessing USB device (VID=%04x PID=%04x): %s",
                    dev.idVendor, dev.idProduct, error)
            return False
        except (IndexError, NotImplementedError) as error:
            LOG.debug("Error accessing USB device (VID=%04x PID=%04x): %s", dev.idVendor, dev.idProduct, error)
            return False

        if cmsis_dap_interface is None:
            return False
        
        # Check the class and subclass are vendor-specific.
        if (cmsis_dap_interface.bInterfaceClass != 0xff) or (cmsis_dap_interface.bInterfaceSubClass != 0):
            return False

        if self._serial is not None:
            if self._serial != dev.serial_number:
                return False
        return True

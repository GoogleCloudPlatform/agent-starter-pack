# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for pyu2f.hidtransport."""

import range
import unittest
from unittest import mock

from pyu2f import errors
from pyu2f import hidtransport
from pyu2f.tests.lib import util


def MakeKeyboard(path, usage):
  d = {}
  d['vendor_id'] = 1133  # Logitech
  d['product_id'] = 49948
  d['path'] = path
  d['usage'] = usage
  d['usage_page'] = 1
  return d


def MakeU2F(path):
  d = {}
  d['vendor_id'] = 4176
  d['product_id'] = 1031
  d['path'] = path
  d['usage'] = 1
  d['usage_page'] = 0xf1d0
  return d


def RPad(collection, to_size):
  while len(collection) < to_size:
    collection.append(0)
  return collection


class DiscoveryTest(unittest.TestCase):

  def testHidUsageSelector(self):
    u2f_device = {'usage_page': 0xf1d0, 'usage': 0x01}
    other_device = {'usage_page': 0x06, 'usage': 0x01}
    self.assertTrue(hidtransport.HidUsageSelector(u2f_device))
    self.assertFalse(hidtransport.HidUsageSelector(other_device))

  def testDiscoverLocalDevices(self):

    def FakeHidDevice(path):
      mock_hid_dev = mock.MagicMock()
      mock_hid_dev.GetInReportDataLength.return_value = 64
      mock_hid_dev.GetOutReportDataLength.return_value = 64
      mock_hid_dev.path = path
      return mock_hid_dev

    with mock.patch.object(hidtransport, 'hid') as hid_mock:
      # We mock out init so that it doesn't try to do the whole init
      # handshake with the device, which isn't what we're trying to test
      # here.
      with mock.patch.object(hidtransport.UsbHidTransport, 'InternalInit') as _:
        hid_mock.Enumerate.return_value = [
            MakeKeyboard('path1', 6), MakeKeyboard('path2', 2),
            MakeU2F('path3'), MakeU2F('path4')
        ]
        mock_hid_dev = mock.MagicMock()
        mock_hid_dev.GetInReportDataLength.return_value = 64
        mock_hid_dev.GetOutReportDataLength.return_value = 64
        hid_mock.Open.side_effect = FakeHidDevice

        # Force the iterator into a list
        devs = list(hidtransport.DiscoverLocalHIDU2FDevices())

        self.assertEqual(hid_mock.Enumerate.call_count, 1)
        self.assertEqual(hid_mock.Open.call_count, 2)
        self.assertEqual(len(devs), 2)

        self.assertEqual(devs[0].hid_device.path, 'path3')
        self.assertEqual(devs[1].hid_device.path, 'path4')


class TransportTest(unittest.TestCase):

  def testInit(self):
    fake_hid_dev = util.FakeHidDevice(bytearray([0x00, 0x00, 0x00, 0x01]))
    t = hidtransport.UsbHidTransport(fake_hid_dev)
    self.assertEqual(t.cid, bytearray([0x00, 0x00, 0x00, 0x01]))
    self.assertEqual(t.u2fhid_version, 0x01)

  def testPing(self):
    fake_hid_dev = util.FakeHidDevice(bytearray([0x00, 0x00, 0x00, 0x01]))
    t = hidtransport.UsbHidTransport(fake_hid_dev)

    reply = t.SendPing(b'1234')
    self.assertEqual(reply, b'1234')

  def testMsg(self):
    fake_hid_dev = util.FakeHidDevice(
        bytearray([0x00, 0x00, 0x00, 0x01]), bytearray([0x01, 0x90, 0x00]))
    t = hidtransport.UsbHidTransport(fake_hid_dev)

    reply = t.SendMsgBytes([0x00, 0x01, 0x00, 0x00])
    self.assertEqual(reply, bytearray([0x01, 0x90, 0x00]))

  def testMsgBusy(self):
    fake_hid_dev = util.FakeHidDevice(
        bytearray([0x00, 0x00, 0x00, 0x01]), bytearray([0x01, 0x90, 0x00]))
    t = hidtransport.UsbHidTransport(fake_hid_dev)

    # Each call will retry twice: the first attempt will fail after 2 retreis,
    # the second will succeed on the second retry.
    fake_hid_dev.SetChannelBusyCount(3)
    with mock.patch.object(hidtransport, 'time') as _:
      self.assertRaisesRegex(errors.HidError, '^Device Busy', t.SendMsgBytes,
                             [0x00, 0x01, 0x00, 0x00])

      reply = t.SendMsgBytes([0x00, 0x01, 0x00, 0x00])
      self.assertEqual(reply, bytearray([0x01, 0x90, 0x00]))

  def testFragmentedResponseMsg(self):
    body = bytearray([x % 256 for x in range(0, 1000)])
    fake_hid_dev = util.FakeHidDevice(bytearray([0x00, 0x00, 0x00, 0x01]), body)
    t = hidtransport.UsbHidTransport(fake_hid_dev)

    reply = t.SendMsgBytes([0x00, 0x01, 0x00, 0x00])
    # Confirm we properly reassemble the message
    self.assertEqual(reply, bytearray(x % 256 for x in range(0, 1000)))

  def testFragmentedSendApdu(self):
    body = bytearray(x % 256 for x in range(0, 1000))
    fake_hid_dev = util.FakeHidDevice(
        bytearray([0x00, 0x00, 0x00, 0x01]), [0x90, 0x00])
    t = hidtransport.UsbHidTransport(fake_hid_dev)

    reply = t.SendMsgBytes(body)
    self.assertEqual(reply, bytearray([0x90, 0x00]))
    # 1 init packet from creating transport, 18 packets to send
    # the fragmented message
    self.assertEqual(len(fake_hid_dev.received_packets), 18)

  def testInitPacketShape(self):
    packet = hidtransport.UsbHidTransport.InitPacket(
        64, bytearray(b'\x00\x00\x00\x01'), 0x83, 2, bytearray(b'\x01\x02'))

    self.assertEqual(packet.ToWireFormat(), RPad(
        [0, 0, 0, 1, 0x83, 0, 2, 1, 2], 64))

    copy = hidtransport.UsbHidTransport.InitPacket.FromWireFormat(
        64, packet.ToWireFormat())
    self.assertEqual(copy.cid, bytearray(b'\x00\x00\x00\x01'))
    self.assertEqual(copy.cmd, 0x83)
    self.assertEqual(copy.size, 2)
    self.assertEqual(copy.payload, bytearray(b'\x01\x02'))

  def testContPacketShape(self):
    packet = hidtransport.UsbHidTransport.ContPacket(
        64, bytearray(b'\x00\x00\x00\x01'), 5, bytearray(b'\x01\x02'))

    self.assertEqual(packet.ToWireFormat(), RPad([0, 0, 0, 1, 5, 1, 2], 64))

    copy = hidtransport.UsbHidTransport.ContPacket.FromWireFormat(
        64, packet.ToWireFormat())
    self.assertEqual(copy.cid, bytearray(b'\x00\x00\x00\x01'))
    self.assertEqual(copy.seq, 5)
    self.assertEqual(copy.payload, RPad(bytearray(b'\x01\x02'), 59))


if __name__ == '__main__':
  unittest.main()

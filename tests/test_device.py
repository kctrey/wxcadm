import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice


class TestDeviceList(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location = choice(self.webex.org.locations.webex_calling())

    def test_devicelist_org(self):
        device_list = self.webex.org.devices
        self.assertIsInstance(device_list, wxcadm.device.DeviceList)
        success = device_list.refresh()
        self.assertTrue(success)

    def test_devicelist_person(self):
        person = choice(self.webex.org.people.webex_calling())
        device_list = person.devices
        self.assertIsInstance(device_list, wxcadm.device.DeviceList)

    def test_devicelist_workspace(self):
        workspace = choice(self.webex.org.workspaces.webex_calling())
        device_list = workspace.devices
        self.assertIsInstance(device_list, wxcadm.device.DeviceList)

    def test_devicelist_status(self) -> None:
        with self.subTest("Online Devices"):
            online_devices = self.webex.org.devices.get_by_status('online')
            if len(online_devices) == 0:
                self.skipTest("No online devices found")
            for device in online_devices:
                self.assertIn(device.connection_status, ['connected', 'connected_with_issues'])
        with self.subTest("Offline Devices"):
            offline_devices = self.webex.org.devices.get_by_status('offline')
            if len(offline_devices) == 0:
                self.skipTest("No offline devices found")
            for device in offline_devices:
                self.assertIn(device.connection_status, ['disconnected', 'offline_deep_sleep', 'offline_expired'])
        with self.subTest("Unknown Devices"):
            unknown_devices = self.webex.org.devices.get_by_status('unknown')
            if len(unknown_devices) == 0:
                self.skipTest("No unknown devices found")
            for device in unknown_devices:
                self.assertIn(device.connection_status, ['unknown'])



class TestDevice(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location = choice(self.webex.org.locations.webex_calling())

    def test_device_members(self):
        device = choice(self.webex.org.devices.webex_calling())
        self.assertIsInstance(device, wxcadm.device.Device)
        members = device.members
        self.assertIsInstance(members, wxcadm.device.DeviceMemberList)

    def test_device_workspace_location_id(self):
        device = choice(self.webex.org.devices.webex_calling())
        self.assertIsNotNone(device.workspace_location_id)
        # The following test ensures that the .workspace_location_id can be decoded and matched to the WorkspaceLocation

class TestSupportedDevices(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)

    def test_supported_device_list(self):
        device_list = self.webex.org.devices.supported_devices
        self.assertIsInstance(device_list, wxcadm.device.SupportedDeviceList)
        with self.subTest("Devices in SupportedDeviceList"):
            self.assertGreater(len(device_list), 0)
        with self.subTest("SupportedDevice typing"):
            device = choice(device_list)
            self.assertIsInstance(device, wxcadm.device.SupportedDevice)

    def test_supported_device_get(self) -> None:
        # These test cases ensure that a SupportedDevice can be retrieved by name
        cisco_8851 = self.webex.org.supported_devices.get('8851')
        self.assertIsInstance(cisco_8851, wxcadm.SupportedDevice)
        self.assertEqual(cisco_8851.managed_by, 'CISCO')
        generic_phone = self.webex.org.supported_devices.get('generic ipphone')
        self.assertIsInstance(generic_phone, wxcadm.SupportedDevice)
        self.assertEqual(generic_phone.managed_by, 'CUSTOMER')


if __name__ == '__main__':
    unittest.main()
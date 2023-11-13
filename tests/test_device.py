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
        device = choice(self.webex.org.devices)
        self.assertIsInstance(device, wxcadm.device.Device)
        members = device.members
        self.assertIsInstance(members, wxcadm.device.DeviceMemberList)


if __name__ == '__main__':
    unittest.main()
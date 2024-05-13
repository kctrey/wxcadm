import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestSomething(unittest.TestCase):
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
        # Enable for test debugging
        # wxcadm.console_logging()

    def test_something(self):
        device_list = self.webex.org.devices
        self.assertIsInstance(device_list, wxcadm.device.DeviceList)
        success = device_list.refresh()
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
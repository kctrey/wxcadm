import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestPersonBargeInSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_person = choice(self.webex.org.people.webex_calling())
        # Enable for test debugging
        # wxcadm.console_logging()

    def test_barge_in_settings(self) -> None:
        barge_in_settings = self.random_person.barge_in
        self.assertIsInstance(barge_in_settings, wxcadm.workspace.BargeInSettings)

    def test_barge_in_settings_update(self) -> None:
        barge_in_settings: wxcadm.BargeInSettings = self.random_person.barge_in
        success = barge_in_settings.set_enabled(enabled=bool(not barge_in_settings.enabled))
        self.assertTrue(success)
        success = barge_in_settings.set_enabled(enabled=bool(barge_in_settings.enabled))
        self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
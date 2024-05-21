import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestECBN(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        # Enable for test debugging
        # wxcadm.console_logging()

    def test_person_ecbn(self):
        thing = choice(self.webex.org.people.webex_calling())
        ecbn = thing.ecbn
        self.assertIsInstance(ecbn, dict)
        prev_value = ecbn['selected']
        self.assertIsInstance(prev_value, str)
        with self.subTest("Location ECBN"):
            self.assertTrue(thing.set_ecbn('location'))
            self.assertTrue(thing.set_ecbn(prev_value))

    def test_workspace_ecbn(self):
        thing = choice(self.webex.org.workspaces.webex_calling())
        ecbn = thing.ecbn
        self.assertIsInstance(ecbn, dict)
        prev_value = ecbn['selected']
        self.assertIsInstance(prev_value, str)
        with self.subTest("Location ECBN"):
            self.assertTrue(thing.set_ecbn('location'))
            if prev_value.upper() != 'NONE':
                self.assertTrue(thing.set_ecbn(prev_value))

    def test_virtual_line_ecbn(self):
        thing = choice(self.webex.org.virtual_lines)
        ecbn = thing.ecbn
        self.assertIsInstance(ecbn, dict)
        prev_value = ecbn['selected']
        print(prev_value)
        self.assertIsInstance(prev_value, str)
        with self.subTest("Location ECBN"):
            self.assertTrue(thing.set_ecbn('location'))
            if prev_value.upper() != 'NONE':
                self.assertTrue(thing.set_ecbn(prev_value))


if __name__ == '__main__':
    unittest.main()
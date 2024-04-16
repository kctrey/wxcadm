import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING, Optional

from wxcadm.number import Number, NumberList


class TestNumbers(unittest.TestCase):
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

    def test_number_lists(self):
        with self.subTest('Org Numbers'):
            org_number_list = self.webex.org.numbers
            self.assertIsInstance(org_number_list, NumberList)
            self.assertIsInstance(org_number_list[0], Number)
            org_number_list = org_number_list.refresh()
            self.assertIsInstance(org_number_list, NumberList)
        with self.subTest('Location Numbers'):
            loc_number_list = self.random_location.numbers
            self.assertIsInstance(loc_number_list, NumberList)
            loc_number_list = loc_number_list.refresh()
            self.assertIsInstance(loc_number_list, NumberList)
        with self.subTest('Get Number by DN'):
            random_number: Optional[Number] = None
            while random_number is None or random_number.phone_number is None:
                random_number = choice(org_number_list)
            self.assertIsInstance(random_number, Number)
            self.assertIsInstance(random_number.phone_number, str)
            got_number = org_number_list.get(phone_number=random_number.phone_number)
            self.assertEqual(random_number, got_number)
        with self.subTest('Get Number by Extension'):
            random_number: Optional[Number] = None
            while random_number is None or random_number.extension is None:
                random_number = choice(org_number_list)
            self.assertIsInstance(random_number, Number)
            self.assertIsInstance(random_number.phone_number, str)
            got_number = org_number_list.get(extension=random_number.extension)
            self.assertEqual(random_number, got_number)



if __name__ == '__main__':
    unittest.main()
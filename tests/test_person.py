import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestPersonList(unittest.TestCase):
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

    def test_get_all(self) -> None:
        all_people = self.webex.org.people.all()
        get_people = self.webex.org.people.get()
        self.assertCountEqual(all_people, get_people)
        self.assertTrue(all_people, self.webex.org.people)

    def test_get_with_filters(self) -> None:
        # Location filter
        random_location = choice(self.webex.org.locations.webex_calling())
        location_people = self.webex.org.people.get(location=random_location)
        self.assertIsInstance(location_people, wxcadm.PersonList)
        # Name filter
        random_person: wxcadm.Person = choice(self.webex.org.people.all())
        get_name: wxcadm.Person = self.webex.org.people.get(name=random_person.display_name)
        self.assertEqual(random_person.id, get_name.id)
        self.assertEqual(random_person.display_name, get_name.display_name)
        # Email filter
        get_email: wxcadm.Person = self.webex.org.people.get(email=random_person.email)
        self.assertEqual(random_person.id, get_email.id)
        self.assertEqual(random_person.display_name, get_email.display_name)
        # ID filter
        get_person: wxcadm.Person = self.webex.org.people.get(id=random_person.id)
        self.assertEqual(random_person.id, get_person.id)
        self.assertEqual(random_person.display_name, get_person.display_name)





if __name__ == '__main__':
    unittest.main()
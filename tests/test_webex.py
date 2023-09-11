import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice


class TestWebex(unittest.TestCase):
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

    def test_bad_token(self):
        with self.assertRaises(wxcadm.TokenError):
            wxcadm.Webex("Bad Token Value")

    def test_org_count(self):
        org_count = len(self.webex.orgs)
        self.assertGreater(org_count, 0)

    def test_location_list(self):
        self.assertIsInstance(self.webex.org.locations, wxcadm.location.LocationList)
        self.assertIsInstance(self.random_location, wxcadm.location.Location)

    def test_location_hunt_groups(self):
        location = self.random_location
        self.assertIsInstance(location.hunt_groups, wxcadm.hunt_group.HuntGroupList)
        if location.hunt_groups:
            self.assertIsInstance(choice(location.hunt_groups), wxcadm.hunt_group.HuntGroup)

    # def test_location_create_update_delete(self):
    #     self.webex.org.locations: wxcadm.location.LocationList
    #     new_loc
    #     print(new_loc)
    #     self.assertIsInstance(new_loc, dict)

    def test_location_call_queues(self):
        location = self.random_location
        self.assertIsInstance(location.call_queues, wxcadm.call_queue.CallQueueList)
        if location.call_queues:
            self.assertIsInstance(choice(location.call_queues), wxcadm.call_queue.CallQueue)

if __name__ == '__main__':
    unittest.main()

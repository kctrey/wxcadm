import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
import queue
import time


class TestXSI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        cls.token_type = os.getenv("WEBEX_TOKEN_TYPE")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        endpoints = self.webex.org.get_xsi_endpoints()
        self.assertIsInstance(endpoints, dict)
        if endpoints is not None:
            self.xsi_capable: bool = True
        else:
            self.xsi_capable = False

    def test_person_profile(self):
        if self.xsi_capable is False:
            self.skipTest("Not an XSI Token")
        with self.subTest("My Profile"):
            if self.token_type.upper() == 'SERVICE':
                self.skipTest("Service Token cannot access own XSI Profile")
            me = self.webex.me
            me.start_xsi()
            my_profile = me.xsi.profile
            self.assertIsInstance(my_profile, dict)
        with self.subTest('Random Person Profile'):
            person = choice(self.webex.org.people.webex_calling())
            person.start_xsi()
            profile = person.xsi.profile
            self.assertIsInstance(profile, dict)

    def test_enterprise_events(self):
        if self.xsi_capable is False:
            self.skipTest("Not an XSI Token")
        events = wxcadm.XSIEvents(self.webex.org)
        self.assertIsInstance(events, wxcadm.xsi.XSIEvents)
        events_queue = queue.Queue()
        channel = events.open_channel(events_queue)
        self.assertIsInstance(channel, wxcadm.xsi.XSIEventsChannelSet)
        time.sleep(5)
        subscription = channel.subscribe("Advanced Call")
        if subscription is not False:
            self.assertIsInstance(subscription, wxcadm.xsi.XSIEventsSubscription)
            self.assertEqual(subscription.active, True)
            if subscription.active is True:
                channel.unsubscribe("all")
                message = events_queue.get()
                self.assertIsInstance(message, dict)
        channel.close()
        self.assertEqual(len(channel.subscriptions), 0)
        self.assertEqual(len(channel.active_channels), 0)

    def test_person_events(self):
        if self.xsi_capable is False:
            self.skipTest("Not an XSI Token")
        events = wxcadm.XSIEvents(self.webex.org)
        self.assertIsInstance(events, wxcadm.xsi.XSIEvents)
        events_queue = queue.Queue()
        channel = events.open_channel(events_queue)
        self.assertIsInstance(channel, wxcadm.xsi.XSIEventsChannelSet)
        time.sleep(5)
        subscription = channel.subscribe("Advanced Call", person=choice(self.webex.org.people.webex_calling()))
        self.assertIsInstance(subscription, wxcadm.xsi.XSIEventsSubscription)
        self.assertEqual(subscription.active, True)
        if subscription.active is True:
            channel.unsubscribe("all")
            message = events_queue.get()
            self.assertIsInstance(message, dict)
        channel.close()
        self.assertEqual(len(channel.subscriptions), 0)
        self.assertEqual(len(channel.active_channels), 0)

    def test_directory_all(self):
        if self.xsi_capable is False:
            self.skipTest("Not an XSI Token")
        if self.token_type.upper() == 'SERVICE':
            me = choice(self.webex.org.people.webex_calling())
            self.assertIsInstance(me, wxcadm.person.Person)
        else:
            me = self.webex.me
            self.assertIsInstance(me, wxcadm.person.Me)
        me.start_xsi()
        with self.subTest('Full Directory'):
            directory = me.xsi.directory()
            self.assertGreaterEqual(len(directory), 1)
        with self.subTest("Group Directory"):
            directory = me.xsi.directory('Group')
            self.assertGreaterEqual(len(directory), 1)
        with self.subTest("Name Search"):
            person = choice(self.webex.org.people.webex_calling())
            directory = me.xsi.directory(first_name=person.first_name)
            self.assertGreaterEqual(len(directory), 1)
        with self.subTest("Name Search - Case Insensitive"):
            person = choice(self.webex.org.people.webex_calling())
            search_string = f"{person.first_name.lower()}/i"
            directory = me.xsi.directory(first_name=search_string)
            self.assertGreaterEqual(len(directory), 1)
        with self.subTest("Any Match Search"):
            person1 = choice(self.webex.org.people.webex_calling())
            person2 = choice(self.webex.org.people.webex_calling())
            directory = me.xsi.directory(first_name=person1.first_name, last_name=person2.last_name, any_match=True)
            self.assertGreaterEqual(len(directory), 2)
        with self.subTest("Personal Directory"):
            directory = me.xsi.directory("personal")
            self.assertIsInstance(directory, list)


if __name__ == '__main__':
    unittest.main()

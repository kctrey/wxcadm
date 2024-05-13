import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestRecordings(unittest.TestCase):
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

    def test_recording_list(self):
        with self.subTest("Org Recordings"):
            org_recordings = self.webex.org.get_recordings()
            self.assertIsInstance(org_recordings, wxcadm.RecordingList)
            if len(org_recordings) > 0:
                random_recording = choice(org_recordings)
                self.assertIsInstance(random_recording, wxcadm.Recording)
                del random_recording
            del org_recordings
        with self.subTest("Person Recordings"):
            person = choice(self.webex.org.people.webex_calling())
            person_recordings = self.webex.org.get_recordings(owner=person)
            self.assertIsInstance(person_recordings, wxcadm.RecordingList)
            if len(person_recordings) > 0:
                random_recording = choice(person_recordings)
                self.assertIsInstance(random_recording, wxcadm.Recording)
                del random_recording
            del person
            del person_recordings
        with self.subTest("Location Recordings"):
            location = choice(self.webex.org.locations.webex_calling())
            location_recordings = self.webex.org.get_recordings(location=location)
            self.assertIsInstance(location_recordings, wxcadm.RecordingList)
            if len(location_recordings) > 0:
                random_recording = choice(location_recordings)
                self.assertIsInstance(random_recording, wxcadm.Recording)
                del random_recording
            del location_recordings
            del location

    def test_recording_data(self) -> None:
        org_recordings = self.webex.org.get_recordings()
        if len(org_recordings) == 0:
            self.skipTest("No Recordings")
        recording = choice(org_recordings)
        self.assertIsInstance(recording.topic, str)
        self.assertIsInstance(recording.created, str)
        self.assertIsInstance(recording.details, dict)
        url = recording.url
        self.assertIsInstance(url, str)
        self.assertGreater(len(url), 10)


if __name__ == '__main__':
    unittest.main()
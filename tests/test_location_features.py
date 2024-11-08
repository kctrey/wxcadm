import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from wxcadm.location import *
    from wxcadm.location_features import *


class TestLocationECBN(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location: Location = choice(self.webex.org.locations.webex_calling())

    def test_location_ecbn_get(self) -> None:
        current_ecbn = self.random_location.ecbn
        self.assertIsInstance(current_ecbn, dict)
        self.assertIn(current_ecbn['selected'], ['LOCATION_NUMBER', 'LOCATION_MEMBER_NUMBER'], "Unknown selected value")


class TestVoicemailGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location: Location = choice(self.webex.org.locations.webex_calling())

    def test_org_voicemail_group_list(self) -> None:
        self.assertIsInstance(self.webex.org.voicemail_groups, wxcadm.VoicemailGroupList)

    def test_create_update_delete_vm_group(self) -> None:
        before_count = len(self.webex.org.voicemail_groups)
        with self.subTest('Add Voicemail Group'):
            new_group = self.webex.org.voicemail_groups.create(
                location=self.random_location,
                name='wxcadm Test',
                extension='928807',
                passcode='288547'
            )
            self.assertIsInstance(new_group, wxcadm.VoicemailGroup)
            self.assertEqual(len(self.webex.org.voicemail_groups.refresh()), before_count + 1)

        with self.subTest('Update VM Group Email'):
            new_group.enable_email_copy('wxcadmautotest@wxcadm.com')
            self.assertTrue(new_group.email_copy_of_message['enabled'])
            self.assertEqual(new_group.email_copy_of_message['emailId'], 'wxcadmautotest@wxcadm.com')
            new_group.update(first_name='Test')
            self.assertEqual(new_group.first_name, 'Test')

        with self.subTest('Delete VM Group'):
            new_group.delete()
            self.assertEqual(len(self.webex.org.voicemail_groups.refresh()), before_count)


class TestOutgoingDigitPatterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location: Location = choice(self.webex.org.locations.webex_calling())

    def test_outgoing_permission_digit_pattern_list(self) -> None:
        self.assertIsInstance(self.random_location.outgoing_permission_digit_patterns,
                              wxcadm.OutgoingPermissionDigitPatternList)

    def test_add_update_remove_pattern(self) -> None:
        # To confirm we are adding and deleting, get the len of the current list for the location
        before_len = len(self.random_location.outgoing_permission_digit_patterns.patterns)
        with self.subTest('Add digit pattern'):
            new_pattern: OutgoingPermissionDigitPattern = \
                self.random_location.outgoing_permission_digit_patterns.create(
                    name='wxcadm Test',
                    pattern='012XXX',
                    action='ALLOW'
                )
            self.assertIsInstance(new_pattern, wxcadm.OutgoingPermissionDigitPattern)
            self.assertEqual(
                len(self.random_location.outgoing_permission_digit_patterns.patterns),
                before_len + 1
            )
        with self.subTest('Update pattern attributes'):
            # Set each value individually
            new_pattern.update(name='wxcadm Change Test')
            self.assertEqual(new_pattern.name, 'wxcadm Change Test')
            new_pattern.update(pattern='013XXX')
            self.assertEqual(new_pattern.pattern, '013XXX')
            new_pattern.update(action='BLOCK')
            self.assertEqual(new_pattern.action, 'BLOCK')
            new_pattern.update(transfer_enabled=True)
            self.assertEqual(new_pattern.transfer_enabled, True)
            # Set all values at one time
            new_pattern.update(name='wxcadm Final Test', action='ALLOW', pattern='014XXX', transfer_enabled=False)
        with self.subTest('Delete pattern'):
            success = new_pattern.delete()
            self.assertEqual(success, True)
            self.assertEqual(
                len(self.random_location.outgoing_permission_digit_patterns.refresh().patterns),
                before_len
            )


class TestLocationFloors(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()
        cls.access_token = os.getenv("WEBEX_ACCESS_TOKEN")
        if not cls.access_token:
            print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
            exit(1)

    def setUp(self) -> None:
        self.webex = wxcadm.Webex(self.access_token)
        self.random_location: Location = choice(self.webex.org.locations.webex_calling())

    def test_floor_list(self) -> None:
        self.assertIsInstance(self.random_location.floors, wxcadm.LocationFloorList)
        if len(self.random_location.floors) == 0:
            self.skipTest("No floors at location")
        self.assertIsInstance(self.random_location.floors[0], wxcadm.LocationFloor)
        self.assertIsInstance(self.random_location.floors[0].floor_number, int)


if __name__ == '__main__':
    unittest.main()
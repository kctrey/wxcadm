import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from wxcadm.location import *
    from wxcadm.location_features import *


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


if __name__ == '__main__':
    unittest.main()
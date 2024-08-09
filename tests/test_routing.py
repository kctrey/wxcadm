import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestTranslationPatterns(unittest.TestCase):
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

    def test_org_tp_instances(self) -> None:
        org_tp = self.webex.org.translation_patterns
        self.assertIsInstance(org_tp, wxcadm.TranslationPatternList)
        if len(org_tp) > 0:
            self.assertIsInstance(org_tp[0], wxcadm.TranslationPattern)

    def test_org_tp_crud(self) -> None:
        with self.subTest("Create"):
            new_pattern = self.webex.org.translation_patterns.create(
                name='WXCADM Test',
                match_pattern='1234567890123456789X',
                replacement_pattern='8443876962'
            )
            self.assertIsInstance(new_pattern, wxcadm.TranslationPattern)
        with self.subTest("Retrieve"):
            self.webex.org.translation_patterns.refresh()
            pattern = self.webex.org.translation_patterns.get(id=new_pattern.id)
            self.assertIsInstance(pattern, wxcadm.TranslationPattern)
        with self.subTest("Update Name"):
            success = pattern.update(name='WXCADM Updated Test')
            self.assertTrue(success)
        with self.subTest("Update Match Pattern"):
            success = pattern.update(match_pattern='987654321098765432X')
            self.assertTrue(success)
        with self.subTest("Update Replacement Pattern"):
            success = pattern.update(replacement_pattern='18553876962')
            self.assertTrue(success)
        with self.subTest("Delete"):
            success = pattern.delete()
            self.assertTrue(success)

    def test_loc_tp_crud(self) -> None:
        with self.subTest("Create"):
            new_pattern = self.webex.org.translation_patterns.create(
                name='WXCADM Loc Test',
                match_pattern='1234567890123456789X',
                replacement_pattern='8443876962',
                location=self.random_location
            )
            self.assertIsInstance(new_pattern, wxcadm.TranslationPattern)
        with self.subTest("Retrieve"):
            self.webex.org.translation_patterns.refresh()
            pattern = self.webex.org.translation_patterns.get(id=new_pattern.id)
            self.assertIsInstance(pattern, wxcadm.TranslationPattern)
        with self.subTest("Update Name"):
            success = pattern.update(name='WXCADM Updated Loc Test')
            self.assertTrue(success)
        with self.subTest("Update Match Pattern"):
            success = pattern.update(match_pattern='987654321098765432X')
            self.assertTrue(success)
        with self.subTest("Update Replacement Pattern"):
            success = pattern.update(replacement_pattern='18553876962')
            self.assertTrue(success)
        with self.subTest("Delete"):
            success = pattern.delete()
            self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
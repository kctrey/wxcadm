import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass


class TestWebexLicenseClasses(unittest.TestCase):
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

    def test_license_list(self):
        license_list = self.webex.org.licenses
        self.assertIsInstance(license_list, wxcadm.WebexLicenseList)
        self.assertIsInstance(license_list[0], wxcadm.WebexLicense)
        calling_licenses = license_list.webex_calling()
        self.assertIsInstance(calling_licenses, list)
        self.assertGreater(len(calling_licenses), 0)
        self.assertIsInstance(calling_licenses[0], wxcadm.WebexLicense)
        chosen_license = choice(calling_licenses)
        self.assertIsInstance(chosen_license, wxcadm.WebexLicense)
        retrieved_license = license_list.get(id=chosen_license.id)
        self.assertIsInstance(retrieved_license, wxcadm.WebexLicense)
        self.assertEqual(retrieved_license.id, chosen_license.id)
        retrieved_license = license_list.get(name=chosen_license.name)
        self.assertIsInstance(retrieved_license, wxcadm.WebexLicense)
        self.assertEqual(retrieved_license.id, chosen_license.id)
        if chosen_license.subscription is not None:
            retrieved_license = license_list.get(subscription=chosen_license.subscription)
            self.assertIsInstance(retrieved_license, list)
            self.assertIsInstance(retrieved_license[0], wxcadm.WebexLicense)
            self.assertEqual(retrieved_license[0].subscription, chosen_license.subscription)
        license_list.refresh()
        self.assertIsInstance(license_list, wxcadm.WebexLicenseList)
        self.assertIsInstance(license_list[0], wxcadm.WebexLicense)

    def test_assignable_licenses(self):
        license_list = self.webex.org.licenses
        self.assertIsInstance(license_list, wxcadm.WebexLicenseList)
        self.assertIsInstance(license_list[0], wxcadm.WebexLicense)
        with self.subTest("Professional licenses"):
            pro_license = license_list.get_assignable_license('professional')
            self.assertIsInstance(pro_license, wxcadm.WebexLicense)
        with self.subTest("Workspace licenses"):
            ws_license = license_list.get_assignable_license('workspace')
            self.assertIsInstance(ws_license, wxcadm.WebexLicense)
        with self.subTest("Hotdesk licenses"):
            hd_license = license_list.get_assignable_license('hotdesk')
            self.assertIsInstance(hd_license, wxcadm.WebexLicense)


if __name__ == '__main__':
    unittest.main()
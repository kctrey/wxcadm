import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice, randint


class TestReportsDataPull(unittest.TestCase):
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

    def test_report_list(self) -> None:
        report_list = self.webex.org.reports
        self.assertIsInstance(report_list, wxcadm.reports.ReportList)
        if len(report_list) > 0:
            self.assertIsInstance(report_list[0], wxcadm.reports.Report)

if __name__ == '__main__':
    unittest.main()

import unittest
import os
from dotenv import load_dotenv
import wxcadm
from random import choice


class TestJobsList(unittest.TestCase):
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

    def test_jobs_list(self):
        jobs = self.webex.org.number_management_jobs
        self.assertIsInstance(jobs, wxcadm.jobs.NumberManagementJobList)

    def test_job_details(self):
        jobs = self.webex.org.number_management_jobs
        with self.subTest("NumberManagementJob instance"):
            job = choice(jobs)
            self.assertIsInstance(job, wxcadm.jobs.NumberManagementJob)

        with self.subTest("Job Details"):
            details = choice(jobs).details
            self.assertIsInstance(details, dict)

        with self.subTest("Job Completed"):
            self.assertIsInstance(choice(jobs).completed, bool)

        with self.subTest("Job Success"):
            self.assertIsInstance(choice(jobs).success, bool)


if __name__ == '__main__':
    unittest.main()

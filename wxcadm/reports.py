from __future__ import annotations
from typing import Optional
import requests
from .common import *
from wxcadm import log
from datetime import datetime, timedelta


class Reports:
    """ The Reports class provides an interface to all reports available via the Webex API """
    def __init__(self, org: Org):
        self.org = org
        self._templates: Optional[list] = None
        self.created_reports: list = []
        """ A list of IDs for all reports created during this session """

    @property
    def templates(self):
        """ The Report Templates available

        Returns:
            dict: A dict of Report Templates

        """
        log.info('Getting reports templates')
        self._templates = webex_api_call('get', '/v1/report/templates')
        return self._templates

    def list_reports(self):
        """ List the reports available to the authorized user via the Webex API

        .. note::
            Webex isolates reports created via the API from reports created within Control Hub. The reports listed
            by this method will show only the reports created using the API.

        Returns:
            list[dict]: A list of all reports as dicts

        """
        log.info('Getting list of reports')
        my_reports = webex_api_call('get', '/v1/reports')
        return my_reports

    def create_report(self, template_id: int,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      site_list: Optional[list] = None):
        """ Create a new report

        The arguments vary based on the Template used. By looking at the `templates` list, you can see the requirements
        in the `validations` key.

        Args:
            template_id (int): The Template ID to use for the report
            start_date (str): The first date to include in the report
            end_date (str): The last date to include in the report
            site_list (list[str], optional): A list of Webex meeting sites

        Returns:
            str: The Report ID that was created

        """
        log.info(f'Creating report with Template ID: {template_id}')
        log.debug(f'\tStart: {start_date}, End: {end_date}')
        log.debug(f'\tSite List: {site_list}')
        payload = {}
        payload['templateId'] = template_id
        if start_date is not None:
            payload['startDate'] = start_date
        if end_date is not None:
            payload['endDate'] = end_date
        if site_list is not None:
            payload['siteList'] = site_list

        response = webex_api_call('post', '/v1/reports', payload=payload)
        log.debug(f'API response: {response}')
        report_id = response['items']['Id']
        log.info(f'Report ID: {report_id}')
        self.created_reports.append(report_id)
        return report_id

    @staticmethod
    def report_status(report_id: str):
        """ The text status of the provided report_id

        Args:
            report_id (str): The Report ID

        Returns:
            str: The status of the report

        """
        log.info(f"Getting report status for Report ID {report_id}")
        response = webex_api_call('get', f'/v1/reports/{report_id}')
        status = response[0]['status']
        return status

    def get_report_lines(self, report_id: str):
        """ Download and return the lines from a report

        This method returns the full report in a list, with each line as an entry.

        Args:
            report_id (str): The Report ID

        Returns:
            list: The report lines

        """
        log.info(f'Getting report with ID {report_id}')
        response = webex_api_call('get', f'/v1/reports/{report_id}')
        url = response[0]['downloadURL']
        log.debug(f'\tDownload URL: {url}')
        r = requests.get(url, headers=self.org._headers)
        if r.ok:
            report_lines = r.text.replace('\xef\xbb\xbf', '')
            return report_lines.split('\n')
        else:
            return False

    def cdr_report(self, start: Optional[str] = None, end: Optional[str] = None, days: Optional[int] = None):
        """ Create a CDR report

        This method serves as a shortcut to :py:meth:`create_report()` for a Calling Detailed Call History report. It
        finds the correct template and creates the report using the given start and end dates, or the ``days``
        argument can be provided to report the last X days.

        Args:
            start (str, optional): The first date to include in the report (YYYY-MM-DD)
            end (str, optional): The last date to include in the report (YYYY-MM-DD)
            days (int, optional): The number of days to report on, ending on yesterday's date

        Returns:
            str: The Report ID

        """
        if start is None and days is None:
            raise ValueError("You must provide either a start date or the number of days")
        if start is not None and days is not None:
            raise ValueError("You must not specify a start date and number of days")
        if days is not None:
            yesterday = datetime.now() - timedelta(1)
            end = datetime.strftime(yesterday, "%Y-%m-%d")
            start_date = yesterday - timedelta(days)
            start = datetime.strftime(start_date, "%Y-%m-%d")

        # Find the CDR Report Template
        for template in self.templates:
            if template['title'] == 'Calling Detailed Call History':
                cdr_template = template['Id']
                break

        report_id = self.create_report(template_id=cdr_template,
                                       start_date=start,
                                       end_date=end)
        return report_id

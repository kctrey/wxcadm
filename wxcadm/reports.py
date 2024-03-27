from __future__ import annotations
from typing import Optional
import requests
from .common import *
import wxcadm
from wxcadm import log
from datetime import datetime, timedelta
from io import BytesIO
from zipfile import ZipFile
from collections import UserList


class Report:
    def __init__(self, org: wxcadm.Org, id: Optional[str] = None, config: Optional[dict] = None):
        self.org: wxcadm.Org = org
        if id is None and config is None:
            raise ValueError('id or config is required for Report init')
        if id is not None:
            log.debug(f'Getting Report details: {id}')
            config = webex_api_call('get', f'v1/reports/{id}')[0]
            log.debug(config)
        self.id: str = config.get('Id', None)
        """ The Report ID """
        self.title: str = config.get('title', '')
        """ The title of the Report """
        self.service: str = config.get('service', '')
        """ The service to which the Report belongs """
        self.start_date: str = config.get('startDate', '')
        """ The Report period start date """
        self.end_date: str = config.get('endDate', '')
        """ The Report period end date """
        self.site_list: str = config.get('siteList', '')
        """ For Webex Meetings reports, the list of Sites """
        self.created: str = config.get('created', '')
        """ The date the report was created """
        self.created_by: str = config.get('createdBy', '')
        """ The person who created the Report """
        self.scheduled_from: str = config.get('scheduledFrom', '')
        """ Whether the Report was scheduled from Control Hub or API """
        self._status: str = config.get('status', 'unknown')
        self.download_url: str = config.get('downloadURL', None)

    def refresh(self):
        """ Refresh the Report

        .. note::
        There is no need to call refresh() before calling status(), because a full refresh will be done when the status
        is updated.

        Returns:
            Report: An updated :class:`Report` instance

        """
        log.debug(f'Refreshing Report {self.id}')
        config = webex_api_call('get', f'v1/reports/{self.id}')[0]
        log.debug(config)
        self.id = config.get('Id', None)
        self.title = config.get('title', '')
        self.service = config.get('service', '')
        self.start_date = config.get('startDate', '')
        self.end_date = config.get('endDate', '')
        self.site_list = config.get('siteList', '')
        self.created = config.get('created', '')
        self.created_by = config.get('createdBy', '')
        self.scheduled_from = config.get('scheduledFrom', '')
        self._status = config.get('status', 'unknown')
        self.download_url = config.get('downloadURL', None)

    @property
    def status(self) -> str:
        """ The status of the report """
        self.refresh()
        return self._status

    def get_report_lines(self) -> list:
        log.info(f'Getting Report lines: {self.id}')
        self.refresh()
        log.debug(f'Download URL: {self.download_url}')
        r = requests.get(self.download_url, headers=self.org._headers)
        log.debug(f'Response Headers: {r.headers}')
        if r.ok:
            if r.headers.get('content-type', '') in ['application/zip', 'application/octet-stream']:
                report_lines = []
                myzip = ZipFile(BytesIO(r.content))
                filename = myzip.namelist()[0]
                for line in myzip.open(filename).readlines():
                    report_lines.append(line.decode('utf-8'))
                return report_lines
            else:
                report_lines = r.text.replace('\xef\xbb\xbf', '')
                return report_lines.split('\n')
        else:
            return []


class ReportTemplate:
    def __init__(self, config: dict):
        self.id: str = config.get('Id', None)
        self.title: str = config.get('title', '')
        self.service: str = config.get('service', '')
        self.max_days: int = config.get('maxDays', 0)
        self.identifier: str = config.get('identifier', '')
        self.validations: list = config.get('validations', [])


class ReportList(UserList):
    """ The Reports class provides an interface to all reports available via the Webex API """
    def __init__(self, org: wxcadm.Org):
        log.info("Initializing empty DECTNetworkList")
        super().__init__()
        self.org = org
        self.data = self._get_data()
        self._templates: Optional[list] = None

    def _get_data(self) -> list:
        data = []
        response = webex_api_call('get', 'v1/reports')
        for item in response:
            data.append(Report(self.org, config=item))
        return data

    @property
    def templates(self):
        """ The Report Templates available

        Returns:
            list: A list of :class:`ReportTemplate` instances

        """
        log.info('Getting reports templates')
        if self._templates is None:
            self._templates = []
            for item in webex_api_call('get', '/v1/report/templates'):
                self._templates.append(ReportTemplate(item))
        return self._templates

    def get_template(self, id: int) -> Optional[ReportTemplate]:
        """ Get a :class:`ReportTemplate` by the Template ID

        Args:
            id (str): The Template ID to find. Normally these look like ints, but Webex expects str

        Returns:
            ReportTemplate: The :class:`ReportTemplate` matching the give ID. None is returned if no match is found.

        """
        for templ in self.templates:
            if templ.id == id:
                return templ
        return None

    def list_reports(self):
        """ List the reports available to the authorized user via the Webex API

        .. note::
            Webex isolates reports created via the API from reports created within Control Hub. The reports listed
            by this method will show only the reports created using the API.

        Returns:
            list[dict]: A list of all reports as dicts

        """
        return self.data

    def create_report(self, template: ReportTemplate,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      site_list: Optional[list] = None):
        """ Create a new report

        The arguments vary based on the Template used. By looking at the `templates` list, you can see the requirements
        in the `validations` key.

        Args:
            template (ReportTemplate): The :class:`ReportTemplate` to use for the report
            start_date (str): The first date to include in the report
            end_date (str): The last date to include in the report
            site_list (list[str], optional): A list of Webex meeting sites

        Returns:
            str: The Report ID that was created

        """
        log.info(f'Creating report with Template ID: {template.id}')
        log.debug(f'\tStart: {start_date}, End: {end_date}')
        log.debug(f'\tSite List: {site_list}')
        payload = {'templateId': template.id}
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
        this_report = Report(self.org, id=report_id)
        self.data.append(Report)
        return this_report

    def delete_report(self, report_id: str) -> bool:
        """ Delete a specified report

        Args:
            report_id (str): The ID of the report to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        log.info(f'Deleting report with ID {report_id}')
        try:
            response = webex_api_call('delete', f'/v1/reports/{report_id}')
            if response.status_code == 204:
                log.info(f'Successfully deleted report with ID: {report_id}')
                return True
            else:
                log.error(f'Failed to delete report with ID: {report_id}, Status Code: {response.status_code}')
                return False
        except Exception as e:
            log.error(f'Exception occurred while deleting report: {e}')
            return False

    def report_status(self, report_id: str):
        """ The text status of the provided report_id

        Args:
            report_id (str): The Report ID

        Returns:
            str: The status of the report

        """
        for item in self.data:
            if item.id == report_id:
                return item.status
        return None

    def get_report_lines(self, report_id: str):
        """ Download and return the lines from a report

        This method returns the full report in a list, with each line as an entry.

        Args:
            report_id (str): The Report ID

        Returns:
            list: The report lines

        """
        for report in self.data:
            if report.id == report_id:
                return report.get_report_lines()
        return None

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
            if template.title == 'Calling Detailed Call History':
                cdr_template = template
                break

        new_report = self.create_report(template=cdr_template,
                                       start_date=start,
                                       end_date=end)
        return new_report

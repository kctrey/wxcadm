from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, timezone

import wxcadm.org
from wxcadm import log
from .common import *


class Calls:
    def __init__(self, parent: Org):
        self.parent = parent

    def cdr(self, start: Optional[str] = None, end: Optional[str] = None, days: Optional[int] = None,
            hours: Optional[int] = None):
        """ Get a list of Call Detail Records

        Args:
            start (str, optional): The first date to include (YYYY-MM-DD)
            end (str, optional): The last date to include (YYYY-MM-DD)
            days (int, optional): The number of days to include, including today. Currently only 1 is supported by the
                API.
            hours (int, optional): The number of hours to include

        Returns:
            str: The Report ID

        .. note::
            This method requires a token with the ``spark-admin:calling_cdr_read`` scope. Additionally, the user
            must have the "Webex Calling Detailed Call History API access" option enabled in Control Hub, under the
            Administrator Roles.

        """
        log.debug('Calls.cdr() started')
        if start is None and days is None and hours is None:
            log.warning("No arguments provided")
            raise ValueError("You must provide either a start date, the number of day or the number of hours")
        if start is not None and (days is not None or hours is not None):
            log.warning("Start date and days/hours was passed. Invalid")
            raise ValueError("You must not specify a start date and number of days or hours")
        # Get the current UTC time to use if we need it
        timenow = datetime.now(timezone.utc)
        # Use "5 minutes ago" as the end time if we weren't given an end

        if end is None:
            endtime = timenow - timedelta(minutes=5)
            end = datetime.strftime(endtime, '%Y-%m-%dT%H:%M:%S.000Z')
            log.debug(f"No end provided. Using {end} as end time.")

        if hours is not None:
            # Fix for time sync issue with API. The API is very picky about the start time not being even a second
            # longer than 48 hours
            if hours == 48:
                starttime = timenow - timedelta(hours=hours) + timedelta(minutes=1)
            else:
                starttime = timenow - timedelta(hours=hours)
            start = datetime.strftime(starttime, '%Y-%m-%dT%H:%M:%S.000Z')
        elif days is not None:
            # Fix for time sync issue with API. The API is very picky about the start time not being even a second
            # longer than 48 hours
            if days == 2:
                starttime = timenow - timedelta(days=days) + timedelta(minutes=1)
            else:
                starttime = timenow - timedelta(days=days)
            start = datetime.strftime(starttime, '%Y-%m-%dT%H:%M:%S.000Z')
        elif start is not None:
            start = start

        log.debug(f'Setting start time to {start}')
        payload = {'startTime': start, 'endTime': end}
        response = webex_api_call('get', '/v1/cdr_feed', params=payload, domain='https://analytics.webexapis.com')
        return response

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

import wxcadm.location
from wxcadm import log
from .common import *


@dataclass
class PagingGroup:
    parent: wxcadm.Location
    id: str
    name: str
    spark_id: str = field(init=False, repr=False)
    config: dict = field(init=False, repr=False)

    def __post_init__(self):
        self.spark_id = decode_spark_id(self.id)
        self.refresh_config()

    def refresh_config(self):
        """ Pull a fresh copy of the Paging Group config from Webex, in case it has changed. """
        api_resp: dict = webex_api_call("get", f"v1/telephony/config/locations/{self.parent.id}/paging/{self.id}")
        self.config = api_resp


@dataclass
class LocationSchedule:
    """ The class for Location Schedules within a :class:`Location`

    When the instance is initialized, it will fetch the configuration from Webex.

    .. note::
            LocationSchedule instances are normally not instantiated manually and are done automatically with the
            :attr:`Location.schedules` property.

    Args:
        parent (Location): The `Location` instance to which the LocationSchedule is assigned.
        id (str): The Webex ID of the LocationSchedule
        name (str): The name of the LocationSchedule
        type (str): The type of LocationSchedule, either 'businessHours' or 'Holidays'

    """
    parent: wxcadm.Location
    """ The `Location` instance to which the LocationSchedule is assigned """
    id: str
    """ The Webex ID of the LocationSchedule """
    name: str
    """ The name of the LocationSchedule """
    type: str
    """ The type of LocationSchedule, either 'businessHours' or 'Holidays' """
    config: dict = field(init=False, repr=False)
    """ The configuration returned by Webex """

    def __post_init__(self):
        self.refresh_config()

    def refresh_config(self):
        """ Pull a fresh copy of the schedule configuration from Webex, in case it has changed. """
        api_resp = webex_api_call("get", f"v1/telephony/config/locations/{self.parent.id}/schedules/"
                                         f"{self.type}/{self.id}")
        self.config = api_resp

    def add_holiday(self, name: str, date: str, recur: bool = False, recurrence: Optional[dict] = None):
        """ Add a new all-day event to a Holidays schedule

        This method provides a quicker way to add an all-day event to a Holidays schedule than using
        :py:meth:`add_event()`. When used on a businessHours schedule, a TypeError will be raised.

        If :attr:`recur` is True and the :attr:`recurrence` dict is not present, the method will set the holiday to
        repeat yearly on the same month and day, which works for holidays like Christmas that fall on the same date.
        If you need to add a holiday, such as Thanksgiving, that recurs on the 4th Thursday of November,
        the :attr:`recurrence` dictionary should be used. For example, Thanksgiving can be defined as follows::

            recurrence = {
                'recurForEver': True,
                'recurYearlyByDay': {
                    'day': 'THURSDAY',
                    'week': 'FOURTH',
                    'month': 'NOVEMBER'
                }
            }

        The format of this dict, and accepted values can be found
        `here <https://developer.webex.com/docs/api/v1/
        webex-calling-organization-settings-with-location-scheduling/create-a-schedule-event>`_

        Args:
            name (str): The name of the holiday
            date (str): The date the holiday occurs this year in the format YYYY-MM-DD.
            recur (bool, optional): Whether the holiday recurs.
            recurrence (dict, optional): A dict of the recurrence info.

        Returns:
            bool: True on success, False otherwise

        Raises:
            TypeError: Raised when attempting to add a holiday to a businessHours schedule

        """
        log.debug(f"add_holiday() started")
        new_event = {"name": name,
                     "startDate": date, "endDate": date, "allDayEnabled": True}
        date_object = datetime.strptime(date, "%Y-%m-%d")
        # If this isn't a Holidays schedule, we shouldn't accept a new holiday
        if self.type.lower() != "holidays":
            log.debug("Trying to add a holiday to a non-holidays schedule. Raising exception.")
            raise TypeError("Schedule is not of type 'holidays'. Cannot add holiday.")
        if recur is True:
            if recurrence is not None:
                new_event['recurrence'] = recurrence
            else:
                new_event['recurrence'] = {"recurForEver": True,
                                           "recurYearlyByDate": {"dayOfMonth": date_object.strftime("%d"),
                                                                 "month": date_object.strftime("%B").upper()
                                                                 }
                                           }
        api_resp = webex_api_call("post", f"v1/telephony/config/locations/"
                                          f"{self.parent.id}/schedules/{self.type}/{self.id}/events", payload=new_event)
        if api_resp:
            self.refresh_config()
            return True
        else:
            return False

    def delete_event(self, event: str):
        """ Delete an event from within the LocationSchedule

        The event can be passed by name or by ID since both are unique.

        Args:
            event (str): The event name or event ID

        Returns:
            bool: True on success, False otherwise

        """
        log.debug("delete_event() started")
        # Since we accept both the event name or ID, we need to loop through the events to find the one we need.
        for e in self.config['events']:
            if e['name'] == event or e['id'] == event:
                api_resp = webex_api_call("delete", f"v1/telephony/config/locations/{self.parent.id}"
                                                    f"/schedules/{self.type}/{self.id}/events/{e['id']}")
                if api_resp is True:
                    # Get a new copy of the config
                    self.refresh_config()
                    return True
                else:
                    self.refresh_config()
                    return False
        return False

    def create_event(self, name: str, start_date: str, end_date: str, start_time: str = "",
                     end_time: str = "", all_day: bool = False, recurrence: Optional[dict] = None):
        """ Create a new event within the LocationSchedule instance

        Due to the flexibility of the event recurrence needs to be provided as a dict. The format of this dict, and
        accepted values can be found `here <https://developer.webex.com/docs/api/v1/webex-calling-organization-settings-with-location-scheduling/create-a-schedule-event>`_

        For example, the following dict would define an event that recurs every weekday, from 9:00-5:00::

            recurrence = {
                'recurForEver': True,
                'recurWeekly': {
                    'monday': True
                }
            }


        Args:
            name (str): The name of the event
            start_date (str): The start date of the event
            end_date (str): The end date of the event
            start_time (str, optional): If this is not an all-day event, the time the event starts
            end_time (str, optional): If this is not an all-day event, the time the event ends
            all_day (bool, optional): True if this is an all-day event. start_time and end_time will be ignored.
            recurrence (dict, optional): Dict of recurrence configuration

        Returns:
            bool: True on success, False otherwise

        """
        log.debug("create_event() started")
        # Input validation
        if all_day is False and (start_time == "" or end_time == ""):
            raise ValueError("If all_day == False, both start_time and end_time are required.")

        # Build the payload
        payload = {'name': name, 'startDate': start_date, 'endDate': end_date, 'allDay': all_day}
        if all_day is False:
            payload['startTime'] = start_time
            payload['endTime'] = end_time
        if recurrence is not None:
            payload['recurrence'] = recurrence

        api_resp = webex_api_call("post", f"v1/telephony/config/locations/{self.parent.id}/"
                                          f"schedules/{self.type}/{self.id}/events",
                                  payload=payload)
        if api_resp:
            self.refresh_config()
            return True
        else:
            self.refresh_config()
            return False

    def update_event(self, id: str, name: str = None, start_date: str = None, end_date: str = None,
                     start_time: str = None,
                     end_time: str = None, all_day: bool = None, recurrence: dict = None):
        log.debug("update_event() started")
        # Input validation
        if all_day is False and (start_time == "" or end_time == ""):
            raise ValueError("If all_day == False, both start_time and end_time are required.")

        # Build the payload
        payload = self.get_event_config_by_id(id)
        if name is not None:
            payload['name'] = name
        if start_date is not None:
            payload['startDate'] = start_date
        if end_date is not None:
            payload['endDate'] = end_date
        if all_day is not None:
            payload['allDay'] = all_day
            if all_day is False:
                if start_time is not None:
                    payload['startTime'] = start_time
                if end_time is not None:
                    payload['endTime'] = end_time
        if recurrence is not None:
            payload['recurrence'] = recurrence

        api_resp = webex_api_call("put", f"v1/telephony/config/")
        if api_resp:
            return True
        else:
            return False

    def get_event_config_by_id(self, id: str) -> Optional[dict]:
        """ Get the 'events' dict for a specific event.

        This method is useful if you are modifying an event and want to provide the full config.

        Args:
            id (str): The Event ID

        Returns:
            dict: The config of the event as a dict. If the Event ID is not found, None is returned.

        """
        for e in self.config['events']:
            if e['id'] == id:
                return e
        return None


class CallParkGroup:
    pass


@dataclass
class CallParkExtension:
    parent: wxcadm.location.Location
    """ The Location to which the Call Park Extension is assigned """
    id: str
    """ The ID of the Call Park Extension """
    name: str
    """ The name of the Call Park Extension """
    extension: str
    """ The Call Park Extension number (as a string) """

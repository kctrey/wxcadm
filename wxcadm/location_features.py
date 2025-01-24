from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from collections import UserList
from datetime import datetime

import wxcadm.location
from .realtime import RealtimeClass
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

    def clone(self, target_location: Optional[wxcadm.Location] = None, name: Optional[str] = None):
        """ Clone the LocationSchedule to another Location or to the same Location with a new name

        Either a `target_location` or a `name` must be specified. If both are specified, the Schedule will be cloned to
        the new Location with the given name.

        Args:
            target_location (Location, optional): The Location to clone the Schedule to
            name (str, optional): The name of the Schedule to create.

        Returns:
            str: The LocationSchedule ID of the newly-created Schedule

        Raises:
            ValueError: Raised when `target_location` and `name` are not provided

        """
        if target_location is None and name is None:
            raise ValueError('target_location or name must be provided')
        payload = dict(self.config)
        del payload['id']
        if name is not None:
            payload['name'] = name
        if target_location is not None:
            target_locid = target_location.id
        else:
            target_locid = self.parent.id
        response = webex_api_call('post', f'v1/telephony/config/locations/{target_locid}/schedules', payload=payload)
        return response['id']


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


@dataclass
class VoicePortal(RealtimeClass):
    """ The class for the Voice Portal at the Location

    .. note::

        Unlike all other methods, changing an attribute of this class will immediately push the change to Webex. This
        is being done to test a new API logic which performs real-time changes.

    """
    log.info("Getting Voice Portal data")
    location: wxcadm.Location = field(repr=False)
    """ The :class:`Location` of the Voice Portal """
    id: str = field(repr=True, init=False, default=None)
    """ The identifier for the Voice Portal """
    language: str = field(repr=True, init=False, default=None)
    """ The language to use for announcements """
    language_code: str = field(repr=True, init=False, default=None)
    """ Language code for voicemail group audio announcement """
    extension: str = field(repr=True, init=False, default=None)
    """ The Voice Portal extension """
    phone_number: str = field(repr=True, init=False, default=None)
    """ The Voice Portal DID """
    first_name: str = field(repr=True, init=False, default=None)
    """ The first name of the Voice Portal in the directory """
    last_name: str = field(repr=True, init=False, default=None)
    """ The last name of the Voice Portal in the directory """
    _api_fields = ['phone_number', 'extension']
    _initialized = False

    def __post_init__(self):
        self.data_url: str = f'v1/telephony/config/locations/{self.location.id}/voicePortal'
        super().__init__()

    def copy_config(self, target_location: wxcadm.Location, phone_number: str = None, passcode: str = None) -> bool:
        """ Copies the Voice Portal settings to another Location.

        The phone number and passcode will not be copied. To define those values as part of the copy operation,
        ensure those arguments are passed to the method.

        Args:
            target_location (wxcadm.Location): The :class:`Location` to copy the settings to
            phone_number (str, optional): The phone number to assign to the Voice Portal
            passcode (str, optional): The Voice Portal passcode to set

        Returns:
            bool: True on success

        """
        payload = {
            'name': 'Voice Portal',
            'languageCode': self.language_code,
            'extension': self.extension,
            'firstName': self.first_name,
            'lastName': self.last_name,
        }
        if phone_number is not None:
            payload['phoneNumber'] = phone_number
        if passcode is not None:
            payload['passcode'] = {
                'newPasscode': passcode,
                'confirmPasscode': passcode
            }
        if isinstance(target_location, wxcadm.Location):
            if target_location.calling_enabled is False:
                raise ValueError("Target Location is not Webex Calling enabled")
            webex_api_call('put', f"v1/telephony/config/locations/{target_location.id}/voicePortal",
                           payload=payload, params={'orgId': target_location.org_id})
        else:
            raise ValueError("target_location much be a Location instance")

        return True


class OutgoingPermissionDigitPatternList:
    def __init__(self, location: wxcadm.Location):
        log.info('Initializing OutgoingPermissionDigitPatternList')
        self.location = location
        self.patterns = self._get_data()

    def _get_data(self) -> list:
        pattern_list = []
        log.debug('Getting data from Webex')
        response = webex_api_call('get',
                                  f'v1/telephony/config/locations/{self.location.id}/outgoingPermission/digitPatterns')
        for pattern in response['digitPatterns']:
            pattern_list.append(OutgoingPermissionDigitPattern(self.location, config=pattern))
        return pattern_list

    def refresh(self):
        self.patterns = self._get_data()
        return self

    def create(self, name: str, pattern: str, action: str, transfer_enabled: Optional[bool] = False):
        """ Create a new Outgoing Permission Digit Pattern for the Location

        Args:
            name (str): The name of the pattern

            pattern (str): The digit pattern. See Webex documentation for valid values.

            action (str): The action to take. Valid values are `'ALLOW'`, `'BLOCK'`, `'AUTH_CODE'`,
            `'TRANSFER_NUMBER_1'`, `'TRANSFER_NUMBER_2'`, `'TRANSFER_NUMBER_3'`

            transfer_enabled (bool): Whether the setting is used for transferred or forwarded calls.

        Returns:
            OutgoingPermissionDigitPattern: The created pattern

        Raises:
            wxcadm.APIError: Raised when the API call fails

        """
        payload = {
            'name': name,
            'pattern': pattern,
            'action': action,
            'transferEnabled': transfer_enabled
        }
        response = webex_api_call('post',
                                  f'v1/telephony/config/locations/{self.location.id}/outgoingPermission/digitPatterns',
                                  params={'orgId': self.location.org_id},
                                  payload=payload)
        # Use the ID that was returned to get the object we want to return
        pattern_id = response['id']
        response = webex_api_call(
            'get',
            f'v1/telephony/config/locations/{self.location.id}/outgoingPermission/digitPatterns/{pattern_id}',
            params={'orgId': self.location.org_id}
        )
        new_pattern = OutgoingPermissionDigitPattern(self.location, response)
        self.patterns.append(new_pattern)
        return new_pattern

    def delete_all(self):
        """ Delete all Outgoing Permission Digit Patterns for this Location

        Returns:
            bool: True on success

        """
        webex_api_call(
            'delete',
            f'v1/telephony/config/locations/{self.location.id}/outgoingPermission/digitPatterns',
            params={'orgId': self.location.org_id}
        )
        self.refresh()
        return True


class OutgoingPermissionDigitPattern:
    def __init__(self, location: wxcadm.Location, config: dict):
        self.location = location
        self.id: str = config.get('id', '')
        self.name: str = config.get('name', '')
        self.pattern: str = config.get('pattern', '')
        self.action: str = config.get('action', '')
        self.transfer_enabled: bool = config.get('transferEnabled')

    def delete(self) -> bool:
        """ Delete the specified digit pattern

        Returns:
            bool: True on success

        """
        webex_api_call(
            'delete',
            f'v1/telephony/config/locations/{self.location.id}/outgoingPermission/digitPatterns/{self.id}'
        )
        return True

    def update(self,
               name: Optional[str] = None,
               pattern: Optional[str] = None,
               action: Optional[str] = None,
               transfer_enabled: Optional[bool] = None):
        name = self.name if name is None else name
        pattern = self.pattern if pattern is None else pattern
        action = self.action if action is None else action
        transfer_enabled = self.transfer_enabled if transfer_enabled is None else transfer_enabled
        payload = {
            'name': name,
            'pattern': pattern,
            'action': action,
            'transferEnabled': transfer_enabled
        }
        webex_api_call(
            'put',
            f'v1/telephony/config/locations/{self.location.id}/outgoingPermission/digitPatterns/{self.id}',
            params={'orgId': self.location.org_id},
            payload=payload
        )
        self.name = name
        self.pattern = pattern
        self.action = action
        self.transfer_enabled = transfer_enabled
        return self


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VoicemailGroup:
    org: wxcadm.Org
    id: str
    name: str
    location_name: str
    location_id: str
    extension: str
    enabled: bool
    esn: Optional[str] = None
    _phone_number: Optional[str] = field(init=False, default=None)
    _first_name: Optional[str] = field(init=False, default=None)
    _last_name: Optional[str] = field(init=False, default=None)
    _language_code: Optional[str] = field(init=False, default=None)
    _greeting: Optional[str] = field(init=False, default=None)
    _greeting_uploaded: Optional[bool] = field(init=False, default=None)
    _greeting_description: Optional[str] = field(init=False, default=None)
    _message_storage: Optional[dict] = field(init=False, default=None)
    _notifications: Optional[dict] = field(init=False, default=None)
    _fax_message: Optional[dict] = field(init=False, default=None)
    _transfer_to_number: Optional[dict] = field(init=False, default=None)
    _email_copy_of_message: Optional[dict] = field(init=False, default=None)
    _message_forwarding_enabled: Optional[bool] = field(init=False, default=None)

    def _get_details(self):
        response = webex_api_call('get',
                                  f'v1/telephony/config/locations/{self.location_id}/voicemailGroups/{self.id}',
                                  params={'orgId': self.org.id})
        self.name = response.get('name')
        self.extension = response.get('extension')
        self.enabled = response.get('enabled')
        self._phone_number = response.get('phoneNumber', None)
        self._first_name = response.get('firstName', '')
        self._last_name = response.get('lastName', '')
        self._language_code = response.get('languageCode', '')
        self._greeting = response.get('greeting', '')
        self._greeting_uploaded = response.get('greetingUploaded', '')
        self._greeting_description = response.get('greetingDescription', '')
        self._message_storage = response.get('messageStorage', None)
        self._notifications = response.get('notifications', None)
        self._fax_message = response.get('faxMessage', None)
        self._transfer_to_number = response.get('transferToNumber', None)
        self._email_copy_of_message = response.get('emailCopyOfMessage', None)
        self._message_forwarding_enabled = response.get('voiceMessageForwardingEnabled', None)

    @property
    def phone_number(self):
        """ The phone number of the Voicemail Group """
        if self._phone_number is None:
            self._get_details()
        return self._phone_number

    @property
    def last_name(self):
        """ The last name of the Voicemail Group """
        if self._last_name is None:
            self._get_details()
        return self._last_name

    @property
    def first_name(self):
        """ The firt name of the Voicemail Group """
        if self._first_name is None:
            self._get_details()
        return self._first_name

    @property
    def language_code(self):
        """ The language code of the Voicemail Group """
        if self._language_code is None:
            self._get_details()
        return self._language_code

    @property
    def greeting_type(self):
        """ The greeting type, either 'DEFAULT' or 'CUSTOM' """
        if self._greeting is None:
            self._get_details()
        return self._greeting

    @property
    def greeting_uploaded(self):
        """ True if CUSTOM greeting has been previously uploaded """
        if self._greeting_uploaded is None:
            self._get_details()
        return self._

    @property
    def greeting_description(self):
        """ CUSTOM greeting for previously uploaded greeting """
        if self._greeting_description is None:
            self._get_details()
        return self._greeting_description

    @property
    def message_storage(self):
        """ Message storage information as a dict """
        if self._message_storage is None:
            self._get_details()
        return self._message_storage

    @property
    def notifications(self):
        """ Notification settings as a dict """
        if self._notifications is None:
            self._get_details()
        return self._notifications

    @property
    def fax_message(self):
        """ Fax messaging settings as a dict """
        if self._fax_message is None:
            self._get_details()
        return self._fax_message

    @property
    def transfer_to_number(self):
        """ Transfer settings for the Voicemail Group as a dict """
        if self._transfer_to_number is None:
            self._get_details()
        return self._transfer_to_number

    @property
    def email_copy_of_message(self):
        """ Email CC settings as a dict """
        if self._email_copy_of_message is None:
            self._get_details()
        return self._email_copy_of_message

    @property
    def message_forwarding_enabled(self):
        """ Whether voice message forwarding is enabled """
        if self._message_forwarding_enabled is None:
            self._get_details()
        return self._message_forwarding_enabled

    def update(self,
               name: Optional[str] = None,
               phone_number: Optional[str] = None,
               extension: Optional[str] = None,
               first_name: Optional[str] = None,
               last_name: Optional[str] = None,
               enabled: Optional[bool] = None,
               language_code: Optional[str] = None,
               greeting_type: Optional[str] = None,
               greeting_description: Optional[str] = None,
               message_storage: Optional[dict] = None,
               notifications: Optional[dict] = None,
               fax_message: Optional[dict] = None,
               transfer_to_number: Optional[dict] = None,
               email_copy_of_message: Optional[dict] = None
               ):
        """ Update Voicmeail Group settings

        When using this method, pass only the values that you wish to change. Values omitted from the parameters will
        not be changed.

        Args:
            name (str, optional): The name of the Voicemail Group
            phone_number (str, optional): The phone number of the Voicemail Group
            extension (str, optional): The extension of the Voicemail Group
            first_name (str, optional): The first name of the Voicemail Group
            last_name (str, optional): The last name of the Voicemail Group
            enabled (bool, optional): Whether the Voicemail Group is enabled
            language_code (str, optional): The language code
            greeting_type (str, optional): The greeting type, either 'CUSTOM' or 'DEFAULT'
            greeting_description (str, optional): The greeting for CUSTOM greetings
            message_storage (dict, optional): The message storage settings as a dict
            notifications (dict, optional): The notification settings as a dict
            fax_message (dict, optional): The fax settings as a dict
            transfer_to_number (dict, optional): The transfer settings as a dict
            email_copy_of_message (dict, optional): The email CC settings as a dict

        Returns:
            VoicemailGroup: The updated VoicemailGroup instance

        Raises:
            wxcadm.APIError: Raised when the update is rejected by Webex

        """
        name = self.name if name is None else name
        phone_number = self.phone_number if phone_number is None else phone_number
        extension = self.extension if extension is None else extension
        first_name = self.first_name if first_name is None else first_name
        last_name = self.last_name if last_name is None else last_name
        enabled = self.enabled if enabled is None else enabled
        language_code = self.language_code if language_code is None else language_code
        greeting_type = self.greeting_type if greeting_type is None else greeting_type
        greeting_description = self.greeting_description if greeting_description is None else greeting_description
        message_storage = self.message_storage if message_storage is None else message_storage
        notifications = self.notifications if notifications is None else notifications
        fax_message = self.fax_message if fax_message is None else fax_message
        transfer_to_number = self.transfer_to_number if transfer_to_number is None else transfer_to_number
        email_copy_of_message = self.email_copy_of_message if email_copy_of_message is None else email_copy_of_message
        payload = {
            'name': name,
            'phoneNumber': phone_number,
            'extension': extension,
            'firstName': first_name,
            'lastName': last_name,
            'enabled': enabled,
            'languageCode': language_code,
            'greeting': greeting_type,
            'greetingDescription': greeting_description,
            'messageStorage': message_storage,
            'notifications': notifications,
            'faxMessage': fax_message,
            'transferToNumber': transfer_to_number,
            'emailCopyOfMessage': email_copy_of_message
        }
        webex_api_call('put',
                       f'v1/telephony/config/locations/{self.location_id}/voicemailGroups/{self.id}',
                       payload=payload)
        self._get_details()
        return self

    def delete(self):
        """ Delete the Group Voicemail """
        webex_api_call('delete',
                       f'v1/telephony/config/locations/{self.location_id}/voicemailGroups/{self.id}')
        return True

    def enable_email_copy(self, email: str):
        """ Enable sending of copies of voicemails to an email

        This is a shortcut for calling the :meth:`update()` method with the `email_copy_of_message` argument dict

        Args:
             email (str): The email address to send copies of messages to

        Returns:
            VoicemailGroup: The updated VoicemailGroup instance

        Raises:
            wxcadm.APIError: Raised when the update is rejected by Webex

        """
        email_conf = {'enabled': True, 'emailId': email}
        self.update(email_copy_of_message=email_conf)
        return self


class VoicemailGroupList(UserList):
    def __init__(self, org: wxcadm.Org):
        log.info(f'Initializing VoicemailGroupList for Org: {org.name}')
        super().__init__()
        self.org = org
        self.data = self._get_data()

    def _get_data(self) -> list:
        log.debug('Getting data')
        data = []
        response = webex_api_call('get', 'v1/telephony/config/voicemailGroups', params={'orgId': self.org.id})
        for group in response['voicemailGroups']:
            group['org'] = self.org
            data.append(VoicemailGroup.from_dict(group))
        return data

    def refresh(self):
        self.data = self._get_data()
        return self

    def get(self, name: Optional[str] = None, id: Optional[str] = None):
        """ Get the VoicemailGroup matching the given `id` or `name`

        Args:
             name (str, optional): The Voicemail Group name to retrieve
             id (str, optional): The Voicemail Group ID to retrieve

        Returns:
            VoicemailGroup: The matching instance. None is returned if no match is found

        """
        for item in self.data:
            if item.id == id or item.name == name:
                return item
        return None

    def create(self,
               location: wxcadm.Location,
               name: str,
               extension: str,
               passcode: str,
               phone_number: Optional[str] = None,
               first_name: Optional[str] = None,
               last_name: Optional[str] = None,
               language_code: Optional[str] = 'en_us',
               message_storage: Optional[dict] = None,
               notifications: Optional[dict] = None,
               fax_message: Optional[dict] = None,
               transfer_to_number: Optional[dict] = None,
               email_copy_of_message: Optional[dict] = None):
        log.info(f'Creating Voicemail Group {name} in Location {location.name}')
        if message_storage is None:
            message_storage = {'storageType': 'INTERNAL'}
        if notifications is None:
            notifications = {'enabled': False}
        if fax_message is None:
            fax_message = {'enabled': False}
        if transfer_to_number is None:
            transfer_to_number = {'enabled': False}
        if email_copy_of_message is None:
            email_copy_of_message = {'enabled': False}

        payload = {
            'name': name,
            'extension': extension,
            'passcode': passcode,
            'phoneNumber': phone_number,
            'firstName': first_name,
            'lastName': last_name,
            'languageCode': language_code,
            'messageStorage': message_storage,
            'notifications': notifications,
            'faxMessage': fax_message,
            'transferToNumber': transfer_to_number,
            'emailCopyOfMessage': email_copy_of_message
        }
        response = webex_api_call('post',
                                  f'v1/telephony/config/locations/{location.id}/voicemailGroups',
                                  params={'orgId': self.org.id},
                                  payload=payload)
        vg_id = response['id']
        self.refresh()
        return self.get(id=vg_id)


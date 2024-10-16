from __future__ import annotations

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .number import NumberList
from collections import UserList

import wxcadm
from wxcadm import log
from .location_features import LocationSchedule, CallParkExtension, VoicePortal, OutgoingPermissionDigitPatternList
from .call_queue import CallQueueList
from .hunt_group import HuntGroupList
from .auto_attendant import AutoAttendantList
from .pickup_group import PickupGroupList
from .common import *
from .exceptions import APIError
from .dect import DECTNetworkList
from .number import NumberList
from .virtual_line import VirtualLineList
from .call_routing import TranslationPatternList


class LocationList(UserList):
    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing LocationList instance")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_items()

    def refresh(self):
        """ Refresh the list of Locations from Webex """
        self.data = self._get_items()

    def _get_items(self):
        if isinstance(self.parent, wxcadm.Org):
            log.debug("Using Org ID as data filter")
            params = {'orgId': self.parent.id}
        else:
            raise ValueError("Unsupported parent class")

        log.debug("Getting Location list")
        response = webex_api_call('get', f'v1/locations', params=params)
        log.debug(f"Received {len(response)} entries")
        items = []
        for entry in response:
            items.append(Location(parent=self.parent,
                                  location_id=entry['id'],
                                  name=entry['name'],
                                  address=entry['address'],
                                  time_zone=entry.get('timeZone', 'Unknown'),
                                  preferred_language=entry.get('preferredLanguage', 'en_US')))
        return items

    def get(self, id: str = None, name: str = None, spark_id: str = None):
        """ Get the Location instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Locations will be
        searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method will raise an
        Exception.

        Args:
            id (str, optional): The Location ID to find
            name (str, optional): The Location Name to find
            spark_id (str, optional): The Spark ID to find

        Returns:
            Location: The Location instance correlating to the given search argument.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        if id is not None:
            for location in self.data:
                if location.id == id:
                    return location
        if name is not None:
            for location in self.data:
                if location.name == name:
                    return location
        if spark_id is not None:
            for location in self.data:
                if location.spark_id == spark_id:
                    return location
        return None

    def create(self,
               name: str,
               time_zone: str,
               preferred_language: str,
               address: dict):
        """ Create a new Location

        Args:
            name (str): The name of the Location
            time_zone (str): The Time Zone of the Location (e.g. America/Chicago)
            preferred_language (str): The preferred language for phones and menus (i.e. en_US)
            address (dict): A dictionary containing the address elements. The format of this dict should be::

                {
                    "address1": "100 N. Main",
                    "address2": "Suite 200",
                    "city": "Houston",
                    "state": "TX",
                    "postalCode": "32123",
                    "country": "US"
                }

        Returns:
            dict: The response from Webex with the Location details.

        """
        payload = {
            'name': name,
            'timeZone': time_zone,
            'preferredLanguage': preferred_language,
            'announcementLanguage': None,
            'address': address
        }
        response = webex_api_call('post', 'v1/locations', payload=payload)
        self.refresh()
        return self.get(id=response['id'])

    def webex_calling(self, enabled: bool = True, single: bool = False) -> Location | list[Location]:
        """ Return a list of :py:class:`Location` where Webex Calling is enabled/disabled

        Args:
            enabled (bool, optional): True (default) returns Webex Calling people. False returns Locations without
                Webex Calling

            single (bool, optional): When True, returns only a single Location, which can be useful for some API calls,
                such as the Device Password API.

        Returns:
            list[:py:class:`Location`]: List of :py:class:`Location` instances. An empty list is returned if none match
            the given criteria

            :py:class:`Location`: When ``single=True`` is present, a single Location will be returned.

        """
        locations = []
        entry: Location
        for entry in self.data:
            if entry.calling_enabled is enabled:
                if single is True:
                    return entry
                locations.append(entry)
        return locations


class Location:
    def __init__(self, parent: wxcadm.Org, location_id: str,
                 name: str,
                 time_zone: str,
                 preferred_language: str,
                 announcement_language: str = None,
                 address: dict = None):
        """Initialize a Location instance

        .. note::
            Location instances are normally not instantiated manually and are done automatically with the
            :meth:`Org.get_locations` method.

        Args:
            location_id (str): The Webex ID of the Location
            name (str): The name of the Location
            time_zone (str): The time zone of the Location
            preferred_language (str): The preferred language at the Location
            announcement_language (str): The language for audio announcements at the Location
            address (dict): The address information for the Location

        Returns:
             Location (object): The Location instance

        """
        self._parent = parent
        self.parent = parent
        self._headers = parent._headers
        self.id: str = location_id
        """The Webex ID of the Location"""
        self.name: str = name
        """The name of the Location"""
        self.address: dict = address
        """The address of the Location"""
        self.time_zone: str = time_zone
        """ The Location time zone"""
        self.preferred_language: str = preferred_language
        """ The preferred language at the Location"""
        self.announcement_language: str = announcement_language
        """ The language for audio announcements at the Location"""
        self._calling_enabled: Optional[bool] = None
        self._calling_config: Optional[dict] = None
        self._pickup_groups: Optional[PickupGroupList] = None
        self._call_queues: Optional[CallQueueList] = None
        self._hunt_groups: Optional[HuntGroupList] = None
        self._dect_networks: Optional[DECTNetworkList] = None
        self._outgoing_permission_digit_patterns: Optional[OutgoingPermissionDigitPatternList] = None
        self._numbers: Optional[NumberList] = None
        self._virtual_lines: Optional[VirtualLineList] = None
        self._floors: Optional[LocationFloorList] = None
        self._translation_patterns = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def outgoing_permission_digit_patterns(self) -> OutgoingPermissionDigitPatternList:
        if self._outgoing_permission_digit_patterns is None:
            self._outgoing_permission_digit_patterns = OutgoingPermissionDigitPatternList(self)
        return self._outgoing_permission_digit_patterns

    @property
    def workspace_location(self):
        """ Get the :class:`WorkspaceLocation` associated with this Location

        Returns:
            WorkspaceLocation: The WorkspaceLocation associated with this Location

        """
        return self.parent.workspace_locations.get(name=self.name)

    @property
    def virtual_lines(self) -> VirtualLineList:
        """ The :class:`VirtualLineList` of Virtual Lines for this Location

        Returns:
            VirtualLineList: The list of Virtual Lines
        """
        if self._virtual_lines is None:
            self._virtual_lines = VirtualLineList(self)
        return self._virtual_lines

    @property
    def floors(self) -> LocationFloorList:
        """ The :class:`LocationFloorList` of floors for this Location """
        if self._floors is None:
            self._floors = LocationFloorList(self)
        return self._floors

    @property
    def calling_enabled(self) -> bool:
        """ Whether the Location is enabled for Webex Calling """
        if self._calling_enabled is None:
            try:
                response = webex_api_call("get", f"v1/telephony/config/locations/{self.id}",
                                          params={'orgId': self.org_id})
                if 'id' in response.keys():
                    self._calling_enabled = True
                    self._calling_config = response
            except APIError:
                self._calling_enabled = False
                self._calling_config = None
        return self._calling_enabled

    @property
    def calling_config(self) -> dict:
        """ The Webex Calling configuration dict """
        if self._calling_config is None:
            try:
                response = webex_api_call("get", f"v1/telephony/config/locations/{self.id}",
                                          params={'orgId': self.org_id})
                if 'id' in response.keys():
                    self._calling_enabled = True
                    self._calling_config = response
            except APIError:
                self._calling_enabled = False
                self._calling_config = None
        return self._calling_config

    @property
    def org_id(self):
        """ The Org ID to which the Location belongs. :attr:`parent.id` can also be used. """
        return self.parent.id

    def enable_webex_calling(self) -> bool:
        """ Enable the Location for Webex Calling

        If the Location is already a Webex Calling Location, no action will be taken and the method will return True.

        Returns:
            bool: True on success

        """
        if self.calling_enabled is False:
            log.info(f"Enabling Webex Calling for Location {self.name}")
            payload = {
                "id": self.id,
                "name": self.name,
                "timeZone": self.time_zone,
                "preferredLanguage": self.preferred_language.lower(),
                "announcementLanguage": self.preferred_language.lower(),
                "address": self.address
            }
            webex_api_call("post", "v1/telephony/config/locations", payload=payload, params={'orgId': self.org_id})
            self._calling_enabled = True
        return True

    def delete(self):
        """ Delete a Location

        .. warning::

            There is currently no way to delete a Location outside of Control Hub. The method is defined here so users
            aren't looking for it expecting it to be there. It will always return False. When the API is exposed,
            this method will be updated to support it.

        Returns:
            bool: Always returns False and no action is taken on Webex

        """
        return False

    @property
    def spark_id(self):
        """The ID used by all underlying services."""
        return decode_spark_id(self.id)

    @property
    def hunt_groups(self):
        """ :class:`HuntGroupList` list of :class:`HuntGroup` instances for this Location """
        log.info(f"Getting Hunt Groups for Location: {self.name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        self._hunt_groups = HuntGroupList(self)
        return self._hunt_groups

    @property
    def announcements(self):
        """ List of :py:class:`Announcement` instances for the Location

        .. note::
            This does not include announcements built at the Organization level

        """
        annc_list = self._parent.announcements.get_by_location_id(self.id)
        return annc_list

    @property
    def translation_patterns(self):
        """ The :class:`TranslationPatternList` with all Translation Patterns for the Location """
        if self._translation_patterns is None:
            self._translation_patterns = TranslationPatternList(self)
        return self._translation_patterns

    @property
    def auto_attendants(self):
        """ List of AutoAttendant instances for this Location """
        log.info(f"Getting Auto Attendants for Location: {self.name}")
        return AutoAttendantList(self)

    @property
    def call_queues(self) -> Optional[CallQueueList]:
        """ :class:`CallQueueList` of :class:`CallQueue` instances for this Location """
        if self._call_queues is None:
            log.info(f"Getting Call Queues for Location: {self.name}")
            if self.calling_enabled is False:
                log.warn("Not a Webex Calling Location")
                return None
            self._call_queues = CallQueueList(self)
        return self._call_queues

    @property
    def numbers(self) -> Optional[NumberList]:
        """ All the Numbers for the Location

        Returns:
            NumberList: The :class:`NumberList` for the Location

        """
        log.info("Getting Location numbers from Webex")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        if self._numbers is None:
            self._numbers = NumberList(self)
        return self._numbers

    @property
    def available_numbers(self):
        """Returns all available numbers for the Location.

        Returns both Active and Inactive numbers so that numbers can be assigned prior to activation/porting/

        Returns:
            list[dict]: A list of available numbers, in dict form

        """
        log.debug('Getting available numbers')
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        params = {'locationId': self.id, 'available': True}
        response = webex_api_call("get", "v1/telephony/config/numbers", params=params)
        if len(response.get('phoneNumbers', 0)) == 0:
            return None
        else:
            return response['phoneNumbers']

    @property
    def main_number(self):
        """Returns the Main Number for this Location, if defined

        Returns:
            str: The main number for the Location. None is returned if a main number cannot be found.

        """
        for number in self._parent.numbers:
            if number['location'].name == self.name and number['mainNumber'] is True:
                return number['number']
        return None

    @property
    def schedules(self):
        """ List of all :class:`wxcadm.LocationSchedule` instances for this Location"""
        log.debug('Getting Location Schedules')
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        response = []
        api_resp = webex_api_call("get", f"v1/telephony/config/locations/{self.id}/schedules", headers=self._headers)
        for schedule in api_resp['schedules']:
            log.debug(f'\tSchedule: {schedule}')
            this_schedule = LocationSchedule(self, schedule['id'], schedule['name'], schedule['type'])
            response.append(this_schedule)
        return response

    def set_announcement_language(self, language: str,
                                  update_users: bool = False,
                                  update_features: bool = False) -> bool:
        """ Set the Announcement Language for the Location or update the Announcement Language for existing users
        or features.

        When using this method, setting either ``update_users`` or ``update_features`` will only change the
        Announcement Language for existing users/features. It does not change the Location default that will be used
        for any new users or features. To ensure that the default language is changed, the method should be called
        without those arguments.

        Args:
            language (str): The language code (e.g. ``en_US``) to assign
            update_users (bool, optional): True to update all existing Users and Workspaces to the new language
            update_features (bool, optional): True to update all existing Features to the new language.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Setting language for {self.name} to {language}")
        payload = {
            'announcementLanguageCode': language,
            'agentEnabled': update_users,
            'serviceEnabled': update_features
        }
        success = webex_api_call('post',
                                 f'/v1/telephony/config/locations/{self.id}/actions/modifyAnnouncementLanguage/invoke',
                                 payload=payload)
        log.debug(f"Response: {success}")
        if success:
            log.info("Language change succeeded")
            return True
        else:
            log.info("Language change failed")
            return False

    def upload_moh_file(self, filename: str):
        """ Upload and activate a custom Music On Hold audio file.

        The audio file must be a WAV file that conforms with the Webex Calling requirements. It is recommended to test
        any WAV file by manually uploading it to a Location in Control Hub. The method will return False if the WAV file
        is rejected by Webex.

        Args:
            filename (str): The filename, including path, to the WAV file to upload.

        Returns:
            bool: True on success, False otherwise

        .. warning::

            This method requires the CP-API access scope.

        """
        log.debug(f'Uploading MOH file: {filename}')
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        upload = self._parent._cpapi.upload_moh_file(self.id, filename)
        if upload is True:
            log.debug('\tActivating MOH')
            activate = self._parent._cpapi.set_custom_moh(self.id, filename)
            if activate is True:
                log.debug('\t\tSuccessful activation')
                return True
            else:
                log.debug('\t\tActivation failed')
                return False
        else:
            return False

    def set_default_moh(self):
        """ Set the MOH to be the Webex Calling system default music.

        Returns:
            bool: True on success, False otherwise

        .. warning::

            This method requires the CP-API access scope.
        """
        log.debug('Setting Default MOH')
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        activate = self._parent._cpapi.set_default_moh(self.id)
        if activate is True:
            log.debug('\tSuccessful activation')
            return True
        else:
            log.debug('\tActivation failed')
            return False

    @property
    def outgoing_call_permissions(self):
        """ The Outgoing Call Permissions dicts (as a list) for the Location"""
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        ocp = webex_api_call('get', f'/v1/telephony/config/locations/{self.id}/outgoingPermission')
        return ocp['callingPermissions']

    def set_outgoing_call_permissions(self, outgoing_call_permissions: list) -> Optional[bool]:
        """ Ste the Outgoing Call Permissions for the Location

        This method uses the `callingPermissions` list style of the Webex API, which is the same format as returned by
        the :py:meth:`outgoing_call_permissions` property. The easiest method to change the permissions is to pull the
        `outgoing_call_permissions` list, modify it and pass it back to this method.

        Args:
            outgoing_call_permissions (list): The Webex `callingPermissions` list

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f'Setting Outgoing Call Permission for Location: {self.name}')
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        log.debug(f'\tNew Permissions: {outgoing_call_permissions}')
        if not isinstance(outgoing_call_permissions, list):
            log.warning('outgoing_call_permissions is not a list')
            raise ValueError('outgoing_call_permissions must be a list')

        payload = {'callingPermissions': outgoing_call_permissions}

        success = webex_api_call('put', f'/v1/telephony/config/locations/{self.id}/outgoingPermission',
                                 payload=payload)
        if success:
            return True
        else:
            return False

    @property
    def park_extensions(self):
        """ List of :py:class:`CallParkExtension` instances for this Location """
        log.info(f"Getting Park Extensions for Location: {self.name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        park_extensions = []
        response = webex_api_call("get", "v1/telephony/config/callParkExtensions", params={'locationId': self.id})
        log.debug(f"Response:\n\t{response}")
        for entry in response['callParkExtensions']:
            this_instance = CallParkExtension(self, entry['id'], entry['name'], entry['extension'])
            park_extensions.append(this_instance)

        return park_extensions

    def create_park_extension(self, name: str, extension: str):
        """ Create a new Call Park Extension at the Location

        Args:
            name (str): The name of the Park Extension
            extension (str): The Park Extension

        Returns:
            str: The ID of the newly created CallParkExtension

        """
        log.info(f"Creating Park Extension {name} ({extension}) at Location: {self.name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        payload = {"name": name, "extension": extension}
        response = webex_api_call("post", f"v1/telephony/config/locations/{self.id}/callParkExtensions",
                                  params={'orgId': self._parent.id}, payload=payload)
        log.debug(f"Response:\n\t{response}")
        return response['id']

    @property
    def pickup_groups(self) -> Optional[PickupGroupList]:
        """ :class:`PickupGroupList` list of :py:class:`PickupGroup` for this Location """
        log.info(f"Getting Pickup Groups for Location {self.name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        if self._pickup_groups is None:
            self._pickup_groups = PickupGroupList(self)
        return self._pickup_groups

    @property
    def voice_portal(self) -> VoicePortal:
        """ :class:`VoicePortal` instance for this Location """
        return VoicePortal(self)

    @property
    def dect_networks(self):
        """ :class:`DECTNetworkList` for this Location """
        if self._dect_networks is None:
            self._dect_networks = DECTNetworkList(self)
        return self._dect_networks


class LocationFloor:
    """ A Floor within a Location """
    def __init__(self, parent: Location, config: Optional[dict] = None, id: Optional[str] = None):
        self.parent = parent
        if config is None and id is not None:
            config = self._get_data(id)
        self.id: str = config['id']
        self.floor_number: int = config['floorNumber']
        self.name: str = config['displayName']

    def _get_data(self, id: str):
        response = webex_api_call('get', f'v1/locations/{self.parent.id}/floors/{id}')
        return response

    def update(self, floor_number: Optional[int] = None, name: Optional[str] = None) -> bool:
        """ Update the floor number and/or name of the floor

        Args:
            floor_number (int, optional): The new floor number
            name (str, optional): The new name for the floor

        Returns:
            bool: True on success

        """
        payload = {}
        if floor_number is not None:
            payload['floorNumber'] = floor_number
        if name is not None:
            payload['displayName'] = name
        response = webex_api_call('put', f'v1/locations/{self.parent.id}/floors/{self.id}', payload=payload,
                                  params={'orgId': self.parent.org_id})
        self.floor_number = response['floorNumber']
        self.name = response['displayName']
        return True

    def delete(self) -> bool:
        """ Delete the floor

        Returns:
            bool: True on success

        """
        webex_api_call('delete', f'v1/locations/{self.parent.id}/floors/{self.id}',
                       params={'orgId': self.parent.org_id})
        return True


class LocationFloorList(UserList):
    def __init__(self, parent: Location):
        super().__init__()
        """ List of :class:`LocationFloor` instances for the :class:`Location` """
        self.parent = parent
        self.data: list = []

        self._get_data()

    def _get_data(self):
        self.data = []
        response = webex_api_call('get', f'v1/locations/{self.parent.id}/floors',
                                  params={'orgId': self.parent.org_id})
        for floor in response:
            self.data.append(LocationFloor(self.parent, floor))

    def refresh(self):
        self._get_data()

    def create(self, floor_number: int, name: str):
        """ Create a new floor in the Location

        Args:
            floor_number (int): The floor number within the building
            name (str): The descriptive name of the floor (e.g. 'Basement', '2nd Floor')

        Returns:
            LocationFloor: The :class:`LocationFloor` instance that was created.

        Raises:
            ValueError: Raised when the ``floor_number`` already exists

        """
        # Validate the floor number doesn't exist
        for floor in self.data:
            if floor.floor_number == floor_number:
                raise ValueError('Duplicate floor number')
        payload = {
            'floorNumber': floor_number,
            'displayName': name
        }
        response = webex_api_call('post', f'v1/locations/{self.parent.id}/floors', payload=payload,
                                  params={'orgId': self.parent.org_id})
        self.data.append(LocationFloor(self.parent, config=response))






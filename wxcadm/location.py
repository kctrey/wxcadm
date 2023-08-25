from __future__ import annotations

from typing import Optional
from collections import UserList

import wxcadm
from wxcadm import log
from .location_features import LocationSchedule, CallParkExtension, HuntGroup
from .call_queue import CallQueueList
from .auto_attendant import AutoAttendant, AutoAttendantList
from .pickup_group import PickupGroupList
from .workspace import WorkspaceList
from .common import *
from .exceptions import APIError


class LocationList(UserList):
    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing LocationtList instance")
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
                                  time_zone=entry['timeZone'],
                                  preferred_language=entry['preferredLanguage']))
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
               announcement_language: str,
               address: dict):
        payload = {
            'name': name,
            'timeZone': time_zone,
            'preferredLanguage': preferred_language,
            'announcementLanguage': announcement_language,
            'address': address
        }
        response = webex_api_call('post', 'v1/locations', payload=payload)
        return response

    def webex_calling(self, enabled: bool = True) -> list[Location]:
        """ Return a list of :py:class:`Location` where Webex Calling is enabled/disabled

        Args:
            enabled (bool, optional): True (default) returns Webex Calling people. False returns Locations without
                Webex Calling

        Returns:
            list[:py:class:`Location`]: List of :py:class:`Location` instances. An empty list is returned if none match
            the given criteria

        """
        locations = []
        entry: Location
        for entry in self.data:
            if entry.calling_enabled is enabled:
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
        self.calling_enabled: bool = False
        """ Whether or not the Location is enabled for Webex Calling """
        self.calling_config: Optional[dict] = None
        """ The Webex Calling config for the Location, if enabled """
        self._pickup_groups: Optional[PickupGroupList] = None
        self._call_queues: Optional[CallQueueList] = None

        # Get the Webex Calling config and determine if the Location is Calling-enabled
        self._get_calling_config()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def _get_calling_config(self):
        try:
            response = webex_api_call("get", f"v1/telephony/config/locations/{self.id}")
            if 'id' in response.keys():
                self.calling_enabled = True
                self.calling_config = response
        except APIError:
            return None

    @property
    def spark_id(self):
        """The ID used by all of the underlying services."""
        return decode_spark_id(self.id)

    @property
    def hunt_groups(self):
        """List of HuntGroup instances for this Location"""
        log.info(f"Getting Hunt Groups for Location: {self.name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        hunt_groups = []
        response = webex_api_call("get", "v1/telephony/config/huntGroups", params={"locationId": self.id})
        log.debug(response)
        for hg in response['huntGroups']:
            this_instance = HuntGroup(self, hg['id'], hg['name'], hg['locationId'], hg['enabled'],
                                      hg.get("phoneNumber", ""), hg.get("extension", ""))
            hunt_groups.append(this_instance)
        return hunt_groups

    @property
    def announcements(self):
        """ List of :py:class:`Announcement` instances for the Location

        .. note::
            This does not include announcements built at the Organization level

        """
        annc_list = self._parent.announcements.get_by_location_id(self.id)
        return annc_list

    @property
    def auto_attendants(self):
        """ List of AutoAttendant instances for this Location """
        log.info(f"Getting Auto Attendants for Location: {self.name}")
        return AutoAttendantList(self)

    @property
    def call_queues(self) -> CallQueueList:
        """ :class:`CallQueueList` of :class:`CallQueue` instances for this Location """
        if self._call_queues is None:
            log.info(f"Getting Call Queues for Location: {self.name}")
            if self.calling_enabled is False:
                log.warn("Not a Webex Calling Location")
                return None
            self._call_queues = CallQueueList(self)
        return self._call_queues

    @property
    def numbers(self):
        """ All the Numbers for the Location

        Returns:
            list[dict]: List of dict containing information about each number

        """
        log.info("Getting Location numbers from Webex")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        params = {'locationId': self.id}
        response = webex_api_call("get", "v1/telephony/config/numbers", params=params)
        loc_numbers = response['phoneNumbers']
        for num in loc_numbers:
            if "owner" in num:
                if "id" in num['owner']:
                    person = self._parent.get_person_by_id(num['owner']['id'])
                    if person is not None:
                        num['owner'] = person
                    else:
                        if num['owner']['type'].upper() == "HUNT_GROUP":
                            hunt_group = self._parent.get_hunt_group_by_id(num['owner']['id'])
                            if hunt_group is not None:
                                num['owner'] = hunt_group
                        elif num['owner']['type'].upper() == "GROUP_PAGING":
                            paging_group = self._parent.get_paging_group(id=num['owner']['id'])
                            if paging_group is not None:
                                num['owner'] = paging_group
                        elif num['owner']['type'].upper() == "CALL_CENTER":
                            call_queue = self._parent.get_call_queue_by_id(num['owner']['id'])
                            if call_queue is not None:
                                num['owner'] = call_queue
                        elif num['owner']['type'].upper() == "AUTO_ATTENDANT":
                            auto_attendant = self._parent.get_auto_attendant(id=num['owner']['id'])
                            if auto_attendant is not None:
                                num['owner'] = auto_attendant
        return loc_numbers

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
        """ List of all of the :class:`wxcadm.LocationSchedule` instances for this Location"""
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

    def set_outgoing_call_permissions(self, outgoing_call_permissions: list) -> bool:
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

    def create_call_queue(self,
                          name: str,
                          first_name: str,
                          last_name: str,
                          phone_number: Optional[str],
                          extension: Optional[str],
                          call_policies: dict,
                          queue_settings: dict,
                          language: Optional[str] = None,
                          time_zone: Optional[str] = None,
                          allow_agent_join: Optional[bool] = False,
                          allow_did_for_outgoing_calls: Optional[bool] = False,
                          ):
        """ Create a new Call Queue at the Location

        Args:
            name (str): The name of the Call Queue
            first_name (str): The first name of the Call Queue in the directory and for Caller ID
            last_name (str): The last name of the Call Queue in the directory and for Caller ID
            phone_number (str, None): The DID for the Call Queue. None indicates no DID.
            extension (str, None): The extension for the Call Queue. None indicates no extension.
            call_policies (dict): The callPolicies dict for the Call Queue. Because the format of this dict changes
                often, see the documentation at developer.webex.com for values.
            queue_settings (dict): The queueSettings dict for the Call Queue. Because the format of this dict changes
                often, see the documentation at developer.webex.com for values.
            language (str, optional): The language code (e.g. 'en_us') for the Call Queue. Defaults to the
                announcement_language of the Location.
            time_zone (str, optional): The time zone (e.g. 'America/Phoenix') for the Call Queue. Defaults to the
                time_zone of the Location.
            allow_agent_join (bool, optional): Whether to allow agents to join/unjoin the Call Queue. Default False.
            allow_did_for_outgoing_calls (bool, optional): Whether to allow the Call Queue DID to be use for
                outgoing calls. Default False.

        Returns:
            CallQueue: The created CallQueue instance

        Raises:
            ValueError: Raised when phone_number and extension are both None. One or both is required.

        """
        log.info(f"Creating Call Queue at Location {self.name} with name: {name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        # Get some values if they weren't passed
        if phone_number is None and extension is None:
            raise ValueError("phone_number and/or extension are required")
        if time_zone is None:
            log.debug(f"Using Location time_zone {self.time_zone}")
            time_zone = self.time_zone
        if language is None:
            log.debug(f"Using Location announcement_language {self.announcement_language}")
            language = self.announcement_language

        payload = {
            "name": name,
            "firstName": first_name,
            "lastName": last_name,
            "extension": extension,
            "phoneNumber": phone_number,
            "callPolicies": call_policies,
            "queueSettings": queue_settings,
            "timeZone": time_zone,
            "languageCode": language,
            "allowAgentJoinEnabled": allow_agent_join,
            "phoneNumberForOutgoingCallsEnabled": allow_did_for_outgoing_calls
        }
        response = webex_api_call("post", f"v1/telephony/config/locations/{self.id}/queues",
                                  payload=payload,
                                  params={'orgId': self._parent.id})
        new_queue_id = response['id']

        # Get the details of the new Queue
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.id}/queues/{new_queue_id}")
        new_queue = CallQueue(self,
                              id=response['id'],
                              name=response['name'],
                              location=self,
                              phone_number=response.get('phoneNumber', ''),
                              extension=response.get('extension', ''),
                              enabled=response['enabled'],
                              get_config=False
                              )
        return new_queue

    def create_auto_attendant(self,
                              name: str,
                              first_name: str,
                              last_name: str,
                              phone_number: Optional[str],
                              extension: Optional[str],
                              business_hours_schedule: str,
                              holiday_schedule: Optional[str],
                              business_hours_menu: dict,
                              after_hours_menu: dict,
                              extension_dialing_scope: str = "GROUP",
                              name_dialing_scope: str = "GROUP",
                              language: Optional[str] = None,
                              time_zone: Optional[str] = None
                              ):
        log.info(f"Creating Auto Attendant at Location {self.name} with name: {name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        # Get some values if they weren't passed
        if phone_number is None and extension is None:
            raise ValueError("phone_number and/or extension are required")
        if time_zone is None:
            log.debug(f"Using Location time_zone {self.time_zone}")
            time_zone = self.time_zone
        if language is None:
            log.debug(f"Using Location announcement_language {self.announcement_language}")
            language = self.announcement_language

        payload = {
            "name": name,
            "firstName": first_name,
            "lastName": last_name,
            "extension": extension,
            "phoneNumber": phone_number,
            "timeZone": time_zone,
            "languageCode": language,
            "businessSchedule": business_hours_schedule,
            "holidaySchedule": holiday_schedule,
            "extensionDialing": extension_dialing_scope,
            "nameDialing": name_dialing_scope,
            "businessHoursMenu": business_hours_menu,
            "afterHoursMenu": after_hours_menu
        }
        response = webex_api_call("post", f"v1/telephony/config/locations/{self.id}/autoAttendants",
                                  payload=payload,
                                  params={'orgId': self._parent.id})
        new_aa_id = response['id']
        this_aa = AutoAttendant(self, self, new_aa_id, name)
        return this_aa

    def create_hunt_group(self,
                          name: str,
                          first_name: str,
                          last_name: str,
                          phone_number: Optional[str],
                          extension: Optional[str],
                          call_policies: dict,
                          enabled: bool = True,
                          language: Optional[str] = None,
                          time_zone: Optional[str] = None
                          ):
        log.info(f"Creating Hunt Group at Location {self.name} with name: {name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        # Get some values if they weren't passed
        if phone_number is None and extension is None:
            raise ValueError("phone_number and/or extension are required")
        if time_zone is None:
            log.debug(f"Using Location time_zone {self.time_zone}")
            time_zone = self.time_zone
        if language is None:
            log.debug(f"Using Location announcement_language {self.announcement_language}")
            language = self.announcement_language

        payload = {
            "name": name,
            "firstName": first_name,
            "lastName": last_name,
            "extension": extension,
            "phoneNumber": phone_number,
            "timeZone": time_zone,
            "languageCode": language,
            "callPolicies": call_policies
        }
        response = webex_api_call("post", f"v1/telephony/config/locations/{self.id}/huntGroups",
                                  payload=payload,
                                  params={'orgId': self._parent.id})
        new_hg_id = response['id']
        # Get the details of the new Hunt Group
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.id}/huntGroups/{new_hg_id}")
        new_hg = HuntGroup(self,
                           id=response['id'],
                           name=response['name'],
                           location=self.id,
                           phone_number=response.get('phoneNumber', ''),
                           extension=response.get('extension', ''),
                           enabled=response['enabled'],
                           config=False
                           )
        return new_hg

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
    def pickup_groups(self) -> PickupGroupList:
        """ :py:class:`PickupGroupList` list of :py:class:`PickupGroup`s for this Location """
        log.info(f"Getting Pickup Groups for Location {self.name}")
        if self.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        if self._pickup_groups is None:
            self._pickup_groups = PickupGroupList(self)
        return self._pickup_groups

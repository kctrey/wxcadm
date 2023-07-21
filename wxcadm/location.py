from __future__ import annotations

from wxcadm import log
from .location_features import LocationSchedule
from .common import *


class Location:
    def __init__(self, parent: Org, location_id: str,
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def spark_id(self):
        """The ID used by all of the underlying services."""
        return decode_spark_id(self.id)

    @property
    def hunt_groups(self):
        """List of HuntGroup instances for this Location"""
        my_hunt_groups = []
        for hg in self._parent.hunt_groups:
            if hg.location == self.id:
                my_hunt_groups.append(hg)
        return my_hunt_groups

    @property
    def announcements(self):
        """ List of :py:class:`Announcement` instances for the Location

        .. note::
            This does not include announcements built at the Organization level

        """
        annc_list = self._parent.announcements.get_by_location_id(self.id)
        return annc_list

    @property
    def auto_attenndants(self):
        """ List of AutoAttendant instances for this Location"""
        aa_list = []
        for aa in self._parent.auto_attendants:
            if aa.location == self.id:
                aa_list.append(aa)
        return aa_list

    @property
    def call_queues(self):
        """List of CallQueue instances for this Location"""
        my_call_queues = []
        for cq in self._parent.call_queues:
            if cq.location_id == self.id:
                my_call_queues.append(cq)
        return my_call_queues

    @property
    def numbers(self):
        """ All the Numbers for the Location

        Returns:
            list[dict]: List of dict containing information about each number

        """
        log.info("Getting Location numbers from Webex")
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


from __future__ import annotations

import base64
from collections import UserList

import requests
import re
import wxcadm
from typing import Union, Optional
from wxcadm import log
from .common import *
from .common import _url_base
from .exceptions import *
from .cpapi import CPAPI
from .location import Location, LocationList
from .location_features import PagingGroup, VoicemailGroupList
from .auto_attendant import AutoAttendantList
from .call_queue import CallQueueList, OrgQueueSettings
from .hunt_group import HuntGroupList
from .webhooks import Webhooks
from .person import UserGroups, Person, PersonList
from .applications import WebexApplications
from .announcements import AnnouncementList, PlaylistList
from .workspace import Workspace, WorkspaceList
from .call_routing import CallRouting, TranslationPatternList
from .reports import ReportList
from .calls import Calls
from .device import DeviceList, SupportedDeviceList
from .recording import ComplianceAnnouncementSettings, RecordingList, OrgRecordingVendorSelection
from .jobs import NumberManagementJobList, UserMoveJobList, RebuildPhonesJobList
from .virtual_line import VirtualLineList, VirtualLine
from .dect import DECTNetworkList
from .number import NumberList
from .events import AuditEventList
from .monitoring import MonitoringList
from .location_features import CallParkExtension


class Org:
    def __init__(self,
                 name: str,
                 id: str,
                 parent: wxcadm.Webex = None,
                 xsi: bool = False,
                 **kwargs
                 ):
        """Initialize an Org instance

        Args:
            name (str): The Organization name
            id (str): The Webex ID of the Organization
            parent (Webex, optional): The parent Webex instance that owns this Org.
            xsi (bool, optional): Whether to get the XSI Endpoints for the Org. Default False.

        Returns:
            Org: This instance of the Org class
        """

        # Instance attrs
        self._numbers = None
        self._paging_groups = None
        self._parent = parent
        self.name: str = name
        'The name of the Organization'
        self.id: str = id
        '''The Webex ID of the Organization'''
        self.xsi: dict = {}
        """The XSI details for the Organization"""
        self._params: dict = {"orgId": self.id}
        self._licenses: Optional[WebexLicenseList] = None
        self._devices: Optional[list] = None
        self._usergroups: Optional[list] = None
        self._roles: Optional[dict] = None
        self._announcements: Optional[AnnouncementList] = None
        self._hunt_groups: Optional[HuntGroupList] = None
        self._call_queues: Optional[CallQueueList] = None
        self._workspaces: Optional[WorkspaceList] = None
        self._people: Optional[PersonList] = None
        self._auto_attendants: Optional[AutoAttendantList] = None
        self._locations: Optional[LocationList] = None
        self._compliance_announcement_settings: Optional[ComplianceAnnouncementSettings] = None
        self._number_management_jobs = None
        self._user_move_jobs = None
        self._rebuild_phones_jobs = None
        self._virtual_lines = None
        self._dect_networks = None
        self._voicemail_groups = None
        self._numbers = None
        self._supported_devices = None
        self._translation_patterns = None
        self._all_monitoring = None
        self._playlists = None

        self.call_routing = CallRouting(self)
        """ The :py:class:`CallRouting` instance for this Org """
        self._reports = None

        # Set the Authorization header based on how the instance was built
        self._headers = parent.headers

        # Create a CPAPI instance for CPAPI work
        self._cpapi = CPAPI(self, self._parent._access_token)

        if xsi:
            self.get_xsi_endpoints()


    @property
    def numbers(self):
        """ :class:`NumberList` of all numbers for the Org """
        if self._numbers is None:
            self._numbers = NumberList(self)
        return self._numbers

    @property
    def voicemail_groups(self):
        """ :class:`VoicemailGroupList of all Voicemail Groups for the Org """
        if self._voicemail_groups is None:
            self._voicemail_groups = VoicemailGroupList(self)
        return self._voicemail_groups

    @property
    def reports(self) -> ReportList:
        """ :class:`~.reports.ReportList` of all Reports for the Org """
        if self._reports is None:
            self._reports = ReportList(self)
        return self._reports

    @property
    def spark_id(self):
        """ The decoded "Spark ID" of the Org ID"""
        org_id_bytes = base64.b64decode(self.id + "===")
        spark_id = org_id_bytes.decode("utf-8")
        return spark_id

    @property
    def org_id(self):
        """ The Org ID of the Org. :attr:`id` should be used in most cases. :attr:`org_id` just simplifies API calls """
        return self.id

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def compliance_announcement_settings(self):
        """ The Call Recording Compliance Announcement settings for the Org

        Returns:
            ComplianceAnnouncementSettings: The settings for the Org

        """
        if self._compliance_announcement_settings is None:
            response = webex_api_call('get', 'v1/telephony/config/callRecording/complianceAnnouncement',
                                      params={'orgId': self.id})
            self._compliance_announcement_settings = ComplianceAnnouncementSettings(self, **response)
        return self._compliance_announcement_settings

    @property
    def auto_attendants(self):
        """ :class:`.auto_attendant.AutoAttendantList` of all Auto Attendants for the Org """
        if self._auto_attendants is None:
            self._auto_attendants = AutoAttendantList(self)
        return self._auto_attendants

    @property
    def workspaces(self):
        """ :class:`.workspace.WorkspacesList` instance for the Org """
        if self._workspaces is None:
            self._workspaces = WorkspaceList(parent=self)
        return self._workspaces

    @property
    def licenses(self):
        """ :class:`WebexLicenseList` for the Organization """
        if self._licenses is None:
            self._licenses = WebexLicenseList(self)
        return self._licenses

    @property
    def locations(self):
        """ :class:`~.location.LocationList` for the Organization """
        if self._locations is None:
            self._locations = LocationList(self)
        return self._locations

    @property
    def dect_networks(self):
        """ :class:`~.dect.DECTNetworkList` for the Organization"""
        if self._dect_networks is None:
            self._dect_networks = DECTNetworkList(self)
        return self._dect_networks

    @property
    def roles(self):
        """ A dict of user roles with the ID as the key and the Role name as the value """
        if self._roles is None:
            roles = {}
            response = webex_api_call('get', 'v1/roles', params={'orgId': self.id})
            for role in response:
                roles[role['id']] = role['name']
            self._roles = roles
        return self._roles

    @property
    def number_management_jobs(self):
        """ :class:`NumberManagementJobList` for this Organization """
        if self._number_management_jobs is None:
            self._number_management_jobs = NumberManagementJobList(self)
        return self._number_management_jobs

    @property
    def user_move_jobs(self):
        """ :class:`UserMoveJobList` for this Organization """
        if self._user_move_jobs is None:
            self._user_move_jobs = UserMoveJobList(self)
        return self._user_move_jobs

    @property
    def rebuild_phones_jobs(self):
        """ :class:`RebuildPhonesJobList` for this Organization """
        if self._rebuild_phones_jobs is None:
            self._rebuild_phones_jobs = RebuildPhonesJobList(self)
        return self._rebuild_phones_jobs

    @property
    def queue_settings(self):
        """ :class:`QueueSettingsList` for this Organization """
        response = webex_api_call("get", "v1/telephony/config/queues/settings", params={'orgId': self.id})
        response['org'] = self
        return OrgQueueSettings.from_dict(response)

    @property
    def paging_groups(self):
        """ All the PagingGroups for the Org

        Returns:
            list[PagingGroup]: The PagingGroup instances for this Org

        """
        if not self._paging_groups:
            paging_groups = []
            response = webex_api_call("get", "v1/telephony/config/paging", headers=self._headers, params=self._params)
            for entry in response['locationPaging']:
                location = self.locations.get(id=entry['locationId'])
                this_pg = PagingGroup(location, entry['id'], entry['name'])
                paging_groups.append(this_pg)
            self._paging_groups = paging_groups
        return self._paging_groups

    @property
    def supported_devices(self) -> SupportedDeviceList:
        """ The :class:`SupportedDeviceList` of :class:`SupportedDevice` models for this Org """
        if self._supported_devices is None:
            self._supported_devices = SupportedDeviceList()
        return self._supported_devices

    @property
    def webhooks(self):
        """ The :py:class:`Webhooks` list with the :py:class:`Webhook` instances for the Org"""
        return Webhooks()

    @property
    def usergroups(self):
        """ The :py:class:`UserGroups` list with the :py:class:`UserGroup` instances for the Org """
        return UserGroups(parent=self)

    @property
    def applications(self):
        """ The :py:class:`WebexApplications` list with the :py:class:`WebexApplication` instances for this Org """
        return WebexApplications(parent=self)

    @property
    def virtual_lines(self):
        """ The :class:`VirtualLineList` list with the :class:`VirtualLine` instances for this Org """
        if self._virtual_lines is None:
            self._virtual_lines = VirtualLineList(self)
        return self._virtual_lines

    @property
    def announcements(self):
        """ The :py:class:`~wxcadm.announcements.AnnouncementList` list with the :py:class:`Announcement` instances
        for this Org"""
        if self._announcements is None:
            self._announcements = AnnouncementList(parent=self)
        return self._announcements

    @property
    def playlists(self) -> PlaylistList:
        """ The :py:class:`~wxcadm.playlists.PlaylistList` list with the :class:`Playlist` instances for this Org"""
        if self._playlists is None:
            self._playlists = PlaylistList(parent=self)
        return self._playlists

    @property
    def calls(self):
        """ The :py:class:`Calls` instance for this Org"""
        return Calls(parent=self)

    def get_paging_group(self, id: str = None, name: str = None, spark_id: str = None):
        """ Get the PagingGroup instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Paging
        Groups will be searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method
        will raise an Exception.

        Args:
            id (str, optional): The PagingGroup ID to find
            name (str, optional): The PagingGroup Name to find
            spark_id (str, optional): The Spark ID to find

        Returns:
            PagingGroup: The PagingGroup instance correlating to the given search argument. None is returned if no
            Location is found.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        for pg in self.paging_groups:
            if pg.id == id:
                return pg
        for pg in self.paging_groups:
            if pg.name == name:
                return pg
        for pg in self.paging_groups:
            if pg.spark_id == spark_id:
                return pg
        return None

    def get_number_assignment(self, number: str):
        """ Get the object to which a phone number is assigned.

        A number may be assigned to a Person, a Workspace, or any number of things. If the number is assigned to a
        known class, that instance will be returned. If not, the `owner` value from the API will be returned. If the
        number is found but not assigned, None will be returned.

        .. note::
            Since Webex sometimes uses E.164 formatting and other times uses the national format, the match is made
            using a partial match. If the method is passed a national-format number, but stored in Webex as an E164
            number, a match will be made.

        Args:
            number (str): The phone number to search for.

        """
        log.info(f"get_number_assignment({number})")
        for num in self.numbers:
            if num.phone_number is not None:
                if number in num.phone_number:
                    log.debug(f"Found match: {num}")
                    log.debug("Finding owner")
                    return num.owner
        return None

    def get_all_monitoring(self) -> dict:
        """ Returns a dict of all Users and Workspaces that are being monitored. The User (Person) or Workspace is the
        dict key and the Users and Workspaces that are monitoring that key are a list.

        Returns:
            dict: A dict in the format ``{ 'people': { person: [] }, 'workspaces': { person: [] } }``

        """
        if self._all_monitoring is None:
            all_monitoring = {'people': {}, 'workspaces': {}, 'park_extensions': {}, 'virtual_lines': {}}
            for person in self.people.webex_calling():
                monitoring: MonitoringList  = person.monitoring
                for element in monitoring.monitored_elements:
                    if isinstance(element, CallParkExtension):
                        if element.id not in all_monitoring['park_extensions'].keys():
                            all_monitoring['park_extensions'][element.id] = []
                        all_monitoring['park_extensions'][element.id].append(person)
                    if isinstance(element, VirtualLine):
                        if element.id not in all_monitoring['virtual_lines'].keys():
                            all_monitoring['virtual_lines'][element.id] = []
                        all_monitoring['virtual_lines'][element.id].append(person)
                    if isinstance(element, Person):
                        if element.id not in all_monitoring['people'].keys():
                            all_monitoring['people'][element.id] = []
                        all_monitoring['people'][element.id].append(person)
                    if isinstance(element, Workspace):
                        if element.id not in all_monitoring['workspaces'].keys():
                            all_monitoring['workspaces'][element.id] = []
                        all_monitoring['workspaces'][element.id].append(person)
            for workspace in self.workspaces.webex_calling():
                monitoring:monitoring = workspace.monitoring
                for element in monitoring.monitored_elements:
                    if isinstance(element, CallParkExtension):
                        if element.id not in all_monitoring['park_extensions'].keys():
                            all_monitoring['park_extensions'][element.id] = []
                        all_monitoring['park_extensions'][element.id].append(workspace)
                    if isinstance(element, VirtualLine):
                        if element.id not in all_monitoring['virtual_lines'].keys():
                            all_monitoring['virtual_lines'][element.id] = []
                        all_monitoring['virtual_lines'][element.id].append(workspace)
                    if isinstance(element, Person):
                        if element.id not in all_monitoring['people'].keys():
                            all_monitoring['people'][element.id] = []
                        all_monitoring['people'][element.id].append(workspace)
                    if isinstance(element, Workspace):
                        if element.id not in all_monitoring['workspaces'].keys():
                            all_monitoring['workspaces'][element.id] = []
                        all_monitoring['workspaces'][element.id].append(workspace)
            self._all_monitoring = all_monitoring
        return self._all_monitoring

    def get_workspace_devices(self, workspace: Optional[Workspace] = None):
        """ Get Webex Calling Workspaces and their associated Devices

        When called without an argument, a list of Workspace instances is returned. Devices associated with each
        Workspace can be accessed with the .devices attribute of each Workspace. If there are no Devices assigned
        to a Workspace, .devices will return an empty list (i.e. []).

        When called with a ``workspace`` argument, which is a Workspace instance, the Devices for that Workspace will
        be returned as a list of Device instances.

        Args:
            workspace (Workspace, optional): A Workspace instance to show devices for

        Returns:
            list: Either a list of :py:class:`Workspace` or a list of :py:class:`Device`, depending on the argument

        """
        # TODO: For now, until the Workspaces API works for all WxC Workspaces, we use the .numbers as the key
        if workspace is not None:
            return workspace.devices
        workspaces = []
        for number in self.numbers:
            if 'owner' in number.keys():
                if isinstance(number['owner'], dict) and number['owner']['type'] == 'PLACE':
                    print(number)
                    ws_config = {'displayName': number['owner']['firstName']}
                    workspace = Workspace(self, id=number['owner']['id'], config=ws_config)
                    if number['owner']['lastName'] != '.':
                        workspace.name += f" {number['owner']['lastName']}"
                    workspace.location = number['location']
                    workspaces.append(workspace)
        return workspaces

    @property
    def devices(self):
        """All the Device instances for the Org

        Returns:
            DeviceList: List of all Device instances

        """
        if self._devices is None:
            self._devices = DeviceList(self)
        return self._devices

    def get_device_by_id(self, device_id: str):
        """ Get the :py:class:`Device` instance for a specific Device ID

        Args:
            device_id (str): The Device ID to return

        Returns:
            Device: The Device instance. False is returned if no match is found.

        """
        log.debug(f"Finding device with ID {device_id}")
        for device in self.devices:
            if device.id == device_id or decode_spark_id(device.id).split("/")[-1] == \
                    decode_spark_id(device_id).split("/")[-1]:
                return device
        return False

    @property
    def people(self):
        """ :py:class:`PersonList` wth all the :py:class:`Person` instances for the Organization """
        if self._people is None:
            self._people = PersonList(self)
        return self._people

    def get_person_by_id(self, id: str):
        """Get the Person instance associated with a given ID

        .. deprecated:: 4.0.0
            Use :py:meth:`Org.people.get_by_id()` instead

        Args:
            id (str): The Webex ID of the Person to look for.

        Returns:
            Person: The Person instance. If no match is found, None is returned

        """
        return self.people.get_by_id(id)

    @property
    def wxc_licenses(self):
        """Get only the Webex Calling licenses from the Org.licenses attribute

        .. deprecated:: 4.5.0

            This method is now deprecated in favor of :py:meth:`Org.licenses.webex_calling()` and will be removed
            in a future release.

        Returns:
            list[str]: The license IDs for each Webex Calling license

        """
        license_list = []
        for license in self.licenses:
            if license.wxc_license:
                license_list.append(license)
        return license_list

    def get_wxc_person_license(self):
        """Get the Webex Calling - Professional license ID

        .. deprecated:: 4.5.0

            This method is now deprecated due to the new :attr:`Org.licenses` property which returns a
            :class:`WebexLicenseList`. Because there may not be only a single Person license, the developer should
            introduce the logic to find the appropriate license or allow the class to pick one automatically.

        Returns:
            str: The License ID

        """
        log.info("__get_wxc_person_license started to find available Professional license")
        for license in self.licenses:
            if license.wxc_type.lower() == "person":
                return license
        raise LicenseError("No Webex Calling Professional license found")

    def get_wxc_standard_license(self):
        """ Get the Webex Calling - Basic license ID

        .. deprecated:: 4.5.0

            This method is now deprecated due to the new :attr:`Org.licenses` property which returns a
            :class:`WebexLicenseList`. Because there may not be only a single Standard license, the developer should
            introduce the logic to find the appropriate license or allow the class to pick one automatically.

        Returns:
            str: The License ID

        """
        log.info("__get_wxc_standard_license started to find available Basic license")
        for license in self.licenses:
            if license.wxc_type.lower() == "standard":
                return license
        raise LicenseError("No Webex Calling Professional license found")

    def create_person(self, email: str,
                      location: Union[str, Location],
                      licenses: list = None,
                      calling: bool = True,
                      messaging: bool = True,
                      meetings: bool = True,
                      phone_number: str = None,
                      extension: str = None,
                      first_name: str = None,
                      last_name: str = None,
                      display_name: str = None,
                      ):
        """Create a new user in Webex.

        .. deprecated:: 4.0.0
            Use :py:meth:`Org.people.create()` instead.

        Args:
            email (str): The email address of the user
            location (Location): The Location instance to assign the user to. Also accepts the Location ID as a string
            licenses (list, optional): List of license IDs to assign to the user. Use this when the license IDs
                are known. To have the license IDs determined dynamically, use the `calling`, `messaging` and
                'meetings` parameters.
            calling (bool, optional): BETA - Whether to assign Calling licenses to the user. Defaults to True.
            messaging (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            meetings (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            phone_number (str, optional): The phone number to assign to the user.
            extension (str, optional): The extension to assign to the user
            first_name (str, optional): The user's first name. Defaults to empty string.
            last_name (str, optional): The users' last name. Defaults to empty string.
            display_name (str, optional): The full name of the user as displayed in Webex. If first name and last name
                are passed without display_name, the display name will be the concatenation of first and last name.

        Returns:
            Person: The Person instance of the newly-created user.

        """
        log.info(f"Creating new user: {email}")
        if (first_name or last_name) and display_name is None:
            log.debug("No display_name provided. Setting default.")
            display_name = f"{first_name} {last_name}"

        # Find the license IDs for each requested service, unless licenses was passed
        if not licenses:
            log.debug("No licenses specified. Finding licenses.")
            licenses = []
            if calling:
                log.debug("Calling requested. Finding Calling licenses.")
                calling_license = self.licenses.get_assignable_license('professional')
                log.debug(f"Using Calling License: {calling_license.name} ({calling_license.id})")
                licenses.append(calling_license.id)
            if messaging:
                pass
            if meetings:
                pass

        # Build the payload to send to the API
        log.debug("Building payload.")
        if isinstance(location, Location):
            location_id = location.id
        else:
            location_id = location
        payload = {"emails": [email], "locationId": location_id, "orgId": self.id, "licenses": licenses}
        if phone_number is not None:
            payload["phoneNumbers"] = [{"type": "work", "value": phone_number}]
        if extension is not None:
            payload["extension"] = extension
        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if display_name is not None:
            payload["displayName"] = display_name
        log.debug(f"Payload: {payload}")
        r = requests.post(_url_base + "v1/people", headers=self._headers, params={"callingData": "true"},
                          json=payload)
        response = r.json()
        if r.status_code == 200:
            person = Person(response['id'], self, response)
            return person
        else:
            raise PutError(response['message'])

    def delete_person(self, person: Person):
        """ Delete a person

        This method deletes the person record from Webex, which removes all of their licenses, numbers, and devices.

        Args:
            person (Person): The :py:class:`Person` instance to delete

        Returns:
            bool: True on success, False otherwise

        """
        success = webex_api_call("delete", f"v1/people/{person.id}", params={'orgId': self.id})
        if success:
            self._people = []
            return True
        else:
            return False

    def get_person_by_email(self, email):
        """Get the Person instance from an email address

        .. deprecated:: 4.0.0
            Use :py:meth:`Org.people.get_by_email()` instead

        Args:
            email (str): The email of the Person to return

        Returns:
            Person: Person instance object. None in returned when no Person is found

        """
        return self.people.get_by_email(email)

    def get_xsi_endpoints(self):
        """Get the XSI endpoints for the Organization.

        Also stores them in the Org.xsi attribute.

        Returns:
            dict: Org.xsi attribute dictionary with each endpoint as an entry. None is returned if no XSI isn't enabled.

        """
        params = {"callingData": "true", **self._params}
        response = webex_api_call("get", "v1/organizations/" + self.id, headers=self._headers, params=params)
        if "xsiActionsEndpoint" in response:
            self.xsi['xsi_domain'] = response['xsiDomain']
            self.xsi['actions_endpoint'] = response['xsiActionsEndpoint']
            self.xsi['events_endpoint'] = response['xsiEventsEndpoint']
            self.xsi['events_channel_endpoint'] = response['xsiEventsChannelEndpoint']
        else:
            return None
        return self.xsi

    @property
    def call_queues(self) -> CallQueueList:
        """The Call Queues for an Organization.

        Returns:
            CallQueueList: List of CallQueue instances for the Organization

        """
        if self._call_queues is None:
            log.info("Getting Call Queues for Organization")
            self._call_queues = CallQueueList(self)
        return self._call_queues

    def get_call_queue_by_id(self, id: str):
        """ Get the :class:`CallQueue` instance with the requested ID

        .. deprecated:: 4.0.0
            Use :meth:`Org.call_queues.get()` instead

        Args:
            id (str): The CallQueue ID

        Returns:
            HuntGroup: The :class:`CallQueue` instance

        """
        log.info(f"Getting Call Queue with ID {id}")
        if not self._call_queues:
            self.call_queues
        for cq in self._call_queues:
            if cq.id == id:
                return cq
        return None

    def get_hunt_group_by_id(self, id: str):
        """ Get the :class:`HuntGroup` instance with the requested ID

        .. deprecated:: 4.0.0

            Use :meth:`Org.hunt_groups.get(id=)` instead


        Args:
            id (str): The HuntGroup ID

        Returns:
            HuntGroup: The :class:`HuntGroup` instance

        """
        if not self._hunt_groups:
            self.hunt_groups
        for hg in self._hunt_groups:
            if hg.id == id:
                return hg
        return None

    @property
    def hunt_groups(self) -> HuntGroupList:
        """The :class:`HuntGroupList` for the Organization.

        Returns:
            HuntGroupList: List of :class:`HuntGroup` instances for the Organization

        """
        if self._hunt_groups is None:
            log.info("Getting Hunt Groups for Organization")
            self._hunt_groups = HuntGroupList(self)
        return self._hunt_groups

    @property
    def translation_patterns(self):
        """ The :class:`TranslationPatternList of Translation Patterns for the Org and all Locations """
        if self._translation_patterns is None:
            self._translation_patterns = TranslationPatternList(self)
        return self._translation_patterns

    @property
    def recording_vendor(self):
        """The :class:`OrgRecordingVendorSelection` instance for the Organization"""
        return OrgRecordingVendorSelection(self)

    @property
    def recorded_people(self):
        """Return all the People within the Organization who have Call Recording enabled

        .. deprecated:: 4.0.0
            Use :py:meth:`Org.people.recorded()` instead

        Returns:
            list[Person]: List of Person instances that have Call Recording enabled

        """
        return self.people.recorded(True)

    def get_license_name(self, license_id: str):
        """Gets the name of a license by its ID

        Args:
            license_id (str): The License ID

        Returns:
            str: The License name. None if not found.

        """
        for license in self.licenses:
            if license.id == license_id:
                return license.name
        return None

    def get_audit_events(self, start: str, end: str) -> AuditEventList:
        """ Get a list of Admin Audit Events for the Organization

        Args:
            start (str): The first date/time in the report, in the format `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS.000Z`
            end (str): The first date/time in the report, in the format `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS.000Z`

        Returns:
            AuditEventList: The :class:`AuditEventList` of all matching events

        """
        # Normalize the start and end if only the date was provided
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", start):
            start = start + "T00:00:00.000Z"
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", end):
            end = end + "T23:59:59.999Z"

        event_list = AuditEventList(self, start, end)
        return event_list

    def get_recordings(self, **kwargs):
        return RecordingList(parent=self, **kwargs)


class WebexLicenseList(UserList):
    def __init__(self, org: wxcadm.Org):
        """ The list of Webex licenses within the Org """
        super().__init__()
        self.org = org
        self.data: list[WebexLicense] = []
        api_response = webex_api_call("get", f"v1/licenses",
                                      params={'orgId': self.org.id})
        for license in api_response:
            self.data.append(WebexLicense(org, license))
        # Add the subscriptions to a list that is available to use for assignment.
        # The idea is that a developer could limit the subscriptions if they wanted
        self.assignable_subscriptions: list = \
            list({license.subscription for license in self.data if license.subscription is not None})
        """ List of assignable subscriptions """

    def refresh(self):
        """ Refresh the list of licenses and their usage """
        self.data = []
        api_response = webex_api_call("get", f"v1/licenses",
                                      params={'orgId': self.org.id})
        new_licenses_data = {license['id']: license for license in api_response}
        existing_license: WebexLicense
        for existing_license in self.data:
            if existing_license.id in new_licenses_data.keys():
                existing_license.total = new_licenses_data[existing_license.id]['totalUnits']
                existing_license.consumed = new_licenses_data[existing_license.id]['consumedUnits']
                existing_license.consumed_by_users = new_licenses_data[existing_license.id]['consumedByUsers']
                existing_license.consumed_by_workspaces = new_licenses_data[existing_license.id]['consumedByWorkspaces']
                del new_licenses_data[existing_license.id]

        for license_data in new_licenses_data.values():
            self.data.append(WebexLicense(self.org, license_data))

    def get_assignable_license(self, license_type: str, ignore_license_overage: bool = False) -> WebexLicense:
        """
        Fetches an assignable Webex license of a specified type.

        This method retrieves a Webex license based on the specified license type and whether
        license overages should be ignored. The function first attempts to find available licenses
        that match the specified criteria. If no available licenses exist, it searches for licenses
        that would cause an overage, depending on the value of `ignore_license_overage`. The function
        ensures the selected license belongs to an assignable subscription or has no subscription.

        Args:
            license_type (str): The type of license to retrieve. Valid valies are 'professional', 'workspace',
                'standard' or 'hotdesk'

            ignore_license_overage (bool, optional): Whether to override license overage conditions
                when no available license exists. Defaults to False.

        Returns:
            WebexLicense: The assignable license that matches the specified criteria.

        Raises:
            wxcadm.LicenseOverageError: If license overage is detected and `ignore_license_overage` is False.
            wxcadm.NotSubscribedForLicenseError: If the account is not subscribed for licenses of the
                specified type.
        """
        if len(self.webex_calling(type=license_type, available_licenses_only=True)) == 0:
            # No "available" licenses. Find one that would cause an overage
            if len(self.webex_calling(type=license_type, available_licenses_only=False)) >= 1:
                if ignore_license_overage:
                    # Make sure we only pick from a subscription in the self.assignable_subscriptions list
                    for license in self.webex_calling(type=license_type, available_licenses_only=False):
                        if license.subscription in self.assignable_subscriptions or license.subscription is None:
                            return license
                    raise LicenseError(f"No available licenses of type {license_type} found in assignable subscriptions")
                else:
                    raise wxcadm.LicenseOverageError(
                        """License overage detected. Override with 'ignore_license_overage=True' or assign a 
                        different license""")
            else:
                raise wxcadm.NotSubscribedForLicenseError(f"No licenses available for {license_type}")
        else:
            for license in self.webex_calling(type=license_type, available_licenses_only=True):
                if license.subscription in self.assignable_subscriptions or license.subscription is None:
                    return license
            raise LicenseError(f"No available licenses of type {license_type} found in assignable subscriptions")

    def get(self,
            id: Optional[str] = None,
            name: Optional[str] = None,
            subscription: Optional[str] = None) -> Optional[Union[wxcadm.WebexLicense, list[wxcadm.WebexLicense]]]:
        """
        Retrieve a Webex license by its ID, name, or subscription
    
        Args:
            id (Optional[str]): The ID of the Webex license to retrieve.
            name (Optional[str]): The name of the Webex license to retrieve..
            subscription (Optional[str]): The subscription of the Webex licenses to retrieve.
    
        Returns:
            WebexLicense: The Webex license that matches the provided ID or name, if only one is found.
            list[WebexLicense]: A list of Webex licenses that matches the provided ID or name, if multiple matches are found.
        """
        matches = []
        for entry in self.data:
            if id is not None and entry.id == id:
                return entry
            if name is not None and entry.name == name:
                matches.append(entry)
            if entry.subscription is not None:
                if subscription is not None and entry.subscription.lower() == subscription.lower():
                    matches.append(entry)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return matches
        else:
            return None

    def webex_calling(self, type: str = 'all', available_licenses_only: bool = False) -> list[WebexLicense]:
        """ Return only Webex Calling licenses

        Params:
            type (str, optional): The type of licenses to return. Options are: 'all',
            'professional', 'workspace', 'hotdesk', or 'standard'. Default is all.

            available_licenses_only (bool, optional): Whether to only return subscriptions with available, unassigned
            licenses. Default is False.

        Returns:
            list[WebexLicense]: List of Webex Calling Licenses

        """
        return_list = []
        if type.lower() == 'all':
            for license in self.data:
                if license.wxc_license is True:
                    return_list.append(license)
        elif type.lower() == 'professional':
            for license in self.data:
                if license.wxc_type == 'professional':
                    return_list.append(license)
        elif type.lower() == 'workspace':
            for license in self.data:
                if license.wxc_type == 'workspace':
                    return_list.append(license)
        elif type.lower() == 'hotdesk':
            for license in self.data:
                if license.wxc_type == 'hotdesk':
                    return_list.append(license)
        elif type.lower() == 'standard':
            for license in self.data:
                if license.wxc_type == 'standard':
                    return_list.append(license)

        if available_licenses_only is True:
            available_list: list[WebexLicense] = []
            for license in return_list:
                if license.consumed < license.total:
                    available_list.append(license)
            return available_list
        else:
            return return_list

class WebexLicense:
    def __init__(self, org: Org, data: dict):
        self.org = org
        self.name: str = data.get('name', 'Unknown')
        """ The license name"""
        self.id: str = data.get('id')
        """ The license ID"""
        self.total: int = data.get('totalUnits', 0)
        """ The total number of licenses in the subscription"""
        self.consumed: int = data.get('consumedUnits', 0)
        """ The number of licenses that have been consumed"""
        self.consumed_by_users: int = data.get('consumedByUsers', 0)
        """ The number of licenses that have been consumed by users"""
        self.consumed_by_workspaces: int = data.get('consumedByWorkspaces', 0)
        """ The number of licenses that have been consumed by workspaces"""
        self.subscription: Optional[str] = data.get('subscriptionId', None)
        """ The subscription ID"""
        self.wxc_license: bool = False
        """ True if this is a Webex Calling license"""
        self.wxc_type: Optional[str] = None
        """ The type of Webex Calling license"""

        if "Webex Calling" in self.name:
            self.wxc_license = True
            if "Professional" in self.name:
                self.wxc_type = "professional"
            elif "Workspace" in self.name:
                self.wxc_type = "workspace"
            elif "Hot desk only" in self.name:
                self.wxc_type = "hotdesk"
            elif "Basic" in self.name:
                self.wxc_type = "standard"

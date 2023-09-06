from __future__ import annotations

import base64
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
from .location_features import PagingGroup
from .auto_attendant import AutoAttendantList
from .call_queue import CallQueueList
from .hunt_group import HuntGroupList
from .webhooks import Webhooks
from .person import UserGroups, Person, PersonList
from .applications import WebexApplications
from .announcements import AnnouncementList
from .workspace import Workspace, WorkspaceList, WorkspaceLocationList
from .call_routing import CallRouting
from .reports import Reports
from .calls import Calls
from .device import Device


class Org:
    def __init__(self,
                 name: str,
                 id: str,
                 parent: wxcadm.Webex = None,
                 locations: bool = False,
                 hunt_groups: bool = False,
                 call_queues: bool = False,
                 xsi: bool = False,
                 ):
        """Initialize an Org instance

        Args:
            name (str): The Organization name
            id (str): The Webex ID of the Organization
            parent (Webex, optional): The parent Webex instance that owns this Org.
            locations (bool, optional): Whether to get all Locations for the Org. Default True.
            hunt_groups (bool, optional): Whether to get all Hunt Groups for the Org. Default False.
            call_queues (bool, optional): Whether to get all Call Queues for the Org. Default False.
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
        self._licenses: Optional[list] = None
        self._wxc_licenses: Optional[list] = None
        self._devices: Optional[list] = None
        """A list of the Devce instances for this Org"""
        self._usergroups: Optional[list] = None
        self._roles: Optional[dict] = None
        self._announcements: Optional[AnnouncementList] = None
        self._hunt_groups: Optional[HuntGroupList] = None
        self._call_queues: Optional[CallQueueList] = None
        self._workspaces: Optional[WorkspaceList] = None
        self._workspace_locations: Optional[WorkspaceLocationList] = None
        self._people: Optional[PersonList] = None
        self._auto_attendants: Optional[AutoAttendantList] = None
        self._locations: Optional[LocationList] = None


        self.call_routing = CallRouting(self)
        """ The :py:class:`CallRouting` instance for this Org """
        self.reports = Reports(self)
        """ The :py:class:`Reports` instance for this Org """

        # Set the Authorization header based on how the instance was built
        self._headers = parent.headers

        # Create a CPAPI instance for CPAPI work
        self._cpapi = CPAPI(self, self._parent._access_token)

        if xsi:
            self.get_xsi_endpoints()

    @property
    def workspace_locations(self):
        """ :py:class:`WorkspaceLocationList of all :py:class:`WorkspaceLocation`s"""
        if self._workspace_locations is None:
            self._workspace_locations = WorkspaceLocationList(self)
        return self._workspace_locations

    @property
    def spark_id(self):
        """ The decoded "Spark ID" of the Org ID"""
        org_id_bytes = base64.b64decode(self.id + "===")
        spark_id = org_id_bytes.decode("utf-8")
        return spark_id

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def auto_attendants(self):
        if self._auto_attendants is None:
            self._auto_attendants = AutoAttendantList(self)
        return self._auto_attendants

    @property
    def workspaces(self):
        if self._workspaces is None:
            self._workspaces = WorkspaceList(parent=self)
        return self._workspaces

    @property
    def licenses(self):
        """ A list of all licenses for the Organization as a dictionary of names and IDs """
        if self._licenses is None:
            self._licenses = self.__get_licenses()
        return self._licenses

    @property
    def locations(self):
        if self._locations is None:
            self._locations = LocationList(self)
        return self._locations

    @property
    def roles(self):
        """ A dict of user roles with the ID as the key and the Role name as the value """
        if self._roles is None:
            roles = {}
            response = webex_api_call('get', 'v1/roles')
            for role in response:
                roles[role['id']] = role['name']
            self._roles = roles
        return self._roles

    def __get_licenses(self):
        """Gets all licenses for the Organization

        Returns:
            list: List of dictionaries containing the license name and ID

        """
        log.info("__get_licenses() started for org")
        license_list = []
        try:
            api_resp = webex_api_call("get", "v1/licenses", headers=self._headers, params=self._params)
        except APIError:
            return None
        for item in api_resp:
            if "Webex Calling" in item['name']:
                wxc_license = True
                if "Professional" in item['name']:
                    wxc_type = "person"
                elif "Workspace" in item['name']:
                    wxc_type = "workspace"
                else:
                    wxc_type = "unknown"
            else:
                wxc_license = False
                wxc_type = None
            lic = {"name": item['name'],
                   "id": item['id'],
                   "total": item['totalUnits'],
                   "consumed": item['consumedUnits'],
                   "subscription": item.get("subscriptionId", ""),
                   "wxc_license": wxc_license,
                   "wxc_type": wxc_type
                   }
            license_list.append(lic)
        return license_list

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

    def get_supported_devices(self):
        response = webex_api_call('get', f"/v1/telephony/config/supportedDevices", params={'orgId': self.id})
        return response['devices']

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
    def announcements(self):
        """ The :py:class:`~wxcadm.announcements.AnnouncementList` list with the :py:class:`Announcement` instances
        for this Org"""
        if self._announcements is None:
            self._announcements = AnnouncementList(parent=self)
        return self._announcements

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

    @property
    def numbers(self):
        """ All the Numbers for the Org

        Returns:
            list[dict]: List of dict containing information about each number

        """
        log.info("Getting Org numbers from Webex")
        response = webex_api_call("get", "v1/telephony/config/numbers", headers=self._headers, params=self._params)
        org_numbers = response['phoneNumbers']
        for num in org_numbers:
            if "owner" in num:
                if "id" in num['owner']:
                    person = self.get_person_by_id(num['owner']['id'])
                    if person is not None:
                        num['owner'] = person
                    else:
                        if num['owner']['type'].upper() == "HUNT_GROUP":
                            hunt_group = self.get_hunt_group_by_id(num['owner']['id'])
                            if hunt_group is not None:
                                num['owner'] = hunt_group
                        elif num['owner']['type'].upper() == "GROUP_PAGING":
                            paging_group = self.get_paging_group(id=num['owner']['id'])
                            if paging_group is not None:
                                num['owner'] = paging_group
                        elif num['owner']['type'].upper() == "CALL_CENTER":
                            call_queue = self.get_call_queue_by_id(num['owner']['id'])
                            if call_queue is not None:
                                num['owner'] = call_queue
                        elif num['owner']['type'].upper() == "AUTO_ATTENDANT":
                            auto_attendant = self.auto_attendants.get(id=num['owner']['id'])
                            if auto_attendant is not None:
                                num['owner'] = auto_attendant
            if "location" in num:
                location = self.locations.get(name=num['location']['name'])
                if location is not None:
                    num['location'] = location
        self._numbers = org_numbers
        return org_numbers

    def get_number_assignment(self, number: str):
        """ Get the object to which a phone number is assigned.

        A number may be assigned to a Person, a Workspace, or any number of things. If the number is assigned to a
        known class, that instance will be returned. If not, the `owner` value from the API will be returned.

        .. note::
            Since Webex sometimes uses E.164 formatting and other times uses the national format, the match is made
            using a partial match. If the method is passed a national-format number, but stored in Webex as an E164
            number, a match will be made.

        Args:
            number (str): The phone number to search for.

        """
        log.info(f"get_number_assignment({number})")
        for num in self.numbers:
            if num.get("phoneNumber", "") is not None:
                if number in num.get("phoneNumber", ""):
                    log.debug(f"Found match: {num}")
                    return num
        return None

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
            list[Device]: List of all Device instances
        """
        devices = []
        response = webex_api_call("get", "/v1/devices", params={"orgId": self.id})
        for device in response:
            this_device = Device(self, config=device)
            devices.append(this_device)
        return devices

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

    def get_location_by_name(self, name: str):
        """Get the Location instance associated with a given Location name

        .. deprecated:: 2.2.0
            Use :meth:`get_location` using the ```name``` argument instead.

        Args:
            name (str): The full name of the Location to look for. (Case sensitive)

        Returns:
            Location: The Location instance. If no match is found, None is returned

        """
        for location in self.locations:
            if location.name == name:
                return location
        return None



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

        Returns:
            list[str]: The license IDs for each Webex Calling license

        """
        if self.licenses is None:
            self.__get_licenses()
        license_list = []
        for license in self.licenses:
            if license['wxc_license']:
                license_list.append(license['id'])
        return license_list

    def get_wxc_person_license(self):
        """Get the Webex Calling - Professional license ID

        Returns:
            str: The License ID

        """
        log.info("__get_wxc_person_license started to find available license")
        for license in self.licenses:
            if license['wxc_type'] == "person":
                return license['id']
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
                meetings` parameters.
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
                log.debug(f"Licenses: {self.get_wxc_person_license()}")
                licenses.append(self.get_wxc_person_license())
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
        success = webex_api_call("delete", f"v1/people/{person.id}")
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

    def get_audit_events(self, start: str, end: str):
        """ Get the Webex Admin Audit events within the given start and end times

        Args:
            start (str): Date/time to begin records in the format ```YYY-MM-DDTHH:MM:SS.XXXZ```
            end (str): Date/time to begin records in the format ```YYY-MM-DDTHH:MM:SS.XXXZ```

        Returns:
            dict: The dict of the events is returned. If no events are found, None is returned.

        """
        params = {'from': start, 'to': end, **self._params}
        response = webex_api_call("get", "v1/adminAudit/events", headers=self._headers, params=params)
        if response:
            return response
        else:
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
    def wxc_people(self):
        """Return all the people within the Organization **who have Webex Calling**

        .. deprecated:: 4.0.0
            Use :py:meth:`Org.people.webex_calling()` instead

        Returns:
            list[Person]: List of Person instances of people who have a Webex Calling license

        """
        return self.people.webex_calling(True)

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
            if license['id'] == license_id:
                return license['name']
        return None

    def get_audit_events(self,
                         start: str, end: str,
                         actor: Optional[Person] = None) -> list[dict]:
        """ Get a list of Admin Audit Events for the Organization

        Args:
            start (str): The first date/time in the report, in the format `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS.000Z`
            end (str): The first date/time in the report, in the format `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS.000Z`
            actor (Person, optional): Only show events performed by this Person

        Returns:

        """
        # Normalize the start and end if only the date was provided
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", start):
            start = start + "T00.00.00.000Z"
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", end):
            end = end + "T23:59:59.999Z"

        if actor is not None:
            actor_id = actor.id
        else:
            actor_id = None

        params = {
            'orgId': self.id,
            'from': start,
            'to': end,
            'actorId': actor_id,
        }
        response = webex_api_call('get', '/v1/adminAudit/events', params=params)
        return response

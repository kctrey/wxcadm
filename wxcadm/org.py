from __future__ import annotations

import base64
import requests
import re
from typing import Union, Optional
from wxcadm import log
from .common import *
from .common import _url_base
from .exceptions import *
from .csdm import CSDM
from .cpapi import CPAPI
from .location import Location
from .location_features import PagingGroup, PickupGroup, HuntGroup, CallQueue, AutoAttendant
from .webhooks import Webhooks
from .person import UserGroups, Person
from .applications import WebexApplications
from .workspace import Workspace, WorkspaceLocation
from .call_routing import CallRouting
from .reports import Reports
from .calls import Calls


class Org:
    def __init__(self,
                 name: str,
                 id: str,
                 parent: Webex = None,
                 people: bool = False,
                 locations: bool = False,
                 hunt_groups: bool = False,
                 call_queues: bool = False,
                 xsi: bool = False,
                 people_list: list = None
                 ):
        """Initialize an Org instance

        Args:
            name (str): The Organization name
            id (str): The Webex ID of the Organization
            parent (Webex, optional): The parent Webex instance that owns this Org.
            people (bool, optional): Whether to get all People for the Org. Default True.
            locations (bool, optional): Whether to get all Locations for the Org. Default True.
            hunt_groups (bool, optional): Whether to get all Hunt Groups for the Org. Default False.
            call_queues (bool, optional): Whether to get all Call Queues for the Org. Default False.
            xsi (bool, optional): Whether to get the XSI Endpoints for the Org. Default False.
            people_list (list, optional): List of people, by ID or email to get instances for.

        Returns:
            Org: This instance of the Org class
        """

        # Instance attrs
        self._numbers = None
        self._paging_groups = None
        self._parent = parent
        self.call_queues: Optional[list] = None
        """The Call Queues for this Org"""
        self.hunt_groups: Optional[list] = None
        """The Hunt Groups for this Org"""
        self.pickup_groups: Optional[list] = None
        'A list of the PickupGroup instances for this Org'
        self.locations: list = []
        'A list of the Location instances for this Org'
        self.name: str = name
        'The name of the Organization'
        self.id: str = id
        '''The Webex ID of the Organization'''
        self.xsi: dict = {}
        """The XSI details for the Organization"""
        self._params: dict = {"orgId": self.id}
        self._licenses: Optional[list] = None
        self._wxc_licenses: Optional[list] = None
        self._people: list = []
        '''A list of all of the Person instances for the Organization'''
        self.workspaces: Optional[list] = None
        """A list of the Workspace instances for this Org."""
        self.workspace_locations: Optional[list] = None
        """A list of the Workspace Location instanced for this Org."""
        self._devices: Optional[list] = None
        """A list of the Devce instances for this Org"""
        self._auto_attendants: list = []
        """A list of the AutoAttendant instances for this Org"""
        self._usergroups: Optional[list] = None
        self._roles: Optional[dict] = None

        self.call_routing = CallRouting(self)
        """ The :py:class:`CallRouting` instance for this Org """
        self.reports = Reports(self)
        """ The :py:class:`Reports` instance for this Org """

        # Set the Authorization header based on how the instance was built
        self._headers = parent.headers

        # Create a CPAPI instance for CPAPI work
        self._cpapi = CPAPI(self, self._parent._access_token)

        # Create a CSDM instance for CSDM work
        self._csdm = CSDM(self, self._parent._access_token)

        if locations:
            self.get_locations()
        if xsi:
            self.get_xsi_endpoints()
        if call_queues:
            self.get_call_queues()
        if hunt_groups:
            self.get_hunt_groups()
        if people:
            self.get_people()
        if people_list:
            for person in people_list:
                self._get_person(person)

    def get_org_data(self):
        """ Get the People, Locations, Call Queues and Hunt Groups for the Org

        Returns:
            None: Doesn't return any values. Simply populates the Org attributes with the data

        """
        self.get_locations()
        self.get_call_queues()
        self.get_hunt_groups()
        self.get_people()
        return None

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
    def licenses(self):
        """ A list of all licenses for the Organization as a dictionary of names and IDs """
        if self._licenses is None:
            self._licenses = self.__get_licenses()
        return self._licenses

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
                location = self.get_location(id=entry['locationId'])
                this_pg = PagingGroup(location, entry['id'], entry['name'])
                paging_groups.append(this_pg)
            self._paging_groups = paging_groups
        return self._paging_groups

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

    def get_auto_attendant(self, id: str = None, name: str = None, spark_id: str = None):
        """ Get the AutoAttendant instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Auto
        Attendants will be searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method
        will raise an Exception.

        Args:
            id (str, optional): The AutoAttendant ID to find
            name (str, optional): The AutoAttendant Name to find
            spark_id (str, optional): The Spark ID to find

        Returns:
            AutoAttendant: The AutoAttendant instance correlating to the given search argument.
                None is returned if no AutoAttendant is found.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        if not self._auto_attendants:
            self._auto_attendants = self.auto_attendants
        for aa in self._auto_attendants:
            if aa.id == id:
                return aa
        for aa in self._auto_attendants:
            if aa.name == name:
                return aa
        for aa in self._auto_attendants:
            if aa.spark_id == spark_id:
                return aa
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
                            auto_attendant = self.get_auto_attendant(id=num['owner']['id'])
                            if auto_attendant is not None:
                                num['owner'] = auto_attendant
            if "location" in num:
                location = self.get_location_by_name(num['location']['name'])
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
        self._devices = self._csdm.get_devices()
        return self._devices

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

    def get_location(self, id: str = None, name: str = None, spark_id: str = None):
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
        if not self.locations:
            self.get_locations()
        if id is not None:
            for location in self.locations:
                if location.id == id:
                    return location
        if name is not None:
            for location in self.locations:
                if location.name == name:
                    return location
        if spark_id is not None:
            for location in self.locations:
                if location.spark_id == spark_id:
                    return location
        return None

    @property
    def people(self):
        """ A list of all of the Person instances for the Organization """
        if not self._people:
            return self.get_people()
        else:
            return self._people

    def get_person_by_id(self, id: str):
        """Get the Person instance associated with a given ID

        Args:
            id (str): The Webex ID of the Person to look for.

        Returns:
            Person: The Person instance. If no match is found, None is returned

        """
        for person in self.people:
            if person.id == id:
                return person
        return None

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

        Also creates a new Person instance for the created user.

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
            self._people.append(person)
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

        Args:
            email (str): The email of the Person to return

        Returns:
            Person: Person instance object. None in returned when no Person is found

        """
        log.info("get_person_by_email() started")
        for person in self.people:
            if person.email.lower() == email.lower():
                return person
        return None

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

    def get_locations(self):
        """Get the Locations for the Organization.

        Also stores them in the Org.locations attribute.

        Returns:
            list[Location]: List of Location instance objects. See the Locations class for attributes.

        """
        log.info("get_locations() started")
        self.locations.clear()
        api_resp = webex_api_call("get", "v1/locations", headers=self._headers, params=self._params)
        for location in api_resp:
            this_location = Location(self,
                                     location['id'],
                                     location['name'],
                                     address=location['address'],
                                     time_zone=location['timeZone'],
                                     preferred_language=location['preferredLanguage'])
            self.locations.append(this_location)
        return self.locations

    def create_location(self,
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
        response = webex_api_call('post', '/v1/locations', params={'orgId': self.id}, payload=payload)
        return response

    def get_workspaces(self):
        """Get the Workspaces and Workspace Locations for the Organizations.

        Also stores them in the Org.workspaces and Org.workspace_locations attributes.

        Returns:
            list[Workspace]: List of Workspace instance objects. See the Workspace class for attributes.

        """
        log.info("Getting Workspaces")
        self.workspaces = []
        api_resp = webex_api_call("get", "v1/workspaces", headers=self._headers, params=self._params)
        for workspace in api_resp:
            this_workspace = Workspace(self, workspace['id'], workspace)
            self.workspaces.append(this_workspace)

        log.info("Getting Workspace Locations")
        self.workspace_locations = []
        api_resp = webex_api_call("get", "v1/workspaceLocations", headers=self._headers, params=self._params)
        for location in api_resp:
            this_location = WorkspaceLocation(self, location['id'], location)
            self.workspace_locations.append(this_location)

        return self.workspaces

    def get_pickup_groups(self):
        """Get all of the Call Pickup Groups for an Organization.

        Also stores them in the Org.pickup_groups attribute.

        Returns:
            list[PickupGroup]: List of Call Pickup Groups as a list of dictionaries.
            See the PickupGroup class for attributes.

        """
        log.info("get_pickup_groups() started")
        self.pickup_groups = []
        # First we need to know if we already have locations, because they are needed
        # for the pickup groups call
        if not self.locations:
            self.get_locations()
        # Loop through all of the locations and get their pickup groups
        # We will create a new instance of the PickupGroup class when we find one
        for location in self.locations:
            api_resp = webex_api_call("get", "v1/telephony/config/locations/" + location.id + "/callPickups",
                                      headers=self._headers)
            for item in api_resp['callPickups']:
                pg = PickupGroup(self, location.id, item['id'], item['name'])
                self.pickup_groups.append(pg)
        return self.pickup_groups

    def get_call_queues(self):
        """Get the Call Queues for an Organization.

        Also stores them in the Org.call_queues attribute.

        Returns:
            list[CallQueue]: List of CallQueue instances for the Organization

        """
        log.info("get_call_queues() started")
        self.call_queues = []
        if not self.locations:
            self.get_locations()
        api_resp = webex_api_call("get", "v1/telephony/config/queues", headers=self._headers, params=self._params)
        for queue in api_resp['queues']:
            id = queue.get("id")
            name = queue.get("name", None)
            location_id = queue.get("locationId")
            phone_number = queue.get("phoneNumber", None)
            extension = queue.get("extension", None)
            enabled = queue.get("enabled")

            queue = CallQueue(self, id, name, location_id, phone_number, extension, enabled, get_config=True)
            self.call_queues.append(queue)
        return self.call_queues

    @property
    def auto_attendants(self):
        """ The Auto Attendants for an Organization

        Returns:
            list[AutoAttendant]: List of AutoAttendant instances for the Organization
        """
        log.info("auto_attendants() started")
        if not self.locations:
            self.get_locations()
        api_resp = webex_api_call("get", "v1/telephony/config/autoAttendants",
                                  headers=self._headers, params=self._params)
        for aa in api_resp['autoAttendants']:
            id = aa.get("id")
            name = aa.get("name")
            location = self.get_location_by_name(aa['locationName'])

            auto_attendant = AutoAttendant(self, location=location, id=id, name=name)
            self._auto_attendants.append(auto_attendant)
        return self._auto_attendants

    def get_call_queue_by_id(self, id: str):
        """ Get the :class:`CallQueue` instance with the requested ID
        Args:
            id (str): The CallQueue ID

        Returns:
            HuntGroup: The :class:`CallQueue` instance

        """
        if self.call_queues is None:
            self.get_call_queues()
        for cq in self.call_queues:
            if cq.id == id:
                return cq
        return None

    def get_hunt_group_by_id(self, id: str):
        """ Get the :class:`HuntGroup` instance with the requested ID
        Args:
            id (str): The HuntGroup ID

        Returns:
            HuntGroup: The :class:`HuntGroup` instance

        """
        if self.hunt_groups is None:
            self.get_hunt_groups()
        for hg in self.hunt_groups:
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

    def get_hunt_groups(self):
        """Get the Hunt Groups for an Organization.

        Also stores them in the Org.hunt_groups attribute.

        Returns:
            list[HuntGroup]: List of HuntGroup instances for the Organization

        """
        log.info("get_hunt_groups() started")
        self.hunt_groups = []
        if not self.locations:
            self.get_locations()

        api_resp = webex_api_call("get", "v1/telephony/config/huntGroups", headers=self._headers, params=self._params)
        for hg in api_resp['huntGroups']:
            hunt_group = HuntGroup(self, hg['id'], hg['name'], hg['locationId'], hg['enabled'],
                                   hg.get("phoneNumber", ""), hg.get("extension", ""))
            self.hunt_groups.append(hunt_group)
        return self.hunt_groups

    def get_people(self):
        """ Get all people within the Organization.

        Also creates a Person instance and stores it in the Org.people attributes

        Returns:
            list[Person]: List of Person instances

        """
        log.info("get_people() started")
        params = {"max": "1000", "callingData": "true", **self._params}
        # Fast Mode - callingData: false is much faster
        if self._parent._fast_mode is True:
            params['callingData'] = "false"
        people = webex_api_call("get", "v1/people", headers=self._headers, params=params)
        log.info(f"Found {len(people)} people.")

        for person in people:
            this_person = Person(person['id'], parent=self, config=person)
            self._people.append(this_person)
        return self._people

    def _get_person(self, match):
        log.info(f"Getting person: {match}")
        if "@" in match:
            params = {"max": "1000", "callingData": "true", "email": match, **self._params}
            url = "v1/people"
            response = webex_api_call("get", url, headers=self._headers, params=params)
            this_person = Person(response[0]['id'], parent=self, config=response[0])
        else:
            params = {"callingData": "true"}
            url = f"v1/people/{match}"
            response = webex_api_call("get", url, headers=self._headers, params=params)
            this_person = Person(response['id'], parent=self, config=response)
        self._people.append(this_person)
        return this_person

    @property
    def wxc_people(self):
        """Return all the people within the Organization **who have Webex Calling**

        Returns:
            list[Person]: List of Person instances of people who have a Webex Calling license

        """
        wxc_people = []
        for person in self.people:
            if person.wxc:
                wxc_people.append(person)
        return wxc_people

    @property
    def recorded_people(self):
        """Return all the People within the Organization who have Call Recording enabled

        Returns:
            list[Person]: List of Person instances that have Call Recording enabled

        """
        recorded_people = []
        for person in self.wxc_people:
            rec_config = person.get_call_recording()
            if rec_config['enabled'] is True:
                recorded_people.append(person)
        return recorded_people

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


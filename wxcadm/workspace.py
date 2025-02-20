from __future__ import annotations

import requests
from collections import UserList
from typing import Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from wxcadm import Org
import wxcadm.location
import wxcadm
from wxcadm import log
from .common import *
from .exceptions import *
from .device import DeviceList
from .monitoring import MonitoringList
from .models import BargeInSettings

class WorkspaceLocationList(UserList):
    def __init__(self, parent: wxcadm.Org):
        """

        .. deprecated:: 3.4.0
            The Workspace Location concept is being removed from the Webex APIs. All Workspace Locations are now simply
            :class:`Location`s now. This class will still show up in come cases until it is completely removed.

        """
        super().__init__()
        log.debug("Initializing WorkspaceLocationList")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_workspace_locations()

    def _get_workspace_locations(self):
        """

        .. deprecated:: 3.4.0
            The Workspace Location concept is being removed from the Webex APIs. All Workspace Locations are now simply
            :class:`Location`s now. This class will still show up in come cases until it is completely removed.

        """
        log.debug("Getting list of Workspace Locations")
        workspace_locations = []
        log.debug(f"Using Org {self.parent.name} as WorkspaceLocation filter")
        params = {'orgId': self.parent.id}

        response = webex_api_call("get", "v1/workspaceLocations", params=params)
        log.debug(f"Received {len(response)} Workspace Locations from Webex")
        for entry in response:
            workspace_locations.append(WorkspaceLocation(self.parent, id=entry['id'], config=entry))
        return workspace_locations

    def get_by_id(self, id: str):
        """ Get a WorkspaceLocation instance from the WorkspaceLocationList by ID

        Args:
            id (str): The WorkspaceLocation ID to find

        Returns:
            WorkspaceLocation: The :py:class:`WorkspaceLocation` instance for the given ID.
            None is returned if no match is found.

        """
        entry: WorkspaceLocation
        for entry in self.data:
            if entry.id == id:
                return entry
        return None

    def get(self, id: Optional[str] = None, name: Optional[str] = None):
        """ Get a WorkspaceLocation instance by ID or name

        Args:
            id (str, optional): The WorkspaceLocation ID
            name (str, optional): The WorkspaceLocation name

        Returns:
            WorkspaceLocation: The :class:`WorkspaceLocation` for the given value.
            None is returned if no match is found.

        """
        if name is None and id is None:
            raise ValueError("Method requires id or name argument")
        entry: WorkspaceLocation
        for entry in self.data:
            if entry.id == id or entry.name == name:
                return entry
        return None

class WorkspaceList(UserList):
    def __init__(self, parent: Union[wxcadm.Org, wxcadm.WorkspaceLocation, wxcadm.Location]):
        """

        .. deprecated:: 3.4.0
            The Workspace Location concept is being removed from the Webex APIs. All Workspace Locations are now simply
            :class:`Location`s now. This class will still show up in come cases until it is completely removed.

        """

        super().__init__()
        log.debug("Initializing WorkspaceList instance")
        self.parent: Union[wxcadm.Org, wxcadm.Location] = parent
        self.data: list = self._get_workspaces()

    def _get_workspaces(self):
        log.debug("Getting List of Workspaces")
        workspaces = []
        if isinstance(self.parent, wxcadm.location.Location):
            log.debug(f"Using Location {self.parent.name} as Workspace filter")
            params = {'locationId': self.parent.id}
        elif isinstance(self.parent, wxcadm.workspace.WorkspaceLocation):
            log.debug(f"Using WorkspaceLocation {self.parent.name} as Workspace filter")
            params = {'workspaceLocationId': self.parent.id}
        elif isinstance(self.parent, wxcadm.org.Org):
            log.debug(f"Using Org {self.parent.name} as Workspace filter")
            params = {'orgId': self.parent.id}
        else:
            params = {}
        response = webex_api_call("get", "v1/workspaces", params=params)
        log.debug(f"Received {len(response)} Workspaces from Webex")
        for entry in response:
            workspaces.append(Workspace(self.parent, id=entry['id'], config=entry))
        return workspaces

    def refresh(self):
        """ Re-query the list of Workspaces from Webex """
        self.data: list = self._get_workspaces()

    def get_by_id(self, id: str):
        """ Get a Workspace instance from the WorkspaceList by ID

        Args:
            id (str): The Workspace ID to find

        Returns:
            Workspace: The :py:class:`Workspace` instance for the given ID. None is returned if no match is found.

        """
        entry: Workspace
        for entry in self.data:
            if entry.id == id:
                return entry
        return None

    def get(self, id: Optional[str] = None, name: Optional[str] = None, uuid: Optional[str] = None):
        """ Get a Workspace instance by ID, Name or UUID

        Args:
            id (str, optional): The Workspace ID
            name (str, optional): The Workspace name
            uuid (str, optional): The Workspace UUID

        Returns:
            Workspace: The :class:`Workspace` for the given criteria

        """
        entry: Workspace
        for entry in self.data:
            if entry.id == id or (entry.name is not None and entry.name == name):
                return entry
            if uuid is not None:
                if entry.spark_id.split('/')[-1].upper() == uuid.upper():
                    return entry
        return None

    def webex_calling(self) -> list:
        """ Return a list of Workspaces that have Webex Calling enabled """
        wxc_workspaces = []
        for entry in self.data:
            if entry.calling.lower() == 'webexcalling':
                wxc_workspaces.append(entry)
        return wxc_workspaces

    def professional(self) -> list:
        """ Return a list of Workspaces that have a Professional license """
        wxc_workspaces = []
        for entry in self.data:
            if entry.calling.lower() == 'webexcalling' and entry.license_type.lower() == 'professional':
                wxc_workspaces.append(entry)
        return wxc_workspaces

    def create(self, location: wxcadm.Location,
               name: str,
               floor: Optional[WorkspaceLocationFloor] = None,
               capacity: Optional[int] = None,
               type: Optional[str] = 'notSet',
               phone_number: Optional[str] = None,
               extension: Optional[str] = None,
               notes: Optional[str] = None,
               hotdesking: Optional[bool] = False,
               supported_devices: Optional[str] = 'phones',
               license_type: str = 'workspace'
               ):
        """ Create a new Workspace

        In order to enable Webex Calling, a Location must be provided as well as an extension, phone number, or both.

        Args:
            location (Location): The :class:`Location` where the Workspace will be located
            name (str): The name of the Workspace
            floor (LocationFloor, optional): The :class:`LocationFloor` where the Workspace is located
            capacity (int, optional): The capacity of the Workspace
            type (str, optional): The type of Workspace. See the developer documentation for options. Defaults to `noteSet`
            phone_number (str, optional): The Webex Calling phone number for the Workspace
            extension (str, optional): The Webex Calling extension for the Workspace
            notes (str, optional): Free-form text notes
            hotdesking (bool, optional): Whether the workspace is enabled for Hot Desking. Defaults to False.
            supported_devices (str, optional): `phones` or `collaborationDevices`. Defaults to `phones`
            license_type (str, optional): 'workspace' or 'professional'. Defaults to 'workspace'

        Returns:
            Workspace: The :class:`Workspace` instance that is created in Control Hub

        Raises:
            ValueError: Raised when an ``extension`` or ``phone_number`` is not provided.

        """
        if extension is None and phone_number is None:
            raise ValueError("Must provide extension, phone_number, or both")
        # Removed 3.4.0 when Workspace Locations were deprecated
        # if location.workspace_location is None:
        #     raise KeyError(f"Location {location.name} does not have a Workspace Location")
        if hotdesking is True:
            hotdesking = 'on'
        else:
            hotdesking = 'off'

        payload = {
            'orgId': self.parent.org_id,
            'displayName': name,
            'locationId': location.id,
            'floorId': floor,
            'capacity': capacity,
            'type': type,
            'calling': {
                'type': 'webexCalling',
                'webexCalling': {
                    'phoneNumber': phone_number,
                    'extension': extension,
                    'locationId': location.id
                }
            },
            'notes': notes,
            'hotdeskingStatus': hotdesking,
            'supportedDevices': supported_devices
        }

        # Find an available license if a Professional license was requested
        if license_type.lower() == 'professional':
            wxc_license = self.parent.get_wxc_person_license()
            payload['calling']['webexCalling']['licenses'] = [wxc_license]

        response = webex_api_call('post', 'v1/workspaces', payload=payload)
        new_workspace_id = response['id']
        # TODO - Eventually I would like to remove the refresh() and just add the new Workspace directly
        self.parent.workspaces.refresh()
        new_workspace = self.parent.workspaces.get_by_id(new_workspace_id)
        return new_workspace


class Workspace:
    def __init__(self, parent: wxcadm.Org, id: str, config: Optional[dict] = None):
        """Initialize a Workspace instance

        If only the `id` is provided, the configuration will be fetched from
        the Webex API. To save API calls, the config dict can be passed using the `config` argument

        Args:
            parent (Org): The Organization to which this workspace belongs
            id (str): The Webex ID of the Workspace
            config (dict): The configuration of the Workspace as returned by the Webex API

        """
        self.id: str = id
        """The Webex ID of the Workspace"""
        self._parent: Union[wxcadm.Org, wxcadm.Location] = parent
        # Instance attributes
        self.location: Optional[wxcadm.Location] = None
        """ The :class:`Location` of the Workspace """
        self.floor_id: Optional[str] = None
        """The Webex ID of the Location Floor ID"""
        self.name: str = ""
        """The name of the Workspace"""
        self.capacity: Optional[int] = None
        """The capacity of the Workspace"""
        self.type: Optional[str] = None
        """
        The type of Workspace. Valid values are:

            "notSet": No value set
            "focus": High concentration
            "huddle": Brainstorm/collaboration
            "meetingRoom": Dedicated meeting space
            "open": Unstructured agile
            "desk": Individual
            "other": Unspecified
        """
        self.sip_address: Optional[str] = None
        """The SIP Address used to call to the Workspace"""
        self.created: Optional[str] = None
        """The date and time the workspace was created"""
        self.calling: Optional[str] = None
        """
        The type of Calling license assigned to the Workspace. Valid values are:

            'freeCalling': Free Calling
            'hybridCalling': Hybrid Calling
            'webexCalling': Webex Calling
            'webexEdgeForDevices': Webex Edge for Devices
        """
        self.calendar: Optional[dict] = None
        """The type of calendar connector assigned to the Workspace"""
        self.notes: Optional[str] = None
        """Notes associated with the Workspace"""
        self.licenses: list = []
        """ The licenses for the Workspace when the calling value is 'webexCalling' """

        # Property storage
        self._numbers: Optional[dict] = None
        self._devices: Optional[DeviceList] = None
        self._monitoring: Optional[dict] = None
        self._barge_in: Optional[BargeInSettings] = None


        if config:
            self.__process_config(config)
        else:
            self.get_config()

    def __str__(self):
        return self.name

    @property
    def org_id(self) -> str:
        """ The Org ID of the Workspace """
        return self._parent.org_id

    @property
    def number(self):
        """ The phone number of the Workspace when the Calling type is 'webexCalling'

        .. note::

            When only one number is assigned, a string will be returned. If multiple numbers are assigned, a list
            of strings will be returned.

        """
        if self._numbers is None:
            log.info(f"Getting numbers for Workspace: {self.name}")
            self._numbers = webex_api_call('get', f"v1/workspaces/{self.id}/features/numbers",
                                           params={'orgId': self.org_id})
            log.debug(self._numbers)
        if len(self._numbers['phoneNumbers']) == 1:
            return self._numbers['phoneNumbers'][0].get('external', None)
        elif len(self._numbers['phoneNumbers']) > 1:
            num_list = []
            for number in self._numbers['phoneNumbers']:
                if number['external'] is not None:
                    num_list.append(number['external'])
            return num_list
        else:
            return None

    @property
    def extension(self):
        """ The extension of the Workspace when the Calling type is 'webexCalling' """
        if self._numbers is None:
            self._numbers = webex_api_call('get', f"v1/workspaces/{self.id}/features/numbers",
                                           params={'orgId': self.org_id})
        if len(self._numbers['phoneNumbers']) == 1:
            return self._numbers['phoneNumbers'][0].get('extension', None)
        elif len(self._numbers['phoneNumbers']) > 1:
            num_list = []
            for number in self._numbers['phoneNumbers']:
                if number['extension'] is not None:
                    num_list.append(number['extension'])
            return num_list
        else:
            return None

    @property
    def barge_in(self):
        if self._barge_in is None:
            try:
                response = webex_api_call('get', f"v1/telephony/config/workspaces/{self.id}/bargeIn",
                                          params={'orgId': self.org_id})
                response['parent'] = self
                self._barge_in = BargeInSettings.from_dict(response)
            except wxcadm.exceptions.APIError:
                return None
        return self._barge_in

    @property
    def esn(self):
        """ The Enterprise Significant Number (ESN) for the Workspace when the Calling type is 'webexCalling' """
        if self._numbers is None:
            self._numbers = webex_api_call('get', f"v1/workspaces/{self.id}/features/numbers",
                                           params={'orgId': self.org_id})
        if len(self._numbers['phoneNumbers']) == 1:
            return self._numbers['phoneNumbers'][0].get('esn', None)
        elif len(self._numbers['phoneNumbers']) > 1:
            num_list = []
            for number in self._numbers['phoneNumbers']:
                if number['esn'] is not None:
                    num_list.append(number['esn'])
            return num_list
        else:
            return None

    @property
    def spark_id(self):
        """ The internal identifier used by Webex """
        return decode_spark_id(self.id)

    @property
    def monitoring(self) -> MonitoringList:
        """ The :class:`~.monitoring.MonitoringList` associated with the Workspace """
        if self._monitoring is None:
            response = webex_api_call("get", f"v1/workspaces/{self.id}/features/monitoring",
                                      params={"orgId": self.org_id})
            response['parent'] = self
            response['org'] = self._parent
            if "monitoredElements" not in response.keys():
                response['monitoredElements'] = []
            self._monitoring = MonitoringList.from_dict(response)
        return self._monitoring

    def get_monitored_by(self):
        """ Returns a list of Users (Person) and Workspaces that are Monitoring this Workspace """
        if isinstance(self._parent, wxcadm.Org):
            monitor_list = self._parent.get_all_monitoring()
        elif isinstance(self._parent, wxcadm.Location):
            monitor_list = self._parent.parent.get_all_monitoring()
        try:
            return monitor_list['workspaces'][self.id]
        except (KeyError, TypeError):
            return None

    def delete(self):
        """ Delete the Workspace

        Returns:
            bool: True on success. In failure conditions, an exception will be raised

        Raises:
            APIError: Raised when the API call fails for any reason

        """
        response = webex_api_call('delete', f'v1/workspaces/{self.id}')
        self._parent.workspaces.refresh()
        return True

    @property
    def devices(self):
        if self._devices is None:
            self._devices = DeviceList(self)
        return self._devices

    @property
    def caller_id(self) -> dict:
        """ The Caller ID settings for the Workspace """
        log.info(f"Getting Caller ID config for Workspace: {self.name}")
        response = webex_api_call('get', f"v1/workspaces/{self.id}/features/callerId", params={'orgId': self.org_id})
        return response

    def set_caller_id(self, name: str, number: str, block_for_received_calls: Optional[bool] = False):
        """ Set the Caller ID for the Workspace

        Args:
            name (str): The name to set as the Caller ID Name. Also accepts keywords: ``direct`` sets the name to the
                Workspace's name . ``location`` sets the name to the name of the Location.
            number (str): The number to set as the Caller ID.  Also accepts keywords: ``direct`` sets the number to the
                Workspace's DID in Webex. ``location`` sets the name to the main number of the Location.
            block_for_received_calls (bool, optional): Block this Workspace's identity when receiving a call


        Returns:
            bool: True on success

        Raises:
            wxcadm.exceptions.APIError: Raised when there is a problem with the API call

        """
        log.info(f"Setting Caller ID for {self.name}")
        log.debug(f"\tNew Name: {name}\tNew Number: {number}")
        payload = {}
        # Handle the possible number values
        if number.lower() == "direct":
            payload['selected'] = "DIRECT_LINE"
        elif number.lower() == "location":
            payload['selected'] = "LOCATION_NUMBER"
        else:
            payload['selected'] = "CUSTOM"
            payload['customNumber'] = number
        # Then deal with possible name values
        if name.lower() == "direct":
            payload['externalCallerIdNamePolicy'] = "DIRECT_LINE"
        elif name.lower() == "location":
            payload['externalCallerIdNamePolicy'] = "LOCATION"
        else:
            payload['externalCallerIdNamePolicy'] = "OTHER"
            payload['customExternalCallerIdName'] = name
        payload['blockInForwardCallsEnabled'] = block_for_received_calls

        webex_api_call('put', f"v1/workspaces/{self.id}/features/callerId", params={'orgId': self.org_id},
                       payload=payload)
        return True

    def get_config(self):
        """Get (or refresh) the confirmation of the Workspace from the Webex API"""
        log.info(f"Getting Workspace config for {self.id}")
        r = requests.get(_url_base + f"v1/workspaces/{self.id}", headers=self._headers,
                         params={'orgId': self._parent.org_id})
        if r.status_code in [200]:
            response = r.json()
            self.__process_config(response)
        else:
            raise APIError(f"Unable to fetch workspace config for {self.id}")

    def __process_config(self, config: dict):
        """Processes the config dict, whether passed in init or from an API call"""
        self.name = config.get("displayName", "")
        if 'locationId' in config.keys():
            if isinstance(self._parent, wxcadm.Org):
                self.location = self._parent.locations.get(id=config['locationId'])
            elif isinstance(self._parent, wxcadm.Location):
                self.location = self._parent
        else:
            self.location = config.get("workspaceLocationId", None)
        self.floor = config.get("floorId", "")
        self.capacity = config.get("capacity", 0)
        if 'type' in config:
            self.type = config['type']
        self.sip_address = config.get("sipAddress", "")
        self.created = config.get("created", "")
        if "calling" in config:
            self.calling = config['calling']['type']
        else:
            self.calling = "None"
        self.calendar = config.get('calendar', None)
        self.notes = config.get("notes", "")
        if self.calling == 'webexCalling':
            self.licenses = config['calling']['webexCalling'].get('licenses', [])

    @property
    def ecbn(self) -> dict:
        """ The Emergency Callback Number details of the Workspace """
        response = webex_api_call('get', f'v1/telephony/config/workspaces/{self.id}/emergencyCallbackNumber',
                                  params={'orgId': self.org_id})
        return response

    def set_ecbn(self, value: Union[str, wxcadm.Person, wxcadm.Workspace, wxcadm.VirtualLine]):
        """ Set the ECBN of the Workspace

        Valid values are ``'direct'``, ``'location'``, or a :class:`Person`, :class:`Workspace`, or
        :class:`VirtualLine` to set the ECBN to one of those.

        Args:
            value (str, Person, Workspace, VirtualLine): The value to set the ECBN to

        Returns:
            bool: True on success

        """
        if isinstance(value, wxcadm.Person) or \
                isinstance(value, wxcadm.Workspace) or \
                isinstance(value, wxcadm.VirtualLine):
            payload = {
                'selected': 'LOCATION_MEMBER_NUMBER',
                'locationMemberId': value.id
            }
        elif value.lower() == 'direct' or value.lower() == 'direct_line':
            payload = {'selected': 'DIRECT_LINE'}
        elif value.lower() == 'location' or value.lower() == 'location_ecbn':
            payload = {'selected': 'LOCATION_ECBN'}
        else:
            raise ValueError('Unknown value')

        response = webex_api_call('put', f'v1/telephony/config/workspaces/{self.id}/emergencyCallbackNumber',
                                  params={'orgId': self.org_id}, payload=payload)
        return response

    @property
    def license_type(self) -> Optional[str]:
        """ The type of Webex Calling license used by the Workspace. Either 'WORKSPACE' or 'PROFESSIONAL'.

        Returns:
            str: The type of license, either 'WORKSPACE' or 'PROFESSIONAL'

        """
        log.info(f"Getting license type for Workspace: {self.name}")
        if len(self.licenses) == 1:
            lic_name = self._parent.get_license_name(self.licenses[0])
            if 'Workspaces' in lic_name:
                return 'WORKSPACE'
            elif 'Professional' in lic_name:
                return 'PROFESSIONAL'
            else:
                return lic_name
        if len(self.licenses) == 0:
            return None
        else:
            return "MULTIPLE"

    def set_professional_license(self):
        if self.license_type.upper() == 'PROFESSIONAL':
            return True
        new_license = self._parent.get_wxc_person_license()
        payload = {
            'displayName': self.name,
            'locationId': self.location.id,
            'floorId': self.floor_id,
            'capacity': self.capacity,
            'type': self.type,
            'calling': {
                'type': 'webexCalling',
                'webexCalling': {
                    'licenses': [
                        new_license
                    ]
                }
            },
            'notes': self.notes,


        }
        response = webex_api_call('put', f"v1/workspaces/{self.id}",
                                  params={'orgId': self.org_id},
                                  payload=payload)
        self.__process_config(response)
        return True


class WorkspaceLocation:
    def __init__(self, parent: wxcadm.Org, id: str, config: dict = None):
        """Initialize a WorkspaceLocation instance.

        If only the `id` is provided, the configuration will be fetched from
            the Webex API. To save API calls, the config dict can be passed using the `config` argument

        Args:
            parent (Org): The Organization to which this WorkspaceLocation belongs
            id (str): The Webex ID of the WorkspaceLocation
            config (dict): The configuration of the WorkspaceLocation as returned by the Webex API

        .. deprecated:: 3.4.0
            The Workspace Location concept is being removed from the Webex APIs. All Workspace Locations are now simply
            :class:`Location`s now. This class will still show up in come cases until it is completely removed.

        """
        self.id: str = id
        """The Webex ID of the Workspace"""
        self._parent: wxcadm.Org = parent
        # Attributes inherited from the Org parent
        self._headers = self._parent._headers
        self._params = self._parent._params
        # Instance attributes
        self.name: Optional[str] = None
        """The name of the WorkspaceLocation"""
        self.address: Optional[str] = None
        """The address of the WorkspaceLocation"""
        self.country: Optional[str] = None
        """The country code (ISO 3166-1) for the WorkspaceLocation"""
        self.city: Optional[str] = None
        """The city name where the WorkspaceLocation is located"""
        self.latitude: Optional[float] = None
        """The WorkspaceLocation latitude"""
        self.longitude: Optional[float] = None
        """The WorkspaceLocation longitude"""
        self.notes: Optional[str] = None
        """Notes associated with the WorkspaceLocation"""
        self.floors: Optional[list] = None
        self._workspaces: Optional[WorkspaceList] = None

        if config:
            self.__process_config(config)
        else:
            self.get_config()

    def get_config(self):
        """Get (or refresh) the configuration of the WorkspaceLocations from the Webex API"""
        log.info(f"Getting Workspace config for {self.id}")
        r = requests.get(_url_base + f"v1/workspaceLocations/{self.id}", headers=self._headers, params=self._params)
        if r.status_code in [200]:
            response = r.json()
            self.__process_config(response)
        else:
            raise APIError(f"Unable to fetch workspace config for {self.id}")

    def get_floors(self):
        """Get (or refresh) the WorkspaceLocationFloor instances for this WorkspaceLocation"""
        log.info(f"Getting Location Floors for {self.name}")
        self.floors = []
        r = requests.get(_url_base + f"v1/workspaceLocations/{self.id}/floors",
                         headers=self._headers, params=self._params)
        response = r.json()
        for floor in response['items']:
            this_floor = WorkspaceLocationFloor(floor)
            self.floors.append(this_floor)

    @property
    def workspaces(self):
        """ The :py:class:`Workspace` instances for this WorkspaceLocation """
        if self._workspaces is None:
            self._workspaces = WorkspaceList(self)
        return self._workspaces


    def __process_config(self, config: dict):
        """Processes the config dict, whether passed in init or from an API call"""
        self.name = config.get("displayName", "")
        self.address = config.get("address", "")
        self.country = config.get("countryCode", "")
        self.city = config.get("cityName", "")
        self.latitude = config.get("latitude", "")
        self.longitude = config.get("longitude", "")
        self.notes = config.get("notes", "")

    def get_uuid(self):
        """ Returns just the UUID portion of the `id` property.

        .. versionadded:: 4.2.2
            Added because the Base64 ID does not match the :attr:`Device.workspace_location_id`. The assumption is
            that this will be resolved in the future, but needs to be supported until then.

        Returns:
            str: The UUID component of the :attr:`id`

        """
        return decode_spark_id(self.id).split("/")[-1]


class WorkspaceLocationFloor:
    def __init__(self, config: dict):
        """Initialize a new WorkspaceLocationFloor

        Args:
            config (dict): The config as returned by the Webex API

        .. deprecated:: 3.4.0
            The Workspace Location concept is being removed from the Webex APIs. All Workspace Location Floors are now
            :class:`LocationFloor`s now. This class will still show up in come cases until it is completely removed.

        """
        self.name = config.get("displayName")
        self.id = config.get("id")
        self.floor = config.get("floorNumber")

from __future__ import annotations

import requests
from collections import UserList
from typing import Optional, Union

import wxcadm.location
import wxcadm
from wxcadm import log
from .common import *
from .exceptions import *
from .device import Device


class WorkspaceLocationList(UserList):
    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing WorkspaceLocationList")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_workspace_locations()

    def _get_workspace_locations(self):
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

class WorkspaceList(UserList):
    def __init__(self, parent: Union["Org", "WorkspaceLocation"]):
        super().__init__()
        log.debug("Initializing WorkspaceList instance")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_workspaces()

    def _get_workspaces(self):
        log.debug("Getting List of Workspaces")
        workspaces = []
        # Eventually, I would like to handle Location instances, but for now we just reject them
        if isinstance(self.parent, wxcadm.location.Location):
            log.warning("Workspaces by Location are not Supported. WorkspaceLocation must be used.")
            raise ValueError("Workspaces cannot be obtained for a Location")
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
        self._parent: wxcadm.Org = parent
        # Attributes inherited from the Org parent
        self._headers = self._parent._headers
        self._params = self._parent._params
        # Instance attributes
        self.location: Optional[str] = None
        """The Webex ID of the Workspace Location (note this is a Workspace Location, not a Calling Location."""
        self.floor: Optional[str] = None
        """The Webex ID of the Floor ID"""
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

        if config:
            self.__process_config(config)
        else:
            self.get_config()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def spark_id(self):
        """ The internal identifier used by Webex """
        return decode_spark_id(self.id)

    @property
    def devices(self):
        log.info(f"Collecting devices for {self.name}")
        devices = []
        response = webex_api_call('get', f'/v1/telephony/config/workspaces/{self.id}/devices')
        log.debug(f"{response}")
        for item in response['devices']:
            this_device = Device(self, item)
            devices.append(this_device)
        return devices

    def add_device(self, model: str, mac: Optional[str] = None, password: Optional[str] = None):
        """ Add a new device to the Workspace

        In order to use this method, you must know the model of the device that you are adding, as expected by the
        Webex API. If you are adding a "Generic IPPhone Customer Managed" device, you can use that value or simply
        send ``model='GENERIC'`` as an alias. You can find the full list of models with the
        :py:meth:`Org.get_supported_devices()` method.

        If the MAC address is passed, a device will be created with the provided MAC address. If no MAC address is
        passed, an Activation Code will be generated and returned as part of the response. Your integration/token must
        have the ``identity:placeonetimepassword_create`` scope to create Activation Codes for devices.

        Args:
            model (str): The model name of the device being added
            mac (str, optional): The MAC address of the device being added
            password (str, optional): Only valid when creating a Generic IPPhone Customer Managed device. If a
                password is not provided, the Webex API will generate a unique, compliant SIP password and return it
                in the response.

        Returns:
            dict: The dict values vary based on the type of device being activated. If the device fails for any reason,
                False will be returned. At the moment, Webex doesn't provide very useful failure reasons, but those may
                be added to the return value when they are available.

        """
        log.info(f"Adding a device to {self.name}")
        payload = {
            "workspaceId": self.id,
            "model": model
        }
        data_needed = False  # Flag that we need to get platform data once we have a Device ID
        if mac is None:
            # If no MAC address is provided, just generate an activation code for the device
            try:
                response = webex_api_call('post',
                                          '/v1/devices/activationCode',
                                          payload=payload,
                                          params={'orgId': self._parent.id})
                log.debug(f"\t{response}")
            except APIError:
                return False

            # Get the ID of the device we just inserted
            device_id = response.get('id', None).replace('=', '')

            results = {
                'device_id': device_id,
                'activation_code': response['code']
            }
        else:
            payload['mac'] = mac
            if model.upper() == "GENERIC" or model.upper() == "Generic IPPhone Customer Managed":
                payload['model'] = "Generic IPPhone Customer Managed"  # Hard-code what the API expects (for now)
                data_needed = True
                if password is None:    # Generate a unique password
                    response = webex_api_call('POST',
                                                  f'/v1/telephony/config/locations/{self.location}/actions/'
                                                  f'generatePassword/invoke')
                    password = response['exampleSipPassword']
                payload['password'] = password
            response = webex_api_call('post', '/v1/devices', payload=payload)
            log.debug(f"\t{response}")

            # Get the ID of the device we just inserted
            device_id = response.get('id', None).replace('=', '')

            results = {
                'device_id': device_id,
                'mac': response['mac']
            }

            if data_needed is True:
                response = webex_api_call('get', f'/v1/telephony/config/devices/{device_id}')
                results['sip_auth_user'] = response['owner']['sipUserName']
                results['line_port'] = response['owner']['linePort']
                results['password'] = password
                results['sip_userpart'] = response['owner']['linePort'].split('@')[0]
                results['sip_hostpart'] = response['owner']['linePort'].split('@')[1]
                results['sip_outbound_proxy'] = response['proxy']['outboundProxy']
                results['sip_outbound_proxy_srv'] = f"_sips._tcp.{response['proxy']['outboundProxy']}"

        # Provide the Device instance in the response as well
        results['device_object'] = self._parent.get_device_by_id(device_id)
        return results

    def get_config(self):
        """Get (or refresh) the confirmation of the Workspace from the Webex API"""
        log.info(f"Getting Workspace config for {self.id}")
        r = requests.get(_url_base + f"v1/workspaces/{self.id}", headers=self._headers, params=self._params)
        if r.status_code in [200]:
            response = r.json()
            self.__process_config(response)
        else:
            raise APIError(f"Unable to fetch workspace config for {self.id}")

    def __process_config(self, config: dict):
        """Processes the config dict, whether passed in init or from an API call"""
        self.name = config.get("displayName", "")
        self.location = config.get("workspaceLocationId", "")
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


class WorkspaceLocation:
    def __init__(self, parent: wxcadm.Org, id: str, config: dict = None):
        """Initialize a WorkspaceLocation instance.

        If only the `id` is provided, the configuration will be fetched from
            the Webex API. To save API calls, the config dict can be passed using the `config` argument

        Args:
            parent (Org): The Organization to which this WorkspaceLocation belongs
            id (str): The Webex ID of the WorkspaceLocation
            config (dict): The configuration of the WorkspaceLocation as returned by the Webex API

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


class WorkspaceLocationFloor:
    def __init__(self, config: dict):
        """Initialize a new WorkspaceLocationFloor

        Args:
            config (dict): The config as returned by the Webex API

        """
        self.name = config.get("displayName")
        self.id = config.get("id")
        self.floor = config.get("floorNumber")

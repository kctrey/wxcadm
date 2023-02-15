from __future__ import annotations

import requests
from typing import Optional
from wxcadm import log
from .common import *
from .exceptions import *
from .device import Device


class Workspace:
    def __init__(self, parent: Org, id: str, config: Optional[dict] = None):
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
        self._parent: Org = parent
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
    def __init__(self, parent: Org, id: str, config: dict = None):
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
        self._parent: Org = parent
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

        if config:
            self.__process_config(config)
        else:
            self.get_config()
        self.get_floors()

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

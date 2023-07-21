from __future__ import annotations

from dataclasses import dataclass, field
from collections import UserList
from wxcadm import log

import requests
from typing import Optional
from .exceptions import *


class RedSky:
    def __init__(self, username: str, password: str):
        """ Initialize a connection to RedSky and obtain basic account info

        Args:
            username (str): The Horizon admin username
            password (str): The Horizon admin password

        """
        # Log into Horizon and get access token info
        payload = {"username": username, "password": password}
        r = requests.post("https://api.wxc.e911cloud.com/auth-service/login", json=payload)
        if r.ok:
            response = r.json()
            log.debug(response)
        else:
            raise APIError("Cannot log into RedSky Horizon")
        self._access_token = response['accessToken']
        self.org_id = response['userProfileTO']['company']['id']
        self._refresh_token = response['refreshTokenInfo']['id']
        self._full_config = response
        self._buildings = []

    @property
    def _headers(self):
        headers = {"Authorization": "Bearer " + self._access_token}
        return headers

    def _token_refresh(self):
        """A method to refresh the access_toke using the stored refresh_token"""
        r = requests.post("https://api.wxc.e911cloud.com/auth-service/token/refresh",
                          headers=self._headers,
                          json=self._refresh_token)
        if r.status_code == 200:
            response = r.json()
            self._access_token = response['accessToken']
            self._refresh_token = response['refreshTokenInfo']['id']
        else:
            raise APIError("There was an error refreshing the RedSky token")

    def get_all_locations(self):
        """ Get all of the Locations that RedSky knows about

        This method is only useful in very specific reporting cases, since you only get the Location information
        and no device-level information.

        Returns:
             list[dict]: A list of the location information as a dict

        """
        response: dict[str, list[dict]] = {'corporate': [], 'personal': []}
        r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/locations/parent/{self.org_id}",
                         headers=self._headers)
        response['corporate'].extend(r.json())
        for user in self.users:
            response['personal'].extend(user.user_locations)
        return response

    @property
    def buildings(self):
        """A list of all of the RedSkyBuilding instances within this RedSky account

        Returns:
            list[RedSkyBuilding]: The RedSkyBuilding instances

        """
        params = {"page": 1,
                  "pageSize": 100,
                  "searchTerm": None,
                  "origin": "default"}
        self._buildings = []

        r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/buildings/parent/{self.org_id}",
                         params=params, headers=self._headers)
        if r.status_code == 401:
            if r.status_code == 401:
                self._token_refresh()
                r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/buildings/parent/{self.org_id}",
                                 headers=self._headers, params=params)
        if r.status_code == 200:
            response = r.json()
            for item in response:
                building = RedSkyBuilding(self, item)
                self._buildings.append(building)
        else:
            raise APIError("Something went wrong getting the list of buildings")

        return self._buildings

    def get_building_by_name(self, name: str):
        """Get the RedSkyBuilding instance for a given name

        Args:
            name (str): The name of the Building to return. Not case sensitive.

        Returns:
            RedSkyBuilding: The instance of the RedSkyBuilding class. None is returned if no match is found.

        """
        for building in self.buildings:
            if building.name.lower() == name.lower():
                return building

        return None

    def get_building_by_webex_location(self, location: Location):
        """Get the RedSkyBuilding instance for a given Location instance.

        This method will first try to match on the Location ID in Webex, which will work if the Building was created
        by ***wxcadm**. If no match is found, it will attempt to match on the Location Name. The Webex Location name and
        the RedSky Building name must match exactly, although case is ignored.

        Args:
            location (Location): The Location instance to search against.

        Returns:
            RedSkyBuilding: The instance of the RedSkyBuilding class. None is returned if no match is found.

        """
        buildings = self.buildings
        for building in buildings:
            if building.supplemental_data == location.id[-20:]:
                return building
        for building in buildings:
            if building.name.lower() == location.name.lower():
                return building
        return None

    def add_building(self, webex_location: Optional[Location] = None,
                     address_string: Optional[str] = None, create_location: bool = True):
        """ Add a new Building to RedSky

        The ``create_location`` arg defaults to True, which will automatically create a RedSkyLocation called "Default".
        If you want to prevent a Location from being created, pass ``create_location=False``.

        Either a ``webex_location`` or ``address_string`` argument should be provided. If both are provided, the Webex
        Location instance will take precedence

        Args:
            webex_location (Location): The Webex Location instance to create the building for
            address_string (str, optional): The complete address, as a string
            create_location (bool. optional: Whether to create a RedSkyLocation called "Default" in the RedSkyBuilding

        Returns:
            RedSkyBuilding: The RedSkyBulding instance that was created

        Raises:
            ValueError: Raised when trying to create a RedSkyBuilding for a Location that is not in the U.S.
            wxcadm.exceptions.APIError: Raised on all API failures

        """
        if webex_location is not None:
            if webex_location.address['country'] != "US":
                raise ValueError("Cannot create Building for non-US location")

            a1 = webex_location.address['address1']
            a2 = webex_location.address.get("address2", "")
            city = webex_location.address['city']
            state = webex_location.address['state']
            zip = webex_location.address['postalCode']
            full_address = f"{a1} {a2}, {city}, {state} {zip}"
        else:
            full_address = address_string

        payload = {"name": webex_location.name,
                   "supplementalData": webex_location.id[-20:],
                   "parentOrganizationUnitId": self.org_id,
                   "fullAddress": full_address,
                   "origin": "default"
                   }
        log.debug(payload)
        r = requests.post("https://api.wxc.e911cloud.com/geography-service/buildings",
                          headers=self._headers, json=payload)
        if r.ok:
            building = self.get_building_by_webex_location(webex_location)
            if create_location is True:
                building = self.get_building_by_webex_location(webex_location)
                if building is not None:
                    building.add_location("Default", ecbn=webex_location.main_number.replace("+1", ""))
                else:
                    raise APIError("The created Building cannot be located. Location not created.")
            return building
        else:
            raise APIError(f"Something went wrong adding Building: {r.text}")

    @property
    def held_devices(self):
        """All of the HELD devices known to RedSky"""
        params = {"page": 1,
                  "pageSize": 100,
                  "searchTerm": None,
                  "type": None}
        r = requests.get(f"https://api.wxc.e911cloud.com/admin-service/held/org/{self.org_id}",
                         headers=self._headers, params=params)
        if r.status_code == 401:
            self._token_refresh()
            r = requests.get(f"https://api.wxc.e911cloud.com/admin-service/held/org/{self.org_id}",
                             headers=self._headers, params=params)
        if r.status_code == 200:
            self._held_devices = []
            response = r.json()
            log.debug(response)
            for device in response:
                self._held_devices.append(device)
        else:
            raise APIError(f"Something went wrong getting the HELD devices {r.text}")

        return self._held_devices

    def phones_without_location(self):
        """Get a list of phone (HELD) devices that don't have a RedSkyLocation associated

        Returns:
            list[dist]: A list of the device properties from RedSky

        """
        devices = []
        for device in self.held_devices:
            if device['erl'] is None and device['deviceType'] == "HELD":
                devices.append(device)
        return devices

    def clients_without_location(self):
        """Get a list of soft client (HELD+) devices that don't have a RedSkyLocation associated

        Returns:
            list[dict]: A list of the device properties from RedSky

        """
        devices = []
        for device in self.held_devices:
            if device['erl'] is None and device['deviceType'] == "HELD_PLUS":
                devices.append(device)
        return devices

    def get_mac_discovery(self):
        """ Get the current MAC address mapping defined in RedSky Horizon

        Returns:
            list[dict]: A list of all the MAC address mappings

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/macAddress/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting MAC mapping: {r.text}")
        return mappings

    def add_mac_discovery(self, mac: str, location: "RedSkyLocation", description: str = ""):
        """ Add a new MAC address mapping to RedSky Horizon

        Args:
            mac (str): The MAC address to add. RedSky isn't picky about formatting or case, so any MAC format should
                work
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        payload = {"macAddress": mac,
                   "locationId": location.id,
                   "orgId": self.org_id,
                   "description": description}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/macAddress",
                          headers=self._headers, json=payload)
        if r.ok:
            added_mapping = r.json()
        else:
            raise APIError(f"There was a problem adding the mapping: {r.text}")
        return added_mapping

    def get_lldp_discovery(self):
        """ Get the current LLDP chassis and port mappings defined in RedSky Horizon

        Returns:
            list[dict]: A list of all the LLDP mappings

        Raises:
            APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/networkSwitch/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                item['ports'] = []
                r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/networkSwitchPort/"
                                 f"networkSwitch/{item['id']}",
                                 headers=self._headers)
                if r.ok:
                    ports = r.json()
                    for port in ports:
                        item['ports'].append(port)
                else:
                    raise APIError(f"There was a problem getting Chassis Ports: {r.text}")
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting Chassis mapping: {r.text}")
        return mappings

    def get_lldp_discovery_by_chassis(self, chassis_id: str):
        """ Get the LLDP chassis and port mappings for a give Chassis identifier

        Args:
            chassis_id (str): The Chassis idnetifier

        Returns:
            dict: The LLDP discovery configuration. None is returned if no match if found

        """
        for entry in self.get_lldp_discovery():
            if entry['chassisId'].upper() == chassis_id.upper():
                return entry
        return None


    def add_lldp_discovery(self, chassis: str, location: "RedSkyLocation", ports: list = None, description: str = ""):
        """ Add a new LLDP mapping to RedSky Horizon

        If only a chassis identifier is provided, the chassis will be added. If a list of ports are provided, the method
        will determine if the chassis already exists. If it does, the ports will be added and the chassis mapping will
        not be changed. If the chassis does not exist, it will be added and mapped to the provided RedSkyLocation, and
        the list of ports will be added, mapped to the same RedSkyLocation.

        Args:
            chassis (str): The chassis identifier
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            ports (list, optional): A list of ports (i.e. ['1','2','3'] or ['B000B4BB1BF4:P1'] to add mapping for
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        if ports is not None:
            # Determine if the chassis already exists
            chassis_exists = False
            chassis_id = ""
            current_lldp = self.get_lldp_discovery()
            for entry in current_lldp:
                if entry['chassisId'].lower() == chassis.lower():
                    chassis_id = entry['id']
                    chassis_exists = True
            if chassis_exists is False:
                new_chassis = self._add_chassis_discovery(chassis, location, description)
                chassis_id = new_chassis['id']
            for port in ports:
                self._add_port_discovery(chassis_id, port, location, description)

            # Now that we added everything, let's get the details of the new chassis and its ports
            current_lldp = self.get_lldp_discovery()
            for entry in current_lldp:
                if entry['chassisId'].lower == chassis.lower():
                    return entry
        else:
            new_chassis = self._add_chassis_discovery(chassis, location, description)
            return new_chassis

    def delete_lldp_chassis(self, chassis_id: str, delete_ports: bool = False):
        """ Delete an LLDP mapping from Horizon Mobility

        Args:
            chassis_id (str): The chassis ID of the LLDp Discovery to delete
            delete_ports (bool, optional): Whether to delete all ports first. Defaults to False

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Deleting Chassis Discovery: {chassis_id}")
        chassis_entry = self.get_lldp_discovery_by_chassis(chassis_id)

        if delete_ports is True:
            log.info("Deleting all ports")
            for port in chassis_entry['ports']:
                log.info(f"\tDeleting Port: {port['portId']}")
                r = requests.delete(f"https://api.wxc.e911cloud.com/networking-service/networkSwitchPort/{port['id']}",
                                    headers=self._headers,
                                    params={
                                        "companyId": self.org_id
                                    })
                log.debug(f"Response Code: {r.status_code}")

        r = requests.delete(f"https://api.wxc.e911cloud.com/networking-service/networkSwitch/{chassis_entry['id']}",
                            headers=self._headers,
                            params={
                                "companyId": self.org_id
                            })
        log.debug(f"Response Code: {r.status_code}")

        if r.ok:
            return True
        else:
            return False

    def update_lldp_location(self, entry_id: str, chassis: str, new_location: RedSkyLocation, description: str):
        payload = {
            'chassisId': chassis,
            'companyId': self.org_id,
            'id': entry_id,
            'locationId': new_location.id,
            'description': description
        }
        r = requests.put("https://api.wxc.e911cloud.com/networking-service/networkSwitch",
                         headers=self._headers, json=payload)
        if r.ok:
            return True
        else:
            raise APIError(f"There was a problem updating the chassis: {r.text}")

    def update_lldp_port_location(self, entry_id: str, chassis_id: str, port: str,
                                  new_location: RedSkyLocation, description: str):
        payload = {
            'description': description,
            'erlId': new_location.id,
            'id': entry_id,
            'networkSwitchId': chassis_id,
            'portId': port
        }
        r = requests.put("https://api.wxc.e911cloud.com/networking-service/networkSwitchPort",
                         headers=self._headers, json=payload)
        if r.ok:
            return True
        else:
            raise APIError(f"There was a problem updating the chassis: {r.text}")

    def _add_chassis_discovery(self, chassis, location, description=""):
        payload = {"chassisId": chassis,
                   "companyId": self.org_id,
                   "locationId": location.id,
                   "description": description}
        r = requests.post("https://api.wxc.e911cloud.com/networking-service/networkSwitch",
                          headers=self._headers, json=payload)
        if r.ok:
            response = r.json()
        else:
            raise APIError(f"There was a problem adding the chassis: {r.text}")
        return response

    def _add_port_discovery(self, chassis_id, port, location, description=""):
        payload = {"erlId": location.id,
                   "portId": port,
                   "description": description,
                   "networkSwitchId": chassis_id}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/networkSwitchPort",
                          headers=self._headers, json=payload)
        if r.ok:
            respose = r.json()
        else:
            raise APIError(f"There was a problem adding the port to the chassis: {r.text}")
        return respose

    def get_bssid_discovery(self):
        """ Get the current BSSID mappings defined in RedSky Horizon

        Returns:
            list[dict]: A list of all the BSSID mappings

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/bssid/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting BSSID mapping: {r.text}")
        return mappings

    def add_bssid_discovery(self, bssid: str, location: "RedSkyLocation", description: str = ""):
        """ Add a new BSSID mapping to RedSky Horizon

        Args:
            bssid (str): The BSSID to add. RedSky isn't picky about formatting or case, so any MAC format should work
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        payload = {"bssid": bssid,
                   "locationId": location.id,
                   "orgId": self.org_id,
                   "description": description}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/bssid",
                          headers=self._headers, json=payload)
        if r.ok:
            added_mapping = r.json()
        else:
            raise APIError(f"There was a problem adding the mapping: {r.text}")
        return added_mapping

    def get_ip_range_discovery(self):
        """ Get the current IP Range mappings defined inRedSky Horizon

        Returns:
            list[dict]: A list of all the IP Range mappings

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/ipRange/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting IP Range mapping: {r.text}")
        return mappings

    def add_ip_range_discovery(self, ip_start: str, ip_end: str, location: "RedSkyLocation", description: str = ""):
        """ Add a new IP Range mapping to RedSky Horizon

        Args:
            ip_start (str): The first IP in the range to add
            ip_end (str): The last IP in the range to add
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        payload = {"ipAddressLow": ip_start,
                   "ipAddressHigh": ip_end,
                   "locationId": location.id,
                   "orgId": self.org_id,
                   "description": description}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/ipRange",
                          headers=self._headers, json=payload)
        if r.ok:
            added_mapping = r.json()
        else:
            raise APIError(f"There was a problem adding the mapping: {r.text}")
        return added_mapping

    @property
    def users(self):
        self._users = RedSkyUsers(parent=self)
        return self._users


class RedSkyUsers(UserList):
    def __init__(self, parent: RedSky):
        log.info("Initializing RedSkyUsers instance")
        super().__init__()
        self.parent = parent
        self.data = []

        # Handle RedSky pagination
        more_data = True
        next_page = 1
        page_size = 100

        while more_data is True:
            r = requests.get(f"https://api.wxc.e911cloud.com/admin-service/deviceUser/company/{self.parent.org_id}",
                             headers=self.parent._headers, params={'page': next_page, 'pageSize': page_size})
            if r.ok:
                data = r.json()
                log.info("Getting RedSky Users")
                log.debug(f"\tPage: {r.headers['X-Pagination-Page']} of {r.headers['X-Pagination-Count']}")
                for user in data:
                    this_user = RedSkyUser(parent=self.parent,
                                           id=user['id'],
                                           email=user['heldUserId'],
                                           raw=user)
                    self.data.append(this_user)
                # Figure out if we need to get more data or not
                if int(r.headers['X-Pagination-Page']) < int(r.headers['X-Pagination-Count']):
                    more_data = True
                    next_page += 1
                else:
                    more_data = False
                    log.debug(f"\tGot {len(self.data)} Users")
            else:
                raise APIError(f"There was a problem getting the RedSky Users")

    def get_by_email(self, email: str) -> Optional[RedSkyUser]:
        for user in self.data:
            if user.email == email:
                return user
        return None


@dataclass
class RedSkyUser:
    parent: RedSky
    id: str
    email: str
    raw: field(repr=False, default_factory=dict)

    @property
    def user_locations(self):
        """ Get the user-defined locations

        These are the locations that the user has entered manually in the Webex app (or the MyE911 app, if they have
        used it)

        Returns:
            list[dict]: List of location information
        """
        log.info("Getting RedSky User locations")
        log.debug(f"User ID: {self.id}")
        r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/locations/deviceUser/{self.id}",
                         headers=self.parent._headers)
        if r.ok:
            data = r.json()
            return data
        else:
            raise APIError(f"There was a problem getting the User's locations")

    @property
    def devices(self):
        """ Get the list of all Webex app devices for the user

        Because the user email is only associated to soft clients, not desk phones, the "devices" returned are only
        computers that have communicated an Emergency Response Location to RedSky. Unfortunately, with the Webex app,
        due to privacy restrictions, it can be difficult to know which device the user is current logged in to.

        Returns:
            list[dict]: A list of the device dictionaries, including the ERL for the device

        """
        log.info(f"Getting devices for RedSky User {self.email}")
        r = requests.get(f"https://api.wxc.e911cloud.com/admin-service/device",
                         headers=self.parent._headers,
                         params={'deviceUserId': self.id})
        if r.ok:
            return r.json()
        else:
            return False


class RedSkyBuilding:
    """A RedSky Horizon Building"""
    def __init__(self, parent: RedSky, config: dict):
        """Initialize a RedSkyBuilding instance.

        Args:
            parent (RedSky): The RedSky instance that this Building belongs to
            config: (dict): The dict returned by the RedSky API containing the Building information

        """
        self._parent: RedSky = parent
        self._raw_config: dict = config
        self.id: str = config.get("id")
        """The ID of the Building"""
        self.name: str = config.get("name")
        """The name of the Building"""
        self.supplemental_data: str = config.get("supplementalData", None)
        """Supplemental data for the Building"""
        self.type: str = config.get("type", "unknown")
        """The type of Building"""
        self.address: dict = config.get("address")
        """The physical address of the building"""
        self._locations: Optional[list] = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def locations(self):
        """A list of RedSkyLocation instances associated with this Building

        Returns:
            list[RedSkyLocation]: List of RedSkyLocation instances

        """
        self._locations = []
        r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/locations/parent/{self.id}",
                         headers=self._parent._headers)
        if r.status_code == 200:
            response = r.json()
            for item in response:
                location = RedSkyLocation(self, item)
                self._locations.append(location)
        else:
            raise APIError(f"There was a problem getting the Locations for Building {self.name}")
        return self._locations

    def get_location_by_name(self, name: str):
        """ Return the RedSkyLocation instance that matches the name provided.

        Args:
            name (str): The name of the location to search for. Not case-sensitive

        Returns:
            RedSkyLocation: The instance of the RedSkyLocation class. None is returned if no match can be found

        """
        for location in self.locations:
            if location.name.lower() == name.lower():
                return location
        return None

    def add_location(self, location_name: str, ecbn: str = "", location_info: str = ""):
        payload = {"name": location_name,
                   "elin": ecbn,
                   "info": location_info,
                   "organizationUnitId": self.id}
        r = requests.post("https://api.wxc.e911cloud.com/geography-service/locations",
                          headers=self._parent._headers, json=payload)
        if r.ok:
            return True
        else:
            raise APIError("Something went wrong adding the Location: {r.text}")


class RedSkyLocation:
    """A RedSky Horizon Location"""
    def __init__(self, parent: RedSkyBuilding, config: dict):
        """Initialize a RedSkyLocation instance

        Args:
            parent (RedSkyBuilding): The RedSkyBuilding instance that this Location belongs to
            config (dict): The dict returned by the RedSky API containing the Location information

        """
        self._parent = parent
        self._raw_config = config
        self.id = config.get("id")
        self.name = config.get("name")
        self.address = config.get("address")
        self.type = config.get("type", "unknown")
        self.suppplemental_data = config.get("supplementalData", None)
        self.org_name_override = config.get("orgNameOverride")
        self.info = config.get("info")
        self.address_entity_name: str = config.get("addressEntityName")
        self.elin: dict = config.get("elin", None)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id



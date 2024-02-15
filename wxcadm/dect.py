from __future__ import annotations

from collections import UserList
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .person import Person
    from .workspace import Workspace

import wxcadm
from wxcadm import log
from .common import *


class DECTHandset:
    pass


class DECTBaseStation:
    def __init__(self, mac: str):
        self.mac: str = mac.upper()
        self.id: Optional[str] = None
        log.info(f"Initializing DECTBaseStation with MAC {mac}")


class DECTNetwork:
    def __init__(self, location: wxcadm.Location, id: str):
        log.info(f"Initializing DECTNetwork with ID {id}")
        self.id: str = id
        self.location: wxcadm.Location = location
        self.base_stations: list = []
        # Since there is no GET, I am not going waste time returning names or other values that were provided to
        # the create()

    def add_base_stations(self, mac_list: list) -> list[DECTBaseStation]:
        """ Add a Base Station to the DECT Network.

        Args:
            mac_list (list[str]): List of MAC addresses as strings

        Returns:
            list[DECTBaseStation]: List of Base Station entries for the DECT Network.

        Raises:
            wxcadm.APIError: Raised when an error is returned by the Webex API

        """
        log.info(f"Adding DECTBaseStations to DECTNetwork {self.id}")
        log.debug(f"MAC List: {mac_list}")
        # Create a DECTBaseStation for now, just to expand later
        payload = []
        for entry in mac_list:
            self.base_stations.append(DECTBaseStation(mac=entry))
            payload.append(entry)
        response = webex_api_call(
            'post',
            f"v1/telephony/config/locations/{self.location.id}/dectNetworks/{self.id}/baseStations",
            payload={'baseStations': payload})
        for entry in response['baseStations']:
            bs = self.get_base_station(mac=entry['mac'])
            bs.id = entry['result']['id']
        return self.base_stations

    def add_handset(self,
                    display_name: str,
                    line1: Person | Workspace,
                    line2: Optional[Person | Workspace] = None
                    ) -> bool:
        """ Add a handset to the DECT Network.

        Args:
            display_name (str): The text to display on the handset. 16 characters max.
            line1 (Person|Workspace): The :class:`Person` or :class:`Workspace` to assign to Line 1 of the handset
            line2 (Person|Workspace, optional): The Person or Workspace to assign to Line 2, if desired.

        Returns:
            bool: True on success. False otherwise.

        Raises:
            wxcadm.exceptions.APIError: Raised if the Webex API returns an error

        """
        log.info(f"Adding a handset to DECT Network {self.id}")
        payload = {
            'line1MemberId': line1.id,
            'customDisplayName': display_name
        }
        if line2:
            payload['line2MemberId'] = line2.id
        response = webex_api_call(
            'post',
            f"v1/telephony/config/locations/{self.location.id}/dectNetworks/{self.id}/handsets",
            payload=payload)
        return response

    def get_base_station(self, mac: str) -> Optional[DECTBaseStation]:
        """ Get the :class:`DECTBaseStation` instance by the Base Station MAC address.

        .. note::

            This currently only works with Base Stations that are being added during the wxcadm session. The Webex API
            does not yet support a method to retrieve existing Base Stations.

        Args:
            mac (str): The MAC address to find

        Returns:
            DECTBaseStation: The DECTBaseStation instance. None is returned if no match is found.

        """
        bs: DECTBaseStation
        for bs in self.base_stations:
            if bs.mac.upper() == mac.upper().strip('-').strip(':'):
                return bs
        return None


class DECTNetworkList(UserList):
    def __init__(self, location: wxcadm.Location):
        log.info("Initializing empty DECTNetworkList")
        super().__init__()
        self.data = []
        self.location: wxcadm.Location = location
        # Note that there is no GET for exiting Networks, Bases or Handsets, so this is really a useless
        # list until they get that figured out. Any device created with .create() will get added, though.

    def create(self,
               name: str,
               model: str,
               default_access_code: Optional[str] = None,
               handset_display_name: Optional[str] = None
               ) -> DECTNetwork:
        """ Create a DECT Network

        Currently model DBS110 and DBS210 are supported. You can pass the model as `'DBS110'`, `'110'`, `'DBS210'` or
        `'210'`.

        Args:
            name (str): The name of the DECT Network
            model (str): The model of the base stations that will be in the DECT Network.
            default_access_code (str, optional): The Default Access Code for all handsets on the DECT Network
            handset_display_name (str, optional): The default Display Name for Handsets

        Returns:
            DECTNetwork: The created :class:`DECTNetwork`

        Raises:
            wxcadm.APIError: Raised when an error is returned by the Webex API

        """
        log.info(f"Creating DECTNetwork {name}")
        # Standardize the model name
        if '110' in model:
            model = 'DMS Cisco DBS110'
            log.debug(f"Normalizing model name to {model}")
        elif '210' in model:
            model = 'DMS Cisco DBS210'
            log.debug(f"Normalizing model name to {model}")
        else:
            log.warning(f"Model {model} not recognized")
            raise ValueError("Model not recognized")
        payload = {
            'name': name,
            'model': model,
            'displayName': handset_display_name
        }
        if default_access_code:
            log.debug(f"Enabling Default Access Code {default_access_code}")
            payload.update({'defaultAccessCodeEnabled': True, 'defaultAccessCode': default_access_code})

        response = webex_api_call('post', f"v1/telephony/config/locations/{self.location.id}/dectNetworks",
                                  payload=payload)
        new_network = DECTNetwork(location=self.location, id=response['id'])
        self.data.append(new_network)
        return new_network

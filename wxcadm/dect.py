from __future__ import annotations

from collections import UserList
from typing import Optional, TYPE_CHECKING, Union
if TYPE_CHECKING:
    from .person import Person
    from .workspace import Workspace

import wxcadm
from wxcadm import log
from .common import *


class DECTHandset:
    def __init__(self, dect_network: DECTNetwork, config: Optional[dict] = None):
        self.dect_network = dect_network
        self.id: Optional[str] = config.get('id', None)
        self.display_name: str = config.get('displayName', '')
        self.access_code: str = config.get('accessCode')
        self.lines: list = config.get('lines', [])

    def delete(self) -> bool:
        """ Delete the Handset

        Returns:
            bool: True on success

        """
        webex_api_call('delete',
                       f'v1/telephony/config/locations/{self.dect_network.location_id}/dectNetworks/'
                       f'{self.dect_network.id}/handsets/{self.id}')
        return True

    def set_handset_display_name(self, display_name: str) -> bool:
        """ Set/change the name displayed on the handset

        Args:
            display_name (str): The new display name

        Returns:
            bool: True on success, False otherwise

        """
        payload = {
            'line1MemberId': self.lines[0]['memberId'],
            'customDisplayName': display_name
        }
        if self.lines[1]:
            payload['line2MemberId'] = self.lines[1]['memberId']
        try:
            webex_api_call(
                'put',
                f'v1/telephony/config/locations/{self.dect_network.location_id}/dectNetworks'
                f'/{self.dect_network.id}/handsets/{self.id}',
                payload=payload)
        except wxcadm.APIError:
            return False
        self.display_name = display_name
        return True


class DECTBaseStation:
    def __init__(self, dect_network: DECTNetwork, config: Optional[dict] = None):
        self.dect_network: DECTNetwork = dect_network
        self.id: Optional[str] = config.get('id', None)
        self.mac: str = config.get('mac', '').upper()
        self.number_of_lines_registered: int = config.get('numberOfLinesRegistered', 0)
        log.info(f"Initializing DECTBaseStation with MAC {self.mac}")

    def delete(self) -> bool:
        """ Delete the Base Station

        Returns:
            bool: True on success

        Raises:
            wxcadm.APIError: Raised when the delete is rejected by Webex
        """
        webex_api_call(
            'delete',
            f'v1/telephony/config/locations/{self.dect_network.location_id}/dectNetworks/'
            f'{self.dect_network.id}/baseStations/{self.id}'
        )
        return True

    def get_handsets(self):
        """ List of :class:`DECTHandset` instances associated with this base station """
        handsets = []
        response = webex_api_call(
            'get',
            f'v1/telephony/config/locations/{self.dect_network.location_id}/dectNetworks/'
            f'{self.dect_network.id}/baseStations/{self.id}'
        )
        for handset in response['handsets']:
            this_handset = DECTHandset(dect_network=self.dect_network, config=handset)
            handsets.append(this_handset)
        return handsets


class DECTNetwork:
    def __init__(self,
                 location: Optional[wxcadm.Location] = None,
                 id: Optional[str] = None,
                 config: Optional[dict] = None):
        # If we were given an ID, even if there was a config present, go fetch the details, but we need the location
        if id is not None:
            if location is None:
                raise ValueError('location must be provided with id')
            else:
                log.debug(f'Getting DECT Network {id} at Location {location.id}')
                config = webex_api_call(
                    'get',
                    f'v1/telephony/config/locations/{location.id}/dectNetworks/{id}'
                )
        log.info(f"Initializing DECTNetwork with Name {config['name']}")
        self.id: str = config.get('id', None)
        self.name: str = config.get('name', '')
        self.display_name: str = config.get('displayName', '')
        self.chain_id: str = config.get('chainId', '')
        self.model: str = config.get('model', '')
        self.default_access_code_enabled: bool = config.get('defaultAccessCodeEnabled', False)
        self.default_access_code: str = config.get('defaultAccessCode', '')
        self.number_of_base_stations: int = config.get('numberOfBaseStations', 0)
        self.number_of_handsets_assigned: int = config.get('numberOfHandsetsAssigned', 0)
        self.number_of_lines: int = config.get('numberOfLines', 0)
        self.location_id: str = config['location'].get('id', None)

    @property
    def handsets(self) -> list:
        handsets = []
        response = webex_api_call(
            'get',
            f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}/handsets'
        )
        for handset in response['handsets']:
            this_handset = DECTHandset(self, config=handset)
            handsets.append(this_handset)
        return handsets

    def delete_base_station(self, base_station: Union[str, DECTBaseStation]) -> list:
        """ Delete a Base Station from this DECT Network.

        The `base_station` parameter can be either a :class:`DECTBaseStation` instance or the Base Station MAC address
        as a string.

        Args:
            base_station (str, DECTBaseStation: The :class:`DECTBaseStation` instance or the MAC address of the Base
            Station to delete

        Returns:
            list: The remaining list of Base Stations

        Raises:
            wxcadm.APIError: Raised when the delete is rejected by Webex

        """
        log.debug('Started DECTNetwork.delete_base_station()')
        if isinstance(base_station, DECTBaseStation):
            log.info(f'Deleting DECT Base Station: {base_station.id} ({base_station.mac.upper()}')
            base_station.delete()
        else:
            for base in self.base_stations:
                if base.mac.upper() == base_station.upper():
                    log.info(f'Deleting DECT Base Station: {base.id} ({base.mac.upper()}')
                    base.delete()
        return self.base_stations

    def delete(self) -> bool:
        """ Delete the DECT Network

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f'Deleting DECT Network {self.id}')
        try:
            webex_api_call(
                'delete',
                f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}'
            )
        except wxcadm.APIError:
            log.error(f'Webex API exception')
            return False
        else:
            log.debug('Success')
            return True

    def set_name(self, name: str, display_name: Optional[str] = None) -> bool:
        """ Set/change the name of the DECT Network

        Args:
            name (str): The new name of the DECT Network
            display_name (str, optional): The Display Name of the DECT Network. Only required if it needs to be changed

        Returns:
            bool: True on success, False otherwise

        """
        if display_name is not None:
            new_display_name = display_name
        else:
            new_display_name = self.display_name
        payload = {
            'name': name,
            'displayName': new_display_name,
            'defaultAccessCodeEnabled': self.default_access_code_enabled,
            'defaultAccessCode': self.default_access_code
        }
        try:
            webex_api_call(
                'put',
                f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}',
                payload=payload
            )
        except wxcadm.APIError:
            return False
        self.name = name
        return True

    def set_display_name(self, display_name: str) -> bool:
        """ Set/change the display name of the DECT Network

        Args:
            display_name (str): The new display name of the DECT Network

        Returns:
            bool: True on success, False otherwise

        """
        payload = {
            'name': self.name,
            'displayName': display_name,
            'defaultAccessCodeEnabled': self.default_access_code_enabled,
            'defaultAccessCode': self.default_access_code
        }
        try:
            webex_api_call(
                'put',
                f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}',
                payload=payload
            )
        except wxcadm.APIError:
            return False
        self.display_name = display_name
        return True

    def enable_default_access_code(self, access_code: Optional[str] = None):
        """ Enable the Default Access Code for handsets.

        If an Access Code has never been defined for the DECT Network, it should be provided using the
        `access_code` parameter. If an Access Code had previously been defined and disabled, it does not need to
        be provided, but can if desired. If a previous Access Code is not present and one is not provided, a
        ValueError will be raised.

        Args:
            access_code (str, optional): The Access Code to set (digits only)

        Returns:
            bool: True on success, False otherwise

        Raises:
            ValueError: Raised when `access_code` is not provided and a previous value does not exist

        """
        if access_code is None:
            if self.default_access_code is None or self.default_access_code == '':
                raise ValueError('access_code does not exist and must be defined')
            else:
                access_code = self.default_access_code
        payload = {
            'name': self.name,
            'displayName': self.display_name,
            'defaultAccessCodeEnabled': True,
            'defaultAccessCode': access_code
        }
        try:
            webex_api_call(
                'put',
                f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}',
                payload=payload
            )
        except wxcadm.APIError:
            return False
        self.default_access_code_enabled = True
        self.default_access_code = access_code
        return True

    def disable_default_access_code(self) -> bool:
        """ Disable the Default Access Code for handsets

        Returns:
            bool: True on success, False otherwise

        """
        payload = {
            'name': self.name,
            'displayName': self.display_name,
            'defaultAccessCodeEnabled': False,
            'defaultAccessCode': self.default_access_code
        }
        try:
            webex_api_call(
                'put',
                f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}',
                payload=payload
            )
        except wxcadm.APIError:
            return False
        self.default_access_code_enabled = False
        return True

    def add_base_stations(self, mac_list: list) -> list[DECTBaseStation]:
        """ Add a Base Station to the DECT Network.

        Args:
            mac_list (list[str]): List of MAC addresses as strings

        Returns:
            list[DECTBaseStation]: List of Base Station entries for the DECT Network, including previously-existing ones

        Raises:
            wxcadm.APIError: Raised when an error is returned by the Webex API

        """
        log.info(f"Adding DECTBaseStations to DECTNetwork {self.id}")
        log.debug(f"MAC List: {mac_list}")
        # Create a DECTBaseStation for now, just to expand later
        payload = []
        for entry in mac_list:
            payload.append(entry)
        try:
            webex_api_call(
                'post',
                f"v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}/baseStations",
                payload={'baseStations': payload})
        except wxcadm.APIError:
            raise wxcadm.APIError
        return self.base_stations

    @property
    def base_stations(self):
        base_stations = []
        response = webex_api_call(
            'get',
            f'v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}/baseStations'
        )
        for item in response['baseStations']:
            this_base = DECTBaseStation(dect_network=self, config=item)
            base_stations.append(this_base)
        return base_stations

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
            f"v1/telephony/config/locations/{self.location_id}/dectNetworks/{self.id}/handsets",
            payload=payload)
        return response

    def delete_handset(self, handset: DECTHandset) -> list:
        """ Delete the specified Handset

        Args:
            handset (DECTHandset): The :class:`DECTHandset` instance to delete

        Returns:
            list: The remaining DECT Handsets. An empty list will be returned if no handsets remain

        """
        remaining = []
        for hs in self.handsets:
            if hs.id == handset.id:
                hs.delete()
            else:
                remaining.append(hs)
        return remaining

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
    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location]):
        log.info("Initializing empty DECTNetworkList")
        super().__init__()
        self.parent = parent
        self.data = self._get_data()

    def _get_data(self):
        log.info("Getting list of DECT Networks")
        networks = []
        if isinstance(self.parent, wxcadm.Location):
            log.debug(f"Using Location {self.parent.name} as Location filter")
            params = {'locationId': self.parent.id}
        elif isinstance(self.parent, wxcadm.Org):
            log.debug(f"Using Org {self.parent.name} as Org filter")
            params = {'orgId': self.parent.id}
        else:
            raise ValueError("Invalid parent class")

        response = webex_api_call('get', 'v1/telephony/config/dectNetworks', params=params)
        for network in response['dectNetworks']:
            this_network = DECTNetwork(config=network)
            networks.append(this_network)
        return networks

    def refresh(self) -> DECTNetworkList:
        """ Refresh the list of DECT Networks from Webex

        Returns:
            DECTNetworkList: The refreshed list of DECT Networks

        """
        self.data = self._get_data()
        return self

    def with_base_stations(self, count: Optional[int] = 1) -> list:
        """ Get a list of :class:`DECTNetwork` instances with at least one Base Station

        Args:
            count(int, optional): The minimum number of Base Stations to include in the response. When omitted, any
            Network with at least 1 Base Station will be returned.

        Returns:
            list: A list of :class:`DECTNetwork` instances

        """
        retval = []
        for network in self.data:
            if network.number_of_base_stations >= count:
                retval.append(network)
        return retval

    def with_handsets(self, count: Optional[int] = 1) -> list:
        """

        Args:
            count:

        Returns:

        """

    def create(self,
               name: str,
               model: str,
               default_access_code: Optional[str] = None,
               handset_display_name: Optional[str] = None,
               location: Optional[wxcadm.Location] = None
               ) -> DECTNetwork:
        """ Create a DECT Network

        Currently model DBS110 and DBS210 are supported. You can pass the model as `'DBS110'`, `'110'`, `'DBS210'` or
        `'210'`.

        Args:
            name (str): The name of the DECT Network
            model (str): The model of the base stations that will be in the DECT Network.
            location (Location, optional): This is only optional when the DECTNetworkList is Location-based
            default_access_code (str, optional): The Default Access Code for all handsets on the DECT Network
            handset_display_name (str, optional): The default Display Name for Handsets

        Returns:
            DECTNetwork: The created :class:`DECTNetwork`

        Raises:
            ValueError: Raised when called on an Org-level DECTNetworkList without a provided `location`
            wxcadm.APIError: Raised when an error is returned by the Webex API

        """
        if location is None and not isinstance(self.parent, wxcadm.Location):
            log.warning('DECTNetworkList.create() called without a location for Org-level list')
            raise ValueError('location must be provided for Org-level create')
        if location is not None and not isinstance(location, wxcadm.Location):
            log.warning('DECTNetworkList.create() received bad value for location')
            raise ValueError('location must be of type wxcadm.Location')
        if location is None and isinstance(self.parent, wxcadm.Location):
            location = self.parent

        log.info(f"Creating DECTNetwork {name} in Location: {location.name}")
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

        response = webex_api_call('post', f"v1/telephony/config/locations/{location.id}/dectNetworks",
                                  payload=payload)
        new_network = DECTNetwork(location=location, id=response['dectNetworkId'])
        self.data.append(new_network)
        return new_network

    def delete(self, network: DECTNetwork):
        """ Delete a DECT Network

        Args:
            network (DECTNetwork): The DECTNetwork instance of the network to be deleted

        Returns:
            DECTNetworkList: The remaining list of DECT Networks

        """
        self.data = self._get_data()
        remaining_networks = []
        log.debug(f'Looking for DECT Network to delete matching ID {network.id}')
        for item in self.data:
            log.debug(f'Checking ID: {item.id}')
            if item.id == network.id:
                log.debug(f'Found DECT Network: {item.id}. Deleting.')
                success = item.delete()
                if success is False:
                    log.warning('DECT Network delete failed')
                    remaining_networks.append(item)
            else:
                remaining_networks.append(item)
        self.data = remaining_networks
        return self

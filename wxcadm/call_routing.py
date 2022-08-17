from __future__ import annotations

from collections import UserList
from dataclasses import dataclass, field
from typing import Union, Optional

import wxcadm.location
from wxcadm import log
from .common import *


class CallRouting:
    def __init__(self, org: Org):
        self.org = org
        """ The Org to which the Call Routing is associated """
        pass

    @property
    def trunks(self):
        """ The ":py:class:`Trunks` instance for this Org """
        return Trunks(self.org)

    @property
    def route_groups(self):
        """ The :py:class:`RouteGroups` instance for this Org """
        return RouteGroups(self.org)

    @property
    def route_lists(self):
        """ The :py:class:`RouteLists` instance for this Org """
        return RouteLists(self.org)

    @property
    def dial_plans(self):
        """ The :py:class:`DialPlans` instance for this Org """
        return DialPlans(self.org)

    def test(self, originator: Union[wxcadm.person.Person, Trunk],
             destination: str,
             orig_number: Optional[str] = None):
        # First, figure out if the originator is a Person or a Trunk
        if isinstance(originator, wxcadm.person.Person):
            originator = originator.id
            orig_type = 'USER'
        elif isinstance(originator, Trunk):
            originator = originator.id
            orig_type = 'TRUNK'
        else:
            log.warning("CallRouting.test() called without a Person or Trunk instance")
            raise ValueError('originator argument must be a Person or Trunk instance')

        payload = {'originatorId': originator,
                   'originatorType': orig_type,
                   'destination': destination}
        if orig_type == 'TRUNK' and orig_number is not None:
            payload['originatorNumber'] = orig_number

        response = webex_api_call('post', '/v1/telephony/config/actions/testCallRouting/invoke',
                                  params={'orgId': self.org.id}, payload=payload)
        return response




class Trunks(UserList):
    def __init__(self, org: Org):
        log.info('Initializing Trunks instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/trunks')
        log.debug(f'Trunks from Webex: {items}')
        for item in items['trunks']:
            this_trunk = Trunk(self.org, **item)
            self.data.append(this_trunk)

    def add_trunk(self, name: str,
                  location: Union[Location, str],
                  password: str,
                  dual_identity_support: bool,
                  type: str,
                  device_type: Optional[str] = 'Cisco Unified Border Element',
                  address: Optional[str] = None,
                  domain: Optional[str] = None,
                  port: Optional[int] = None,
                  max_concurrent_calls: Optional[int] = None):
        """ Create a Trunk for the organization.

        A Trunk is a connection between Webex Calling and the premises, which terminates on the premises with a local
        gateway or other supported device. The trunk can be assigned to a Route Group - a group of trunks that allow
        Webex Calling to distribute calls over multiple trunks or to provide redundancy.

        Args:
            name (str): A unique name for the Trunk
            location (Location): The Location instance to add the Trunk to. Also supports a Location ID as a string.
            password (str): The password to use with the Trunk
            dual_identity_support (bool): The Dual Identity Support setting impacts the handling of the From header and
                P-Asserted-Identity (PAI) header when sending an initial SIP INVITE to the trunk for an outbound call.
                When True, the From and PAI headers are treated independently and may differ. When False, the PAI header
                is set to the same value as the From header. Please refer to the documentation for more details.
            type (str): Either 'REGISTERING' or 'CERTIFICATE_BASED'
            device_type (str, optional): The type of device. Defaults to 'Cisco Unified Border Element'
            address (str, optional): FQDN or SRV address. Required to create a static certificate-based trunk.
            domain (str, optional): Domain name. Required to create a static certificate based trunk.
            port (int, optional): FQDN port. Required to create a static certificate-based trunk.
            max_concurrent_calls (int, optional): Max Concurrent call. Required to create a static certificate based
                trunk.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f'Adding Trunk: {name}')
        if isinstance(location, wxcadm.location.Location):
            location_id = location.id
        elif isinstance(location, str):
            location_id = location
        else:
            log.warning(f'Cannot determine Location ID with given location: {location}')
            return False

        payload = {'name': name,
                   'locationId': location_id,
                   'password': password,
                   'dualIdentitySupportEnabled': dual_identity_support,
                   'trunkType': type}
        if type.upper() == 'CERTIFICATE_BASED':
            payload['deviceType'] = device_type
            payload['address'] = address
            payload['domain'] = domain
            payload['port'] = port
            payload['maxConcurrentCalls'] = max_concurrent_calls

        success = webex_api_call('post', '/v1/telephony/config/premisePstn/trunks',
                                 params={'orgId': self.org.id},
                                 payload=payload)
        if success:
            return True
        else:
            return False


@dataclass
class Trunk:
    org: Org = field(repr=False)
    """ The Org to which the Trunk belongs """
    id: str
    """ The unique identifier of the Trunk """
    name: str
    """ The text name of the Trunk """
    location: Union[dict, Location]
    """ The Location instance associated with the Trunk """
    inUse: bool
    """ Whether the Trunk is in use """
    trunkType: str
    """ The type of Trunk, either 'REGISTERING' or 'CERTIFICATE_BASED' """

    def __post_init__(self):
        log.debug(f'Finding Location instance: {self.location}')
        # Since we only have a dict of the trunk location, go get the actual Location instance
        my_location = self.org.get_location(id=self.location['id'])
        if my_location is not None:
            self.location = my_location


class RouteGroups(UserList):
    def __init__(self, org: Org):
        log.info('Initializing RouteGroups instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/routeGroups', params={'orgId': self.org.id})
        log.debug(f'Route Groups from Webex: {items}')
        for item in items['routeGroups']:
            this_rg = RouteGroup(self.org, **item)
            self.data.append(this_rg)

    def get_route_group(self, id: Optional[str] = None, name: Optional[str] = None) -> RouteGroup:
        """ Return a RouteGroup instance with the given ID or name.

        Args:
            id (str, optional): The RouteGroup ID
            name (str, optional): The RouteGroup name

        Returns:
            RouteGroup: The matching RouteGroup instance. None is returned if no match is found.

        """
        for rg in self.data:
            if rg.id == id or rg.name == name:
                return rg
        return None


@dataclass
class RouteGroup:
    org: Org = field(repr=False)
    """ The Org to which the RouteGroup belongs """
    id: str
    """ The unique identifier for the RouteGroup """
    name: str
    """ The name of the RouteGroup """
    inUse: bool
    """ Whether or not the RouteGroup is being used by any Location, Route List or Dial Plan"""


class RouteLists(UserList):
    # TODO - Create Route List, Delete Route List
    def __init__(self, org: Org):
        log.info('Initializing RouteLists instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/routeLists')
        log.debug(f'Route Lists from Webex: {items}')
        for item in items['routeLists']:
            this_rl = RouteList(self.org, **item)
            self.data.append(this_rl)


@dataclass
class RouteList:
    # TODO - Delete Route List
    org: Org = field(repr=False)
    """ The Org to which the RouteList belongs """
    id: str = field(repr=False)
    """ The unique identifier for the RouteList """
    name: str
    """ The name of the RouteList """
    locationId: str
    locationName: str
    routeGroupId: str
    routeGroupName: str

    def __post_init__(self):
        # This cleans up the Location and Route Group references so that they get the wxcadm instances for each
        self.route_group = self.org.call_routing.route_groups.get_route_group(id=self.routeGroupId)
        del self.routeGroupId, self.routeGroupName
        self.location = self.org.get_location(id=self.locationId)
        del self.locationId, self.locationName

    @property
    def numbers(self):
        """ The numbers assigned to this RouteList """
        response = webex_api_call('get', f'/v1/telephony/config/premisePstn/routeLists/{self.id}/numbers')
        return response.json()


class DialPlans(UserList):
    def __init__(self, org: Org):
        log.info('Initializing DialPlans instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/dialPlans')
        log.debug(f'Dial Plans from Webex: {items}')
        for item in items['dialPlans']:
            this_dp = DialPlan(self.org, **item)
            self.data.append(this_dp)

@dataclass
class DialPlan:
    org: Org = field(repr=False)
    id: str = field(repr=False)
    name: str
    routeId: str
    routeName: str
    routeType: str

    _patterns: Optional[list] = field(init=False, default=None)

    @property
    def patterns(self):
        """ The Dial Patters within the DialPlan"""
        response = webex_api_call('get', f'/v1/telephony/config/premisePstn/dialPlans/{self.id}/dialPatterns')
        self._patterns = response['dialPatterns']
        return self._patterns

    def add_pattern(self, pattern: str) -> bool:
        """ Add a new dial pattern to the DialPlan

        Args:
            pattern (str): The pattern to add. This should be a valid Webex Dial Plan pattern.

        Returns:
            bool: True on success, False otherwise

        """
        payload = {'dialPatterns': [{'dialPattern': pattern, 'action': 'ADD'}]}
        success = webex_api_call('put', f'/v1/telephony/config/premisePstn/dialPlans/{self.id}/dialPatterns',
                                 payload=payload)
        if success:
            return True
        else:
            return False

    def delete_pattern(self, pattern: str) -> bool:
        """ Delete a dial pattern from the DialPlan

        Args:
            pattern (str): The pattern to delete. The patter should already exist in the DialPlan

        Returns:
            bool: True on success, False otherwise

        """
        payload = {'dialPatterns': [{'dialPattern': pattern, 'action': 'DELETE'}]}
        success = webex_api_call('put', f'/v1/telephony/config/premisePstn/dialPlans/{self.id}/dialPatterns',
                                 payload=payload)
        if success:
            return True
        else:
            return False


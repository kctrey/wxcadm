from __future__ import annotations

from collections import UserList
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from typing import Optional, Union, List

import wxcadm
import wxcadm.location
import wxcadm.person
from wxcadm import log
from .common import *
from .models import OutboundProxy


class CallRouting:
    def __init__(self, org: wxcadm.Org):
        self.org = org
        """ The Org to which the Call Routing is associated """
        pass

    @property
    def trunks(self):
        """ The :py:class:`Trunks` instance for this Org """
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

    def test(self, originator: wxcadm.person.Person | Trunk,
             destination: str,
             orig_number: Optional[str] = None) -> dict:
        """ Test the Call Routing for a call.

        This method accepts the `originator` as either a :py:class:`Person` instance or a :py:class:`Trunk` instance,
        depending on whether the call is being placed by a user or arriving at Webex Calling over a Trunk.

        Args:
            originator (Person, Trunk): The Person or Trunk instance to test origination from
            destination (str): The destination number
            orig_number (str): For Trunk-originated calls, the originator number

        Returns:
            dict: Since the responses are dynamic, the full response dict from the Webex API is returned.

        """
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
    """ Trunks is a class that behaves as an array. Each item in the array is a :py:class:`Trunk` instance."""
    def __init__(self, org: wxcadm.Org):
        log.info('Initializing Trunks instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/trunks')
        log.debug(f'Trunks from Webex: {items}')
        for item in items['trunks']:
            item['org'] = self.org
            this_trunk = Trunk.from_dict(item)
            self.data.append(this_trunk)

    def get(self, name: Optional[str] = None, id: Optional[str] = None) -> Optional[Trunk]:
        """ Get a Trunk by name or ID

        Args:
            name: The name of the Trunk
            id: The Trunk ID

        Returns:

        """
        if name is None and id is None:
            raise ValueError("Must provide name or id")
        for trunk in self.data:
            if trunk.id == id:
                return trunk
            if trunk.name == name:
                return trunk
        return None

    def add_trunk(self, name: str,
                  location: wxcadm.Location | str,
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


@dataclass_json
@dataclass
class Trunk:
    org: wxcadm.Org = field(repr=False)
    """ The Org to which the Trunk belongs """
    id: str
    """ The unique identifier of the Trunk """
    name: str
    """ The text name of the Trunk """
    location: dict | wxcadm.Location
    """ The Location instance associated with the Trunk """
    in_use: bool = field(metadata=config(field_name="inUse"))
    """ Whether the Trunk is in use """
    trunk_type: str = field(metadata=config(field_name="trunkType"))
    """ The type of Trunk, either 'REGISTERING' or 'CERTIFICATE_BASED' """
    dedicated_instance_only: bool = field(metadata=config(field_name="isRestrictedToDedicatedInstance"))
    """ Whether the Trunk can only be used by Webex Calling Dedicated Instance"""

    # Fields from a detail GET. They will be populated with a __getattr__ later
    otg_dtg: str = field(init=False, repr=False)
    """ The OTG/DTG value for the Trunk"""
    lineport: str = field(init=False, repr=False)
    """ The Line/Port identifier for the Trunk """
    used_by_locations: list[dict] = field(init=False, repr=False)
    """ List of Locations using the Trunk for PSTN routing """
    pilot_user_id: str = field(init=False, repr=False)
    """ The Pilot User ID for the Trunk """
    outbound_proxy: Optional[OutboundProxy] = field(init=False, repr=False)
    """ The :class:`~.models.OutboundProxy` for the Trunk """
    sip_auth_user: str = field(init=False, repr=False)
    """ The SIP Auth User ID for the Trunk """
    status: str = field(init=False, repr=False)
    """ The status of the Trunk """
    response_status: list = field(init=False, repr=False)
    """ List of status messages for the Trunk """
    dual_identity_support: bool = field(init=False, repr=False)
    """ Whether the Trunk supports Dual Identity """
    device_type: str = field(init=False, repr=False)
    """ The type of the device """
    max_calls: int = field(init=False, repr=False)
    """ The Max Concurrent Calls """

    def __post_init__(self):
        log.debug(f'Finding Location instance: {self.location}')
        # Since we only have a dict of the trunk location, go get the actual Location instance
        my_location = self.org.locations.get(id=self.location['id'])
        if my_location is not None:
            self.location = my_location

    def __getattr__(self, item):
        # The following is a crazy fix for a PyCharm debugger bug. It serves no purpose other than to stop extra API
        # calls when developing in PyCharm. See the following bug:
        # https://youtrack.jetbrains.com/issue/PY-48306
        if item == 'shape':
            return None
        log.debug(f"Collecting details for Trunk: {self.id}")
        response = webex_api_call('get', f"v1/telephony/config/premisePstn/trunks/{self.id}",
                                  params={'orgId': self.org.id})
        self.otg_dtg = response.get('otgDtgId', '')
        self.lineport = response.get('linePort', '')
        self.used_by_locations = response.get('locationsUsingTrunk', [])
        self.pilot_user_id = response.get('pilotUserId', '')
        proxy_dict = response.get('outboundProxy', None)
        if proxy_dict is not None:
            proxy = OutboundProxy.from_dict(proxy_dict)
            self.outbound_proxy = proxy
        else:
            self.outbound_proxy = None
        self.sip_auth_user = response.get('sipAuthenticationUserName', '')
        self.status = response.get('status', '')
        self.response_status = response.get('responseStatus', [])
        self.dual_identity_support = response.get('dualIdentitySupportEnabled', False)
        self.device_type = response.get('deviceType', '')
        self.max_calls = response.get('maxConcurrentCalls', 0)
        return self.__getattribute__(item)

    def set_dual_identity_support(self, enabled: bool):
        """ Set the Dual Identity Support flag for the Trunk

        The Dual Identity Support setting impacts the handling of the From header and P-Asserted-Identity (PAI) header
        when sending an initial SIP INVITE to the trunk for an outbound call. When enabled, the From and PAI headers
        are treated independently and may differ. When disabled, the PAI header is set to the same value as the From
        header. Please refer to the documentation for more details.

        Args:
            enabled (bool): Whether the Dual Identity Support flag is enabled or disabled

        Returns:
            bool: True on success, False otherwise

        Raises:
            wxcadm.ApiError: Raised when the command is rejected by the Webex API

        """
        log.debug(f'Setting Dual Identity Support on trunk: {self.id} to {enabled}')
        payload = {
            "dualIdentitySupportEnabled": enabled,
        }
        webex_api_call("put", f"v1/telephony/config/premisePstn/trunks/{self.id}",
                       payload=payload, params={'orgId': self.org.id})
        self.dual_identity_support = enabled
        return True

    def set_max_calls(self, calls: int):
        """ Sets the maximum number of Concurrent Calls for the Trunk

        .. note::
            Setting the maximum number of Concurrent Calls for the Trunk is only supported for certificate-based trunks.

        Args:
            calls (int): The maximum number of Concurrent Calls for the Trunk

        Returns:
            bool: True on success, False otherwise

        Raises:
            ValueError: Raised when trying to set the max calls value on a registration-based Trunk
            wxcadm.ApiError: Raised when the command is rejected by the Webex API

        """
        log.debug(f'Setting Max Concurrent Calls on trunk: {self.id} to {calls}')
        if self.trunkType == "REGISTERING":
            log.warning("Cannot set max_calls on REGISTERING Trunk")
            return ValueError("Cannot set max_calls on REGISTERING Trunk")
        payload = {
            "maxConcurrentCalls": calls
        }
        webex_api_call("put", f"v1/telephony/config/premisePstn/trunks/{self.id}",
                       payload=payload, params={'orgId': self.org.id})
        self.max_calls = calls
        return True


class RouteGroups(UserList):
    """ RouteGroups is a class that behaves as an array. Each item in the array is a :py:class:`RouteGroup` instance."""
    def __init__(self, org: wxcadm.Org):
        log.info('Initializing RouteGroups instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/routeGroups', params={'orgId': self.org.id})
        log.debug(f'Route Groups from Webex: {items}')
        for item in items['routeGroups']:
            this_rg = RouteGroup(self.org, **item)
            self.data.append(this_rg)

    def get(self, id: Optional[str] = None, name: Optional[str] = None) -> Optional[RouteGroup]:
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
    org: wxcadm.Org = field(repr=False)
    """ The Org to which the RouteGroup belongs """
    id: str
    """ The unique identifier for the RouteGroup """
    name: str
    """ The name of the RouteGroup """
    inUse: bool
    """ Whether or not the RouteGroup is being used by any Location, Route List or Dial Plan"""

    @property
    def trunks(self) -> List[dict]:
        """ A dict of the Trunks within the Route Group along with their Priorities """
        response = webex_api_call('get', f"v1/telephony/config/premisePstn/routeGroups/{self.id}",
                                  params={'orgId': self.org.org_id})
        return response['localGateways']

    def add_trunk(self, trunk: Trunk, priority: Union[str, int]):
        """ Add a new Trunk to the Route Group with the given priority

        The priority value will be a fixed number value (int) for the given priority. For a Route Group with an unknown
        number of existing Trunks, the keyword ``'next'`` can be used to assign the priority as the next numerical
        value, or the keyword ``'with_last'`` will assign the priority to the same value as other trunks with the last
        priority value.

        Args:
            trunk (Trunk): The :class:`Trunk` to add
            priority (str, int): Either a numeric priority or the word ``'next'`` or ``'with_last'``

        Returns:

        """
        trunks = self.trunks
        if priority == 'next' or priority =='with_last':
            highest_val = self.__get_last_priority(trunks)
            if priority == 'next':
                priority = int(highest_val) + 1
            else:
                priority = int(highest_val)

        trunks.append(
            {
                'id': trunk.id,
                'name': trunk.name,
                'locationId': trunk.location.id,
                'priority': priority
            }
        )
        payload = {
            'name': self.name,
            'localGateways': trunks
        }

        webex_api_call('put', f"v1/telephony/config/premisePstn/routeGroups/{self.id}",
                       params={'orgId': self.org.org_id}, payload=payload)
        return True

    def __get_last_priority(self, trunks: Optional[dict] = None):
        if trunks is None:
            trunks = self.trunks
        highest = 1
        for trunk in trunks:
            if trunk['priority'] > highest:
                highest = trunk['priority']
        return highest


class RouteLists(UserList):
    """ RouteLists is a class that behaves as an array. Each item in the array is a :py:class:`RouteList` instance."""
    # TODO - Create Route List, Delete Route List
    def __init__(self, org: wxcadm.Org):
        log.info('Initializing RouteLists instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/routeLists')
        log.debug(f'Route Lists from Webex: {items}')
        for item in items['routeLists']:
            this_rl = RouteList(self.org, **item)
            self.data.append(this_rl)

    def get(self, name: Optional[str] = None, id: Optional[str] = None) -> Optional[RouteLists]:
        """ Get a RouteList by name or ID

        Args:
            name: The name of the RouteList
            id: The RouteList ID

        Returns:
            RouteList

        """
        if name is None and id is None:
            raise ValueError("Must provide name or id")
        for routelist in self.data:
            if routelist.id == id:
                return routelist
            if routelist.name == name:
                return routelist
        return None


@dataclass
class RouteList:
    # TODO - Delete Route List
    org: wxcadm.Org = field(repr=False)
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
        self.location = self.org.locations.get(id=self.locationId)
        del self.locationId, self.locationName

    @property
    def numbers(self):
        """ The numbers assigned to this RouteList """
        response = webex_api_call('get', f'/v1/telephony/config/premisePstn/routeLists/{self.id}/numbers')
        return response.json()


class DialPlans(UserList):
    """ DialPlans is a class that behaves as an array. Each item in the array is a :py:class:`DialPlan` instance."""
    def __init__(self, org: wxcadm.Org):
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
    org: wxcadm.Org = field(repr=False)
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
            pattern (str): The pattern to delete. The pattern should already exist in the DialPlan

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


class TranslationPattern:
    def __init__(self,
                 parent: Union[wxcadm.Org, wxcadm.Location],
                 config: Optional[dict] = None):
        log.info("Creating TranslationsPattern instance")
        self.parent = parent
        self.id: Optional[str] = None
        self.name: Optional[str] = None
        self.match_pattern: Optional[str] = None
        self.replacement_pattern: Optional[str] = None
        self.location: Optional[wxcadm.Location] = None
        self.__process_config(config)

    def __process_config(self, config: dict):
        log.debug(f"Processing config: {config}")
        self.id = config.get('id')
        self.name = config.get('name', '')
        self.match_pattern = config.get('matchingPattern')
        self.replacement_pattern = config.get('replacementPattern')
        self.level = config.get('level', None)
        if config.get('location', None) is not None:
            self.location = location_finder(config['location']['id'], self.parent)

    def update(self,
               name: Optional[str] = None,
               match_pattern: Optional[str] = None,
               replacement_pattern: Optional[str] = None):
        """ Update a Translation Pattern

        Args:
            name (str, optional): The new name of the Translation Pattern. Defaults to no change.
            match_pattern (str, optional): The new match pattern. Defaults to no change.
            replacement_pattern (str, optional): The new replacement pattern. Defaults to no change.

        Returns:
            bool: True on success

        """
        log.info(f"Updating TranslationPattern {self.id}")
        payload = {'name': name if name is not None else self.name,
                   'matchingPattern': match_pattern if match_pattern is not None else self.match_pattern,
                   'replacementPattern': replacement_pattern if replacement_pattern is not None \
                       else self.replacement_pattern}
        url = f'v1/telephony/config/callRouting/translationPatterns/{self.id}' if self.location is None \
            else f'v1/telephony/config/locations/{self.location.id}/callRouting/translationPatterns/{self.id}'
        response = webex_api_call('put', url, params={'orgId': self.parent.org_id}, payload=payload)
        log.debug(f"Response: {response}")
        return True

    def delete(self):
        """ Delete the Translation Pattern

        Returns:
            bool: True on success

        """
        log.info(f"Deleting Translation Pattern {self.id}")
        url = f'v1/telephony/config/callRouting/translationPatterns/{self.id}' if self.location is None \
            else f'v1/telephony/config/locations/{self.location.id}/callRouting/translationPatterns/{self.id}'
        webex_api_call('delete', url, params={'orgId': self.parent.org_id})
        return True


class TranslationPatternList(UserList):
    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location]):
        super().__init__()
        self.parent: Union[wxcadm.Org, wxcadm.Location] = parent
        self.data: list[wxcadm.TranslationPattern] = self._get_data()

    def _get_data(self):
        data = []
        params = {
            'orgId': self.parent.org_id
        }
        if isinstance(self.parent, wxcadm.Location):
            params['limitToLocationId'] = self.parent.id
        response = webex_api_call('get', "v1/telephony/config/callRouting/translationPatterns", params=params)
        for entry in response['translationPatterns']:
            data.append(TranslationPattern(self.parent, entry))
        return data

    def refresh(self):
        """ Refresh the list of Translations Patterns """
        self.data = self._get_data()
        return self.data

    def get(self,
            id: Optional[str] = None,
            name: Optional[str] = None,
            match_pattern: Optional[str] = None,
            replacement_pattern: Optional[str] = None,
            ):

        for entry in self.data:
            if entry.id == id or id is None:
                if entry.name == name or name is None:
                    if entry.match_pattern == match_pattern or match_pattern is None:
                        if entry.replacement_pattern == replacement_pattern or replacement_pattern is None:
                            return entry

        return None

    def create(self,
               name: str,
               match_pattern: str,
               replacement_pattern: str,
               location: Optional[wxcadm.Location] = None):
        """ Create a new Translation Pattern

        If this method is called for a :class:`TranslationPatternList` at the Org level, the ``location`` argument is
        optional, and, if omitted, the Translation Pattern will be created at the Org level. If the
        :class:`TranslationPatternList` is at the Location level, the ``location`` argument is still optional but will
        default to the Location of the list.

        Args:
            name (str): The name of the Translation Pattern
            match_pattern (str): The pattern to match
            replacement_pattern (str): The replacement pattern to apply to a match
            location (Location, optional): The :class:`Location` to create the Translation Pattern for

        Returns:
            TranslationPattern: The newly-created Translation Pattern.

        """
        log.info(f"Creating Translation Pattern. Name: {name}, Match: {match_pattern}, Replace: {replacement_pattern}")
        payload = {
            'name': name,
            'matchingPattern': match_pattern,
            'replacementPattern': replacement_pattern
        }
        scope = 'org'
        if location is not None:
            log.info(f"Location received in arg: {location.name}")
            url = f"v1/telephony/config/locations/{location.id}/callRouting/translationPatterns"
            scope = 'location'
            location_id = location.id
        else:
            if isinstance(self.parent, wxcadm.Location):
                log.info(f"No Location received. Using Location scope from parent: {self.parent.name}")
                url = f"v1/telephony/config/locations/{self.parent.id}/callRouting/translationPatterns"
                scope = 'location'
                location_id = self.parent.id
            else:
                log.info("No Location defined. Using Org scope.")
                url = f"v1/telephony/config/callRouting/translationPatterns"
                scope = 'org'

        response = webex_api_call('post', url, params={'orgId': self.parent.org_id}, payload=payload)
        pattern_id = response['id']
        log.debug(f"New Pattern ID: {pattern_id}")
        log.debug("Getting new pattern details")
        if scope == 'org':
            config = webex_api_call('get', f"v1/telephony/config/callRouting/translationPatterns/{pattern_id}",
                                    params={'orgId': self.parent.org_id})
            new_pattern = TranslationPattern(self.parent, config)
        else:
            config = webex_api_call(
                'get',
                f"v1/telephony/config/locations/{location_id}/callRouting/translationPatterns/{pattern_id}",
                params={'orgId': self.parent.org_id}
            )
            new_pattern = TranslationPattern(self.parent, config)
        return new_pattern


from __future__ import annotations
from collections import UserList
from typing import TYPE_CHECKING
import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
import logging
import wxcadm
from .common import *
from typing import Optional, Union
from .exceptions import *
from wxcadm import log
from .virtual_line import VirtualLine
if TYPE_CHECKING:
    from .person import Person
    from .workspace import Workspace


class DeviceLayout:
    def __init__(self, device: Device, config: Optional[dict] = None):
        self.device = device
        """ The :class:`Device` associated with this layout """
        self.layout_mode: str = ''
        """ The Layout Mode """
        self.user_reorder_enabled: bool = False
        """ Whether the user can re-order the items in the list """
        self.line_keys: list = []
        """ The list of line keys for the configured lines """
        self.kem_type: Optional[str] = None
        """ The type of KEM used by the Device Layout """
        self.kem_keys: Optional[list] = None
        """ The list of keys used by the KEM """

        if config is None:
            self._get_config()
        else:
            self._parse_config(config)

    def _parse_config(self, config: dict):
        self.layout_mode = config.get('layoutMode', '')
        self.user_reorder_enabled = config.get('userReorderEnabled', False)
        self.line_keys = config.get('lineKeys', [])
        self.kem_type = config.get('kemModuleType', None)
        self.kem_keys = config.get('kemKeys', None)

    def _get_config(self):
        response = webex_api_call('get', f'v1/telephony/config/devices/{self.device.id}/layout',
                                  params={'orgId': self.device.parent.org_id})
        self._parse_config(response)


class Device:
    def __init__(self, parent: wxcadm.Org | Person | Workspace,
                 config: Optional[dict] = None,
                 id: Optional[str] = None):
        self.parent = parent
        """ The :py:class:`Org`, :py:class:`Person` or :py:class:`Workspace` that created this instance """

        # The logic below addresses the case where the Device owner is a Person, because of how we have to get the
        # list of devices
        if "connectionStatus" not in config.keys():
            try:
                config = webex_api_call('get', f'/v1/devices/{id}', params={'orgId': self.parent.org_id})
            except wxcadm.APIError:
                pass

        self.id: str = config['id']
        """ The Device ID """
        self.tags: list = config.get('tags', config.get('description', []))
        """ The device tags """
        self.model: str = config.get('model', config.get('product', ''))
        """ The model name of the device """
        self.mac: str = config.get('mac')
        """ The device MAC address """
        self.is_owner: bool = config.get('primaryOwner', False)
        """ Whether the Person or Workspace is the primary owner of the device """
        self.activation_state: Optional[str] = config.get('activationState', None)
        """ The device activation state """
        self.type: str = config['type']
        """ The type of device association """
        self.ip_address: Optional[str] = config.get('ipAddress', config.get('ip', ''))
        """ The IP Address of the device """
        self._settings: Optional[dict] = None
        self.display_name = config.get('displayName', None)
        """ The name of device as displayed in Webex """
        self.capabilities: list = config.get('capabilities', [])
        """ The capabilities of the device """
        self.user_permissions: list = config.get('permissions', [])
        """ The permissions the user has for this device. For example, "xapi" means this user is allowed to use xapi """
        self.connection_status: Optional[str] = config.get('connectionStatus', None)
        """ Whether the device is connected or not """
        self.serial: Optional[str] = config.get('serial', None)
        """ The serial number of the device, if available """
        self.software: Optional[str] = config.get('software', None)
        """ The operating system name data and version tag, if available """
        self.upgrade_channel: Optional[str] = config.get('upgradeChannel', None)
        """ The upgrade channel the device is assigned to """
        self.created: Optional[str] = config.get('created', None)
        """ The date and time that the device was created on Webex """
        self.first_seen: Optional[str] = config.get('firstSeen', None)
        """ The date and time that the device was first seen online """
        self.last_seen: Optional[str] = config.get('lastSeen', None)
        """ The date and time that the device was last seen online """
        self.owner = None
        """ The :py:class:`Person` or :py:class:`Workspace` that owns the device primarily """
        self.workspace_location_id: Optional[str] = config.get('workspaceLocationId', None)
        """ The WorkspaceLocation ID of the device, which indicates the WorkspaceLocation of the primary
            Person or Workspace
            
            .. deprecated:: 3.4.0
            The Workspace Location concept is being removed from the Webex APIs. All Workspace Locations are now simply
            :class:`Location`s now. This class will still show up in come cases until it is completely removed. Use
            :attr:`Device.location_id` instead. 
            
        """
        self.location_id: Optional[str] = config.get('locationId', None)
        """ The Location ID of the device, which indicates the Location of the primary Person or Workspace """
        self._device_members = None
        self._layout = None

        if 'personId' in config.keys() and isinstance(self.parent, wxcadm.Org):
            self.owner = self.parent.get_person_by_id(config['personId'])
            if self.owner is None:
                self.owner = config['personId']
        elif 'workspaceId' in config.keys() and isinstance(self.parent, wxcadm.Org):
            self.owner = self.parent.workspaces.get_by_id(config['workspaceId'])

    @property
    def layout(self) -> DeviceLayout:
        """ The :class:`DeviceLayout` for the Device """
        if self._layout is None:
            self._layout = DeviceLayout(self)
        return self._layout

    def set_layout(self, layout: DeviceLayout):
        """ Use the provided :class:`DeviceLayout` as the new layout for the Device.

        .. note::

            Due to the complexity of the DeviceLayout, the lists and dicts for each line section are represented as
            they are defined by the Webex Developer documents. See the documented format at:
            https://developer.webex.com/docs/api/v1/device-call-settings/modify-device-layout-by-device-id

        Args:
            layout (DeviceLayout: The :class:`DeviceLayout` to apply

        Returns:
            bool: True on success

        """
        payload = {
            'layoutMode': layout.layout_mode,
            'userReorderEnabled': layout.user_reorder_enabled,
            'lineKeys': layout.line_keys
        }
        if layout.kem_type is not None:
            payload['kemModuleType'] = layout.kem_type
        if layout.kem_keys is not None:
            payload['kemKeys'] = layout.kem_keys

        webex_api_call('put', f"v1/telephony/config/devices/{self.id}/layout", payload=payload,
                       params={'orgId': self.parent.org_id})
        return True

    def change_tags(self, operation: str, tag: Optional[Union[str, list]] = None):
        """ Add a tag to the list of tags for this device

        It is also possible to change the tags by modifying the ``settings`` directly, but this method ensures that
        no other settings are touched.

        Args:
            operation (str): Valid values are:
                "add" - Add a tag or list of tags to the existing tags
                "remove" - Remove all tags for the device
                "replace" - Replace all tags with the provided tag or list of tags
            tag (str, list, optional): The tag value or list of values. Valid for "add" and "replace" operations.

        Returns:

        """
        # Value checking
        if (operation.lower() in ['add', 'replace']) and tag is None:
            raise ValueError("add or replace operations require a 'tag' param")
        if isinstance(tag, str):
            tag = [tag]

        payload = {
            "op": operation.lower(),
            "path": "tags",
            "value": tag
        }
        webex_api_call("patch", f"/v1/devices/{self.id}", payload=payload, params={'orgId': self.parent.org_id})

        return True

    @property
    def config(self) -> dict:
        """ Returns the device configuration as a dictionary """
        response = webex_api_call('get', f'/v1/telephony/config/devices/{self.id}')
        return response

    @property
    def settings(self):
        """ The device settings.

        The available settings vary by device type, so the raw dictionary from Webex is returned.

        """
        if self._settings is None:
            response = webex_api_call('get', f'/v1/telephony/config/devices/{self.id}/settings',
                                      params={'model': self.model, 'orgId': self.parent.org_id})
            self._settings = response
        return self._settings

    @settings.setter
    def settings(self, config: dict):
        try:
            webex_api_call('put', f'v1/telephony/config/devices/{self.id}/settings',
                                  payload=config, params={'orgId': self.parent.org_id})
        except APIError:
            logging.warning("The API call to set the device settings failed")

        self._settings = config

    def apply_changes(self) -> bool:
        """ Issues request to the device to download and apply changes to the configuration.

        Returns:
            bool: True on success, False otherwise

        """
        try:
            webex_api_call('post', f'v1/telephony/config/devices/{self.id}/actions/applyChanges/invoke',
                           params={'orgId': self.parent.org_id})
        except APIError:
            return False

        return True

    def delete(self):
        """ Delete the device from Webex Calling and from Control Hub completely

        Returns:
            bool: True on success. An exception will be thrown otherwise

        """
        webex_api_call("delete", f"v1/devices/{self.id}", params={'orgId': self.parent.org_id})
        return True

    @property
    def members(self):
        """ :class:`DeviceMembersList` of the configured lines (i.e. members) on the device """
        if self._device_members is None:
            self._device_members = DeviceMemberList(self)
        return self._device_members

    def get_workspace_location_uuid(self):
        """ Returns just the UUID portion of the `workspace_location_id` property.

        .. versionadded:: 4.2.2
            Added because the Base64 ID does not match the ID values for :class:`WorkspaceLocation`. The assumption is
            that this will be resolved in the future, but needs to be supported until then

        Returns:
            str: The UUID component of the :attr:`workspace_location_id`

        """
        return decode_spark_id(self.workspace_location_id).split("/")[-1]


class DeviceMemberList(UserList):
    def __init__(self, device: Device):
        log.info(f"Collecting Device Members for {device.display_name}")
        super().__init__()
        log.info("Initializing DeviceMemberList")
        self.device = device
        """ The :class:`Device` instance associated with this Member List"""
        self.max_line_count: Optional[int] = None
        """ The max number of lines in the device"""
        self.data = self._get_data()

    def _get_data(self):
        try:
            response = webex_api_call('get', f"v1/telephony/config/devices/{self.device.id}/members",
                                      params={'orgId': self.device.parent.org_id})
        except:
            return []
        log.debug(response)
        members = []
        for entry in response['members']:
            members.append(DeviceMember(self.device, entry))
        self.max_line_count = response['maxLineCount']
        return members

    def refresh(self):
        """ Refresh the list of configured lines from Webex """
        self.data = self._get_data()

    def available_members(self) -> list:
        """ Get a list of available members, which are Workspaces and People that can be assigned to this device.

        This returns a dict, which is what is returned by Webex. I am not sure what the purpose of this API call is,
        but I see it used in Control Hub, so I am including it in case it provides some value.

        Returns:
            dict: A list of available members to add to the device

        """
        response = webex_api_call('get', f"v1/telephony/config/devices/{self.device.id}/availableMembers",
                                  params={'orgId': self.device.parent.org_id})
        return response['members']

    def add(self, members: Union[list, Workspace, Person, VirtualLine],
            line_type: str = 'shared',
            line_label: Optional[str] = None,
            hotline_enabled: bool = False,
            hotline_destination: Optional[str] = None,
            allow_call_decline: bool = False) -> bool:
        """ Add a new configured line (member) to the Device

        .. note::

            When using the ``line_type``, ``hotline_enabled`` or ``allow_call_decline`` arguments, those will be
            applied to all members in the list, if provided. If you need different settings for each member, call the
            add() method multiple times with the relevant settings.

        Args:
            members (list, Workspace, Person, VirtualLine): The Workspace, Person, VirtualLine or a list of those to
                add as configured lines.

            line_type (str, optional): Allowed values are ``'primary'`` for the primary device for a Person or Workspace
                or ``'shared'`` for Shared Line Appearances on non-primary devices. Defaults to ``'shared'``

            line_label (str, optional): A text label for the line on the device. Note that this is only supported for
                Cisco MPP devices. Attempting to set a line label on a Customer or Partner Managed Device will fail.

            hotline_enabled (bool, optional): Whether Hotline should be enabled for the line. Default False.
            hotline_destination (str, optional): The Hotline destination number. Required when ``hotline_enabled``
                is True

            allow_call_decline (bool, optional): Whether declining a call will decline across all devices or just
                silence this device. Defaults to False, which silences this device only.

        Returns:
            bool: True on success, False otherwise.

        """
        log.info(f"Adding to Device Members to {self.device.display_name}")
        ports_available = self.ports_available()
        members_list_json: list = self._json_list()
        # If a Workspace or Person was provided, put it into a list anyway
        if isinstance(members, (wxcadm.person.Person, wxcadm.workspace.Workspace, wxcadm.virtual_line.VirtualLine)):
            members = [members]
        # The following section was removed because port assignment doesn't seem to do anything, at least with MPP
        # if port is not None:
        #     # Check to make sure the port is available, or the whole port range
        #     for i in range(port, port + len(members), 1):
        #         if i not in ports_available:
        #             log.warning(f"Requested port {port} is already in use.")
        #             raise ValueError(f"Port {port} is already in use")

        port = ports_available[0]
        log.debug(f"Using port {port} as the starting port number")

        # Set some defaults to the right values for the API call
        line_type = 'PRIMARY' if line_type.lower() == 'primary' else 'SHARED_CALL_APPEARANCE'

        for new_member in members:
            member_config = {
                'port': port,
                'id': new_member.id,
                'primaryOwner': False,
                'lineType': line_type,
                'lineWeight': 1,
                'hotlineEnabled': hotline_enabled,
                'hotlineDestination': hotline_destination,
                'allowCallDeclineEnabled': allow_call_decline,
            }
            # lineLabel cannot be passed to non-MPP devices, so don't add it unless we need to
            if line_label is not None:
                member_config['lineLabel'] = line_label
            members_list_json.append(member_config)

        wxcadm.webex_api_call('put',
                              f"v1/telephony/config/devices/{self.device.id}/members",
                              payload={'members': members_list_json},
                              params={'orgId': self.device.parent.org_id})
        return True

    def _json_list(self) -> list:
        json_list = []
        entry: DeviceMember
        for entry in self.data:
            new_entry = {
                'port': entry.port,
                'id': entry.id,
                'primaryOwner': entry.primary_owner,
                'lineType': entry.line_type,
                'lineWeight': entry.line_weight,
                'hotlineEnabled': entry.hotline_enabled,
                'hotlineDestination': entry.hotline_destination,
                'allowCallDeclineEnabled': entry.call_decline_all,
            }
            # lineLabel is weird, so we have to only add it back when it is not None
            if entry.line_label is not None:
                new_entry['lineLabel'] = entry.line_label
            json_list.append(new_entry)
        return json_list

    def ports_available(self) -> list:
        """ Returns a list of available port numbers. """
        ports_available = []
        for port, member in self.port_map().items():
            if member is None:
                ports_available.append(port)
        return ports_available

    def port_map(self) -> dict:
        """ Returns a dict mapping of all ports and their assigned :class:`DeviceMember` """
        port_map = {}
        for i in range(1, self.max_line_count + 1, 1):
            port_map[i] = None
        member: DeviceMember
        for member in self.data:
            log.debug("Starting loop")
            for p in range(member.port, member.port + member.line_weight, 1):
                log.debug(f"In Loop: {p}")
                port_map[p] = member
        return port_map

    def get(self, person: Optional[Person] = None, workspace: Optional[Workspace] = None):
        if person is not None and workspace is not None:
            raise ValueError('Only person or workspace is accepted, not both')
        if person is not None:
            member_instance = person
        if workspace is not None:
            member_instance = workspace
        for member in self.data:
            if member.id is not None and (member.id == member_instance.id):
                return member
        return None


class DeviceMember:
    def __init__(self, device: Device, member_info: dict):
        self.device: Device = device
        """ The :class:`Device` instance associated with this member """
        self.member_type: str = member_info['memberType']
        """ The type of member, either 'person' or 'workspace'"""
        self.id: str = member_info['id']
        """ The ID of the member"""
        self.port: int = member_info['port']
        """ The device port number of the member"""
        self.primary_owner: bool = member_info['primaryOwner']
        """ Whether this member is the primary owner of the device"""
        self.line_type: str = member_info['lineType']
        """ The type of line, either 'primary' or 'shared'"""
        self.line_weight: int = member_info['lineWeight']
        """ The weight of this line"""
        self.hotline_enabled: bool = member_info['hotlineEnabled']
        """ Whether hotline is enabled for this member"""
        self.hotline_destination: Optional[str] = member_info.get('hotlineDestination', None)
        """ The hotline destination number, if enabled"""
        self.call_decline_all: bool = member_info['allowCallDeclineEnabled']
        """ Whether call decline is enabled for this member"""
        self.line_label: Optional[str] = member_info.get('lineLabel', None)
        """ The line label, if set"""
        self.first_name: Optional[str] = member_info.get('firstName', None)
        """ The first name of the member"""
        self.last_name: Optional[str] = member_info.get('lastName', None)
        """ The last name of the member"""
        self.phone_number: Optional[str] = member_info.get('phoneNumber', None)
        """ The phone number of the member"""
        self.extension: Optional[str] = member_info.get('extension', None)
        """ The extension of the member"""
        self.host_ip: Optional[str] = member_info.get('hostIP', None)
        """ The host IP address of the member"""
        self.remote_ip: Optional[str] = member_info.get('remoteIP', None)
        """ The remote IP address of the member """
        self.line_port: Optional[str] = member_info.get('linePort', None)
        """ The line port of the member"""
        self.esn: Optional[str] = member_info.get('esn', None)
        """ The ESN of the member"""
        self.routing_prefix: Optional[str] = member_info.get('routingPrefix', None)
        """ The routing prefix of the member"""
        self.location_id = None
        """ The location ID of the member """
        if 'location' in member_info.keys():
            self.location_id = member_info['location']['id']

    def set_line_label(self, label: str) -> DeviceMember:
        """ Set/update the Line Label on the device

        Args:
            label (str): The new line label

        Returns:
            DeviceMember: The updated DeviceMember instance

        """
        # Rather than rebuild the member list from what we already have, it's quicker to just pull a fresh copy
        old_member_list = webex_api_call('get', f'v1/telephony/config/devices/{self.device.id}/members',
                                         params={'orgId': self.device.parent.org_id})
        new_member_list = []
        for member in old_member_list['members']:
            if member['id'] == self.id:
                member['lineLabel'] = label
            # The PUT doesn't take all the fields that the GET has so we have to clean up
            member.pop('remoteIP', None)
            member.pop('linePort', None)
            member.pop('firstName', None)
            member.pop('lastName', None)
            member.pop('phoneNumber', None)
            member.pop('extension', None)
            member.pop('hostIP', None)
            member.pop('location', None)

            new_member_list.append(member)

        # Once we have rebuilt the list, just PUT it back
        webex_api_call('put', f'v1/telephony/config/devices/{self.device.id}/members',
                       payload={'members': new_member_list}, params={'orgId': self.device.parent.org_id})
        self.line_label = label
        return self

    def set_hotline(self, enabled: bool, destination: Optional[str] = None) -> DeviceMember:
        """ Enable or disable Hotline for the Device Member

        Args:
            enabled (bool): True for Enabled, False for Disabled
            destination (str, optional): The Hotline destination

        Returns:
            DeviceMember: The updated DeviceMember instance

        """
        # Rather than rebuild the member list from what we already have, it's quicker to just pull a fresh copy
        old_member_list = webex_api_call('get', f'v1/telephony/config/devices/{self.device.id}/members',
                                         params={'orgId': self.device.parent.org_id})
        new_member_list = []
        for member in old_member_list['members']:
            if member['id'] == self.id:
                member['hotlineEnabled'] = enabled
                if destination is not None:
                    member['hotlineDestination'] = destination

            # The PUT doesn't take all the fields that the GET has so we have to clean up
            member.pop('remoteIP', None)
            member.pop('linePort', None)
            member.pop('firstName', None)
            member.pop('lastName', None)
            member.pop('phoneNumber', None)
            member.pop('extension', None)
            member.pop('hostIP', None)
            member.pop('location', None)

            new_member_list.append(member)

        # Once we have rebuilt the list, just PUT it back
        webex_api_call('put', f'v1/telephony/config/devices/{self.device.id}/members',
                       payload={'members': new_member_list}, params={'orgId': self.device.parent.org_id})
        self.hotline_enabled = enabled
        if destination is not None:
            self.hotline_destination = destination
        return self

    def set_call_decline_all(self, enabled: bool):
        """ Set or change the Call Decline behavior of the Device Member.

        When set to True, declining the call on the device will decline the call on all devices. When set to False,
        declining the call on the device will only silence the device and allow other devices to keep ringing.

        Args:
            enabled (bool): True to decline on all devices, False to decline on this device

        Returns:
            DeviceMember: The updated DeviceMember instance

        """
        # Rather than rebuild the member list from what we already have, it's quicker to just pull a fresh copy
        old_member_list = webex_api_call('get', f'v1/telephony/config/devices/{self.device.id}/members',
                                         params={'orgId': self.device.parent.org_id})
        new_member_list = []
        for member in old_member_list['members']:
            if member['id'] == self.id:
                member['allowCallDeclineEnabled'] = enabled

            # The PUT doesn't take all the fields that the GET has so we have to clean up
            member.pop('remoteIP', None)
            member.pop('linePort', None)
            member.pop('firstName', None)
            member.pop('lastName', None)
            member.pop('phoneNumber', None)
            member.pop('extension', None)
            member.pop('hostIP', None)
            member.pop('location', None)

            new_member_list.append(member)

        # Once we have rebuilt the list, just PUT it back
        webex_api_call('put', f'v1/telephony/config/devices/{self.device.id}/members',
                       payload={'members': new_member_list}, params={'orgId': self.device.parent.org_id})
        self.call_decline_all = enabled
        return self


class DeviceList(UserList):
    _endpoint = "v1/devices"
    _endpoint_items_key = None
    _item_endpoint = "v1/devices/{item_id}"
    _item_class = Device

    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location, wxcadm.Workspace, wxcadm.Person]):
        super().__init__()
        log.debug("Initializing DeviceList")
        self.parent: wxcadm.Org | wxcadm.person.Person | wxcadm.workspace.Workspace | wxcadm.Location = parent
        self.data: list = self._get_data()
        self._supported_devices: Optional[SupportedDeviceList] = None

    def _get_data(self) -> list:
        log.debug("_get_data() started")
        params = {}

        if isinstance(self.parent, wxcadm.Org):
            log.debug(f"Using Org ID {self.parent.id} as data filter")
            params['orgId'] = self.parent.id
        elif isinstance(self.parent, wxcadm.Location):
            log.debug(f"Using Location ID {self.parent.id} as data filter")
            params['locationId'] = self.parent.id
        elif isinstance(self.parent, wxcadm.person.Person):
            log.debug(f"Using API endpoint v1/telephony/config/people/{self.parent.id}/devices")
            self._endpoint = f"v1/telephony/config/people/{self.parent.id}/devices"
            self._endpoint_items_key = 'devices'
        elif isinstance(self.parent, wxcadm.workspace.Workspace):
            log.debug(f"Using Workspace ID {self.parent.id} as data filter")
            params['workspaceId'] = self.parent.id
        else:
            log.warn("Parent class is not Org or Location, so all items will be returned")
        response = webex_api_call('get', self._endpoint, params=params)
        items = []
        if self._endpoint_items_key is not None:
            log.info(f"Found {len(response[self._endpoint_items_key])} items")
            for entry in response[self._endpoint_items_key]:
                items.append(self._item_class(parent=self.parent, config=entry, id=entry['id']))
        else:
            log.info(f"Found {len(response)} items")
            for entry in response:
                items.append(self._item_class(parent=self.parent, config=entry, id=entry['id']))
        return items

    def refresh(self):
        """ Refresh the list of instances from Webex

        Returns:
            bool: True on success, False otherwise.

        """
        self.data = self._get_data()
        return True

    def get(self,
            id: Optional[str] = None,
            name: Optional[str] = None,
            mac_address: Optional[str] = None,
            spark_id: Optional[str] = None,
            connection_status: Optional[str] = None):
        """ Get the instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Locations will be
        searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method will raise an
        Exception.

        Args:
            id (str, optional): The Device ID to find
            name (str, optional): The Device Name to find. Case-insensitive.
            mac_address (str, optional): The Device MAC address
            spark_id (str, optional): The Spark ID to find
            connection_status(str, optional): The connection status of the device (e.g. "disconnected", "connected")

        Returns:
            Device: The Device instance, or list of instances correlating to the given search argument.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and mac_address is None and spark_id is None and connection_status is None:
            raise ValueError("A search argument must be provided")
        if id is not None:
            for item in self.data:
                if item.id == id:
                    return item
        if name is not None:
            for item in self.data:
                if item.display_name.lower() == name.lower():
                    return item
        if mac_address is not None:
            for item in self.data:
                if item.mac == mac_address.upper().replace(':', '').replace('-', ''):
                    return item
        if spark_id is not None:
            for item in self.data:
                if item.spark_id == spark_id:
                    return item
        if connection_status is not None:
            item_list: list = []
            for item in self.data:
                if item.connection_status.lower() == connection_status.lower():
                    item_list.append(item)
            return item_list
        return None

    def create(self, model: SupportedDevice,
               mac: Optional[str] = None,
               password: Optional[str] = None,
               person: Optional[wxcadm.person.Person] = None,
               workspace: Optional[wxcadm.workspace.Workspace] = None):
        """ Add a new device to the Workspace, Person or Org

        In order to use this method, you must know the model of the device that you are adding, which is a
        :class:`SupportedDevice` from the :attr:`Org.supported_devices` :class:`SupportedDeviceList`.

        If the MAC address is passed, a device will be created with the provided MAC address. If no MAC address is
        passed, an Activation Code will be generated and returned as part of the response. Your integration/token must
        have the ``identity:placeonetimepassword_create`` scope to create Activation Codes for devices. Some supported
        devices do not allow onboarding by Activation Code, which will raise a ValueError. You can check the
        :attr:`SupportedDevice.onboarding_method` attribute to determine what onboarding methods are allowed.

        Args:
            model (SupportedDevice): The :class:`SupportedDevice` model that is being added

            mac (str, optional): The MAC address of the device being added

            password (str, optional): Only valid when creating devices that are not managed by Cisco. If a
                password is not provided, the Webex API will generate a unique, compliant SIP password and return it
                in the response.

            person (Person, optional): If the :class:`DeviceList` was accessed via :attr:`Org.devices`, a Person or
                Workspace must be provided when creating a Device

            workspace (Workspace, optional): If the :class:`DeviceList` was accessed via :attr:`Org.devices`, a
                Workspace or Person must be provided when creating a Device

        Returns:
            dict: The dict values vary based on the type of device being activated. If the device fails for any reason,
                False will be returned. At the moment, Webex doesn't provide very useful failure reasons, but those may
                be added to the return value when they are available.

        Raises:
            ValueError: Raised when the DeviceList cannot determine which Person or Workspace to add the device to.
                This is normally when the DeviceList was created at the Org level with :attr:`Org.devices`. Ensure you
                are passing a ``workspace`` or ``person`` argument to the method. It may also be raised if the device
                type does not support the requested onboarding method.

        """
        log.info(f"Adding a device to {self.parent.name}")
        payload = {}
        if isinstance(model, SupportedDevice):
            log.debug(f"Checking SupportedDevice requirements for {model.model}")
            log.debug(f"Setting model name to {model.model}")
            payload['model'] = model.model
            if model.managed_by.upper() == 'CISCO':
                log.debug("Cisco-managed device. No password needed.")
                password_needed = False
                data_needed = False
            else:
                log.debug(f"{model.managed_by.title()}-managed device. Password needed.")
                password_needed = True
                data_needed = True
            if 'ACTIVATION_CODE' not in model.onboarding_method and mac is None:
                raise ValueError("Activation Code not supported")
            if isinstance(self.parent, wxcadm.Workspace) or workspace is not None:
                if 'PLACE' not in model.supported_for:
                    raise ValueError("Device does not support Workspaces")
            if isinstance(self.parent, wxcadm.Person) or person is not None:
                if 'PEOPLE' not in model.supported_for:
                    raise ValueError("Device does not support People")
        else:
            raise ValueError("model argument must be a SupportedDevice object")

        if isinstance(self.parent, wxcadm.workspace.Workspace):
            payload['workspaceId'] = self.parent.id
            params = {'orgId': self.parent.org_id}
            device_info_url = f"v1/telephony/config/workspaces/{self.parent.id}/devices"
        elif isinstance(self.parent, (wxcadm.person.Person, wxcadm.person.Me)):
            payload['personId'] = self.parent.id
            params = {'orgId': self.parent.org_id}
            device_info_url = f"v1/telephony/config/people/{self.parent.id}/devices"
        elif isinstance(self.parent, wxcadm.org.Org):
            if person is not None:
                payload['personId'] = person.id
                params = {'orgId': self.parent.id}
                device_info_url = f"v1/telephony/config/people/{person.id}/devices"
            elif workspace is not None:
                payload['workspaceId'] = workspace.id
                params = {'orgId': self.parent.id}
                device_info_url = f"v1/telephony/config/people/{workspace.id}/devices"
            else:
                raise ValueError("Person or Workspace must be provided")
        else:
            raise ValueError("Cannot determine Person or Workspace from given arguments")

        if mac is None and 'ACTIVATION_CODE' in model.onboarding_method:
            # If no MAC address is provided, just generate an activation code for the device
            try:
                response = webex_api_call('post',
                                          'v1/devices/activationCode',
                                          payload=payload, params=params)
                log.debug(f"\t{response}")
            except APIError:
                return False

            # Get the ID of the device we just inserted
            device_id = response.get('id', None)
            if device_id is not None:
                device_id = device_id.replace('=', '')

            results = {
                'device_id': device_id,
                'activation_code': response['code']
            }
        else:
            payload['mac'] = mac
            if password_needed is True:
                if password is None:  # Generate a unique password
                    if isinstance(self.parent, (wxcadm.person.Person, wxcadm.person.Me)):
                        password_location = self.parent.location
                    if isinstance(self.parent, wxcadm.workspace.Workspace):
                        password_location = self.parent._parent.locations.webex_calling(single=True).id
                    if isinstance(self.parent, wxcadm.org.Org):
                        password_location = self.parent.locations.webex_calling(single=True).id
                    response = webex_api_call('POST',
                                              f'v1/telephony/config/locations/{password_location}/actions/'
                                              f'generatePassword/invoke')
                    password = response['exampleSipPassword']
                payload['password'] = password

            response = webex_api_call('post', 'v1/devices', payload=payload, params=params)
            log.debug(f"\t{response}")

            # Get the ID of the device we just inserted
            # Adding 9800s does not return any JSON, just a bool, so when that happens, we just need to go find the
            # newly added device. Unfortunately, it means an entirely different API call (4.4.1)
            if isinstance(response, bool):
                device_info = webex_api_call('get', device_info_url, params={'orgId': self.parent.org_id})
                for device in device_info['devices']:
                    if device['mac'] == mac.upper().replace(':', '').replace('-', ''):
                        new_device = Device(parent=self.parent, config=device, id=device['id'])
                        results = {
                            'device_id': new_device.id,
                            'mac': new_device.mac,
                            'device_object': new_device
                        }
            else:
                device_id = response.get('id', None).replace('=', '')

                results = {
                    'device_id': device_id,
                    'mac': response['mac'],
                    'device_object': Device(self.parent, config=response)
                }

            if data_needed is True:
                response = webex_api_call('get', f'/v1/telephony/config/devices/{device_id}',
                                          params={'orgId': self.parent.org_id})
                results['sip_auth_user'] = response['owner']['sipUserName']
                results['line_port'] = response['owner']['linePort']
                results['password'] = password
                results['sip_userpart'] = response['owner']['linePort'].split('@')[0]
                results['sip_hostpart'] = response['owner']['linePort'].split('@')[1]
                results['sip_outbound_proxy'] = response['proxy']['outboundProxy']
                results['sip_outbound_proxy_srv'] = f"_sips._tcp.{response['proxy']['outboundProxy']}"

        # Provide the Device instance in the response as well
        return results

    @property
    def supported_devices(self):
        """ The list of supported devices for the Org along with the capabilities of each """
        if self._supported_devices is None:
            self._supported_devices = SupportedDeviceList()
        return self._supported_devices

    def webex_calling(self, enabled = True) -> list:
        """ Returns a list of Device instances where Webex Calling is enabled or disabled.

        Args:
            enabled(bool, optional): Whether Webex Calling is enabled on the Device. Defaults to True.

        Returns:
            list: List of :class:`Device` instances matching the requested argument.

        """
        device_list = []
        device: Device
        for device in self.data:
            if device.workspace_location_id is not None:
                wxc_device = True
            else:
                wxc_device = False
            if wxc_device is enabled:
                device_list.append(device)
        return device_list

    def get_by_status(self, status: str) -> list:
        """ Get a list of devices by the connection status from :attr:`Device.connection_status`

        The `status` argument accepts the "raw" :attr:`Device.connection_status`:
            - "connected"
            - "disconnected"
            - "connected_with_issues"
            - "offline_expired"
            - "activating"
            - "unknown"
        It also accepts the following grouping values which are unique to **wxcadm**:
            - "online" returns devices which are known to be online
            - "offline" returns devices which are known to be offline

        Since `"activating"` and `"unknown"` devices are not known to be in a state, they can only be returned by
            passing the raw value as the status

        Args:
            status (str): See the documentation above for a list of valid values.

        Returns:
            list(Device): List of :class:`Device` instances matching the requested argument.

        """
        return_list = []
        if status.lower() == 'online':
            match_status_list = ['connected', 'connected_with_issues']
        elif status.lower() == 'offline':
            match_status_list = ['disconnected', 'offline_expired', 'offline_deep_sleep']
        else:
            match_status_list = [status]
        for device in self.data:
            if device.connection_status.lower() in match_status_list:
                return_list.append(device)
        return return_list


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SupportedDevice:
    model: str
    """ The model of the device """
    display_name: str
    """ The display name of the device type """
    type: str
    """ The type of the device"""
    manufacturer: str
    """ The manufacturer of the device"""
    managed_by: str
    """ Whether the device is managed by Cisco or a third party """
    supported_for: list
    """ What the device type is supported for """
    onboarding_method: list
    """ What methods are available to onboard the device """
    allow_configure_layout_enabled: bool
    """ Whether the device type supports configuring the layout """
    number_of_line_ports: int
    """ The number of line ports on the device """
    kem_support_enabled: bool
    """ Whether the device supports a key expansion module """
    upgrade_channel_enabled: bool
    """ Whether the device supports multiple upgrade channels """
    customized_behaviors_enabled: bool
    """ Whether the device supports customized behaviors """
    allow_configure_ports_enabled: bool
    """ Whether the device supports configuring line ports """
    customizable_line_label_enabled: bool
    """ Whether the device supports customizable line labels """
    kem_module_count: Optional[int] = None
    """ The number of KEM modules supported by the device """
    kem_module_type: Optional[list] = None
    """ The type of KEM modules supported by the device """
    default_upgrade_channel: Optional[str] = None
    """ The default upgrade channel for the device """
    additional_primary_line_appearances_enabled: Optional[bool] = None
    """ Whether the device supports configuring additional primary line appearances """
    basic_emergency_nomadic_enabled: Optional[bool] = None
    """ Whether the device supports basic emergency nomadic (HELD) """


class SupportedDeviceList(UserList):
    _endpoint = "v1/telephony/config/supportedDevices"
    _endpoint_items_key = 'devices'
    _item_endpoint = None
    _item_class = SupportedDevice

    def __init__(self):
        super().__init__()
        log.info('Collecting SupportedDeviceList')
        self.data: list = self._get_data()

    def _get_data(self) -> list:
        log.debug('_get_data() started')
        response = webex_api_call('get', self._endpoint)
        items = []
        if self._endpoint_items_key is not None:
            log.info(f"Found {len(response[self._endpoint_items_key])} items")
            for entry in response[self._endpoint_items_key]:
                items.append(self._item_class.from_dict(entry))
        else:
            log.info(f"Found {len(response)} items")
            for entry in response:
                items.append(self._item_class(**entry))
        return items

    def get(self, model_name: str):
        """ Get a :class:`SupportedDevice` of list of :class:`SupportedDevices`s matching given model name
        
        Matches will match on a partial model name. For example ``model='Cisco 8841'`` will match a
        :class:`SupportedDevice` with model 'DMS Cisco 8841'.

        Args:
            model_name (str): The name or partial model name. Not case-sensitive.

        Returns:
            SupportedDevice: If only a single entry matches, that Device will be returned. If multiple Devices match,
            a list of devices will be returned.

        """
        supported_devices = []
        for dev in self.data:
            if model_name.upper() in dev.model.upper():
                supported_devices.append(dev)
        if len(supported_devices) == 1:
            return supported_devices[0]
        else:
            return supported_devices

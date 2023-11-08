from __future__ import annotations
from collections import UserList
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .person import Person
    from .workspace import Workspace
import logging
import json
import wxcadm
from .common import *
from typing import Optional, Union
from .exceptions import *
from wxcadm import log


class Device:
    def __init__(self, parent: Person | Workspace, config: dict):
        self.parent = parent
        """ The :py:class:`Org`, :py:class:`Person` or :py:class:`Workspace` that created this instance """
        self.id: str = config['id']
        """ The Device ID """
        self.tags: list = config.get('tags', config.get('description', ''))
        """ The device tags """
        self.model: str = config.get('model', config.get('product', ''))
        """ The model name of the device """
        self.mac: str = config.get('mac')
        """ The device MAC address """
        self.is_owner: bool = config.get('primaryOwner', None)
        """ Whether the Person or Workspace is the primary owner of the device """
        self.activation_state: str = config.get('activationState', None)
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
        self._device_members = None

        if 'personId' in config.keys() and isinstance(self.parent, wxcadm.Org):
            self.owner = self.parent.get_person_by_id(config['personId'])
        elif 'workspaceId' in config.keys() and isinstance(self.parent, wxcadm.Org):
            self.owner = self.parent.workspaces.get_by_id(config['workspaceId'])

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
        response = webex_api_call("patch", f"/v1/devices/{self.id}", payload=payload)

        return True

    @property
    def settings(self):
        """ The device settings.

        The available settings vary by device type, so the raw dictionary from Webex is returned.

        """
        if self._settings is None:
            response = webex_api_call('get', f'/v1/telephony/config/devices/{self.id}/settings',
                                      params={'model': self.model})
            self._settings = response
        return self._settings

    @settings.setter
    def settings(self, config: dict):
        try:
            webex_api_call('put', f'v1/telephony/config/devices/{self.id}/settings',
                                  payload=config)
        except APIError:
            logging.warning("The API call to set the device settings failed")

        self._settings = config

    def apply_changes(self) -> bool:
        """ Issues request to the device to download and apply changes to the configuration.

        Returns:
            bool: True on success, False otherwise

        """
        try:
            webex_api_call('post', f'v1/telephony/config/devices/{self.id}/actions/applyChanges/invoke')
        except APIError:
            return False

        return True

    def delete(self):
        """ Delete the device from Webex Calling and from Control Hub completely

        Returns:
            bool: True on success. An exception will be thrown otherwise

        """
        response = webex_api_call("delete", f"v1/devices/{self.id}")

        return True

    @property
    def members(self):
        """ :class:`DeviceMembersList` of the configured lines (i.e. memmbers) on the device """
        if self._device_members is None:
            self._device_members = DeviceMemberList(self)
        return self._device_members


class DeviceMemberList(UserList):
    def __init__(self, device: Device):
        log.info(f"Collecting Device Members for {device.display_name}")
        super().__init__()
        log.info("Initializing DeviceMemberList")
        self.device = device
        self.max_line_count: Optional[int] = None
        self.data = self._get_data()

    def _get_data(self):
        response = webex_api_call('get', f"v1/telephony/config/devices/{self.device.id}/members")
        log.debug(response)
        members = []
        for entry in response['members']:
            members.append(DeviceMember(self.device, entry))
        self.max_line_count = response['maxLineCount']
        return members

    def refresh(self):
        """ Refresh the list of configured lines from Webex """
        self.data = self._get_data()

    def available(self) -> list:
        response = webex_api_call('get', f"v1/telephony/config/devices/{self.device.id}/availableMembers")
        return response['members']

    def add(self, members: Union[list, Workspace, Person],
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
            members (list, Workspace, Person): The Workspace, Person, or a list of both to add as configured lines.

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
        if isinstance(members, (wxcadm.person.Person, wxcadm.workspace.Workspace)):
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
            members_list_json.append({
                'port': port,
                'id': new_member.id,
                'primaryOwner': False,
                'lineType': line_type,
                'lineWeight': 1,
                'hotlineEnabled': hotline_enabled,
                'hotlineDestination': hotline_destination,
                'allowCallDeclineEnabled': allow_call_decline,
                'lineLabel': line_label
            })

        response = wxcadm.webex_api_call('put',
                                         f"v1/telephony/config/devices/{self.device.id}/members",
                                         payload={'members': members_list_json})
        return True

    def _json_list(self) -> list:
        json_list = []
        entry: DeviceMember
        for entry in self.data:
            json_list.append({
                'port': entry.port,
                'id': entry.id,
                'primaryOwner': entry.primary_owner,
                'lineType': entry.line_type,
                'lineWeight': entry.line_weight,
                'hotlineEnabled': entry.hotline_enabled,
                'hotlineDestination': entry.hotline_destination,
                'allowCallDeclineEnabled': entry.allow_call_decline,
                'lineLabel': entry.line_label
            })
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


class DeviceMember:
    def __init__(self, device: Device, member_info: dict):
        self.device: Device = device
        self.member_type: str = member_info['memberType']
        self.id: str = member_info['id']
        self.port: int = member_info['port']
        self.primary_owner: bool = member_info['primaryOwner']
        self.line_type: str = member_info['lineType']
        self.line_weight: int = member_info['lineWeight']
        self.hotline_enabled: bool = member_info['hotlineEnabled']
        self.hotline_destination: str = member_info.get('hotlineDestination', None)
        self.allow_call_decline: bool = member_info['allowCallDeclineEnabled']
        self.line_label: Optional[str] = member_info.get('lineLabel', None)

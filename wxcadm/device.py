from __future__ import annotations
from collections import UserList
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .person import Person
    from .workspace import Workspace
import logging

import wxcadm
from .common import *
from typing import Optional, Union
from .exceptions import *


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

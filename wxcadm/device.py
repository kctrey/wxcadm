from __future__ import annotations

import logging

from .common import *
from typing import Optional, Union
from .exceptions import *


class Device:
    def __init__(self, parent: Union[Person, Workspace], config: dict):
        self.parent = parent
        """ The :py:class:`Person` or :py:class:`Workspace` that owns the Device """
        self.id: str = config['id']
        """ The Device ID """
        self.tags: list = config['description']
        """ The device tags """
        self.model: str = config['model']
        """ The model name of the device """
        self.mac: str = config['mac']
        """ The device MAC address """
        self.is_owner: bool = config['primaryOwner']
        """ Whether the Person or Workspace is the primary owner of the device """
        self.activation_state: str = config['activationState']
        """ The device activation state """
        self.type: str = config['type']
        """ The type of device association """
        self.ip_address: Optional[str] = config.get('ipAddress', None)
        """ The IP Address of the device """
        self._settings: Optional[dict] = None

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
            webex_api_call('put', f'/v1/telephony/config/devices/{self.id}/settings',
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
            webex_api_call('post', f'/v1/telephony/config/devices/{self.id}/actions/applyChanges/invoke')
        except APIError:
            return False

        return True


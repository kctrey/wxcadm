from __future__ import annotations

import requests
from typing import Optional
from .exceptions import *


class Device:
    """The Device class holds device information, currently only available with CSDM."""
    def __init__(self, parent: CSDM, config: dict):
        self._parent = parent
        self.display_name: str = config.get("displayName", "")
        """The display name associated with the device"""
        self.uuid: str = config.get("cisUuid", "")
        """The Cisco UUID associated with the device"""
        self.account_type: str = config.get("accountType", "UNKNOWN")
        """The type of account the device is associated with"""
        self.url: str = config.get("url", "")
        """The URL to access the CSDM API for the device"""
        self.created: str = config.get("createTime", "")
        """The timestamp when the device was added"""
        self.serial: str = config.get("serial", "")
        """The serial number of the device"""
        self.product: str = config.get("product", "")
        """The product name"""
        self.type: str = config.get("type", "")
        """The type of device"""
        self.last_seen: str = config.get("lastKnownOnline", "UNKNOWN")
        """The last time the device was seen online"""
        self.owner_id: str = config.get("ownerId", "UNKNOWN")
        """The Spark ID of the device owner"""
        self.owner_name: str = config.get("ownerDisplayName", "UNKNOWN")
        """The display name of the device owner"""
        self.calling_type: str = config.get("callingType", "UNKNOWN")
        """The type of Calling the device is licensed for"""
        self.usage_mode: str = config.get("usageMode", "UNKNOWN")
        """The usage mode the device is operating in"""
        self.status: str = config.get("connectionStatus", "UNKNONW")
        """Real-time status information"""
        self.category: str = config.get("category", "UNKNOWN")
        """The device category"""
        self.product_family: str = config.get("productFamily", "UNKNOWN")
        """The product family to which the device belongs"""
        self.mac: str = config.get("mac", "UNKNOWN")
        """The MAC address of the device"""
        self._calling_location: Optional[Location] = None
        """The Webex Calling :class:`Location`"""
        self._image: Optional[str] = config.get("imageFilename", None)

    def __str__(self):
        return f"{self.product},{self.display_name}"

    @property
    def calling_location(self):
        """ The :class:`Location` instance that the device is assigned to

        .. warning::

            This attribute requires the CP-API access scope.
        """
        if not self._calling_location:
            location = self._parent._parent._cpapi.get_workspace_calling_location(self.owner_id)
            self._calling_location = location
        return self._calling_location

    @calling_location.setter
    def calling_location(self, location: Location):
        if isinstance(location, Location):
            self._calling_location = location

    def refresh(self):
        """Refresh the information about this device (including status) from CSDM"""
        r = requests.get(self.url, headers=self._parent._headers)
        if r.ok:
            response = r.json()
            return response
        else:
            raise CSDMError("Unable to refresh device status")

    def change_workspace_caller_id(self, name: str, number: str):
        """ Change the Caller ID for a Workspace

        For most cases, the ``name`` and ``number`` arguments will be special keywords to specify either the DID
        (Direct Line) or the Location Number as the Caller ID.

        Args:
            name (str): Acceptable values are 'DIRECT_LINE' and 'LOCATION'
            number (str): Acceptable values are 'DIRECT_LINE' and 'LOCATION_NUMBER'

        Returns:
            bool: True if successful. False otherwise

        .. warning::

            This method requires the CP-API access scope.

        """
        cpapi = self._parent._parent._cpapi
        if cpapi.change_workspace_caller_id(self.owner_id, name=name, number=number):
            return True
        else:
            return CSDMError("Not able to set Caller ID for Workspace")

from __future__ import annotations

from collections import UserList

import wxcadm.location
from wxcadm import log
from .common import *


class PickupGroupList(UserList):
    def __init__(self, parent: wxcadm.Location):
        super().__init__()
        self.parent: wxcadm.Location = parent
        self.data: list = self._get_items()

    def _get_items(self):
        if isinstance(self.parent, wxcadm.Location):
            log.debug("Using Location as data filter")
        else:
            raise ValueError("Unsupported parent class")

        log.debug("Getting Call Pickup list")
        response = webex_api_call('get', f'v1/telephony/config/locations/{self.parent.id}/callPickups')
        log.debug(f"Received {len(response['callPickups'])} entries")
        items = []
        for entry in response['callPickups']:
            items.append(PickupGroup(self.parent, id=entry['id'], config=entry))
        return items

    def get(self, id: str = None, name: str = None, spark_id: str = None):
        """ Get the PickupGroup instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Auto
        Attendants will be searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method
        will raise an Exception.

        Args:
            id (str, optional): The AutoAttendant ID to find
            name (str, optional): The AutoAttendant Name to find
            spark_id (str, optional): The Spark ID to find

        Returns:
            AutoAttendant: The AutoAttendant instance correlating to the given search argument.
                None is returned if no AutoAttendant is found.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        for aa in self.data:
            if aa.id == id:
                return aa
        for aa in self.data:
            if aa.name == name:
                return aa
        for aa in self.data:
            if aa.spark_id == spark_id:
                return aa
        return None


class PickupGroup:
    def __init__(self, parent: wxcadm.Location, id: str, config: dict):
        self.parent: wxcadm.Location = parent
        self.id: str = id
        """The Webex ID of the Pickup Group"""
        self.name: str = config['name']
        """The name of the Pickup Group"""
        self.config = config
        """The raw JSON configuration for the Pickup Group"""

    @property
    def users(self):
        """ All Users assigned to this Pickup Group"""
        log.info(f"Getting users for PickupGroups {self.name}")
        users = []
        response = webex_api_call('get', f'v1/telephony/config/locations/{self.parent.id}/callPickups/{self.id}')
        for item in response['agents']:
            #TODO - Once the Workspaces API supports Calling WOrkspaces, this should probably tie each Person/Workspace
            # to its corresponding instance
            users.append(item)
        return users

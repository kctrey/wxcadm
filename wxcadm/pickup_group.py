from __future__ import annotations

from collections import UserList

import wxcadm.location
from wxcadm import log
from .common import *


class PickupGroupList(UserList):
    def __init__(self, location: wxcadm.Location):
        super().__init__()
        self.location: wxcadm.Location = location
        self.data: list = self._get_items()

    def _get_items(self):
        if isinstance(self.location, wxcadm.Location):
            log.debug("Using Location as data filter")
        else:
            raise ValueError("Unsupported parent class")

        log.debug("Getting Call Pickup list")
        response = self.location.org.api.get(
            f'v1/telephony/config/locations/{self.location.id}/callPickups',
            items_key='callPickups'
        )
        items = []
        for entry in response:
            items.append(PickupGroup(self.location, id=entry['id'], config=entry))
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
    def __init__(self, location: wxcadm.Location, id: str, config: dict):
        self.location: wxcadm.Location = location
        """ The Location of the Pickup Group """
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
        response = self.location.org.api.get(f'v1/telephony/config/locations/{self.location.id}/callPickups/{self.id}')
        for item in response['agents']:
            if item['type'] == 'VIRTUAL_LINE':
                agent = self.location.org.virtual_lines.get(id=item['id'])
            elif item['type'] == 'PEOPLE':
                agent = self.location.org.people.get(id=item['id'])
            elif item['type'] == 'PLACE':
                agent = self.location.org.workspaces.get(id=item['id'])
            else:
                agent = item
            users.append(agent)
        return users

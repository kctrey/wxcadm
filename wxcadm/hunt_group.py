from __future__ import annotations

from typing import Optional, Union
from collections import UserList

import wxcadm.exceptions
from .common import *
from wxcadm import log


class HuntGroup:
    def __init__(self, parent: wxcadm.Org | wxcadm.Location, id: str, config: Optional[dict] = None):
        """Initialize a HuntGroup instance

        .. note::
            The HuntGroup class is normally not instantiated manually. It is created by the :class:`HuntGroupList`.

        Args:
            parent (Location|Org): The Location or Org instance to which the Hunt Group belongs
            id (str): The Webex ID for the Hunt Group
            config (dict, optional): The full config dict from Webex

        Returns:
            HuntGroup: The HuntGroup instance

        """
        log.debug(f"Initializing HuntGroup instance")

        # Instance attrs
        self.parent: wxcadm.Org | wxcadm.Location = parent
        self.id: str = id
        """The Webex ID of the Hunt Group"""
        self.name: str = config.get('name', '')
        """The name of the Hunt Group"""
        self.location_id: str = config['locationId']
        """The Location ID associated with the Hunt Group"""
        self.enabled: bool = config.get('enabled', True)
        """Whether the Hunt Group is enabled or not"""
        self.phone_number: str = config.get('phoneNumber', '')
        """The DID for the Hunt Group"""
        self.extension: str = config.get('extension', '')
        """The extension of the Hunt Group"""

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def config(self) -> dict:
        """ The config of the Hunt Group """
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.location_id}/huntGroups/{self.id}")
        return response

    @property
    def agents(self) -> list:
        return self.config['agents']


class HuntGroupList(UserList):
    _endpoint = "v1/telephony/config/huntGroups"
    _endpoint_items_key = "huntGroups"
    _item_endpoint = "v1/telephony/config/locations/{location_id}/huntGroups/{item_id}"
    _item_class = HuntGroup

    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location]):
        super().__init__()
        log.debug("Initializing HuntGroupList")
        self.parent: wxcadm.Org | wxcadm.Location = parent
        self.data: list = self._get_data()

    def _get_data(self) -> list:
        log.debug("_get_data() started")
        params = {}

        if isinstance(self.parent, wxcadm.Org):
            log.debug(f"Using Org ID {self.parent.id} as Data filter")
            params['orgId'] = self.parent.id
        elif isinstance(self.parent, wxcadm.Location):
            log.debug(f"Using Location ID {self.parent.id} as Data filter")
            params['locationId'] = self.parent.id
        else:
            log.warn("Parent class is not Org or Location, so all items will be returned")
        response = webex_api_call('get', self._endpoint, params=params)
        log.info(f"Found {len(response[self._endpoint_items_key])} items")

        items = []
        for entry in response[self._endpoint_items_key]:
            items.append(self._item_class(parent=self.parent, id=entry['id'], config=entry))
        return items

    def refresh(self):
        """ Refresh the list of instances from Webex

        Returns:
            bool: True on success, False otherwise.

        """
        self.data = self._get_data()
        return True

    def get(self, id: Optional[str] = None, name: Optional[str] = None, spark_id: Optional[str] = None):
        """ Get the instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Locations will be
        searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method will raise an
        Exception.

        Args:
            id (str, optional): The Call Queue ID to find
            name (str, optional): The Call Queue Name to find. Case-insensitive.
            spark_id (str, optional): The Spark ID to find

        Returns:
            CallQueue: The CallQueue instance correlating to the given search argument.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        if id is not None:
            for item in self.data:
                if item.id == id:
                    return item
        if name is not None:
            for item in self.data:
                if item.name.lower() == name.lower():
                    return item
        if spark_id is not None:
            for item in self.data:
                if item.spark_id == spark_id:
                    return item
        return None

    def create(self,
               name: str,
               first_name: str,
               last_name: str,
               phone_number: Optional[str],
               extension: Optional[str],
               call_policies: dict,
               enabled: bool = True,
               language: Optional[str] = None,
               time_zone: Optional[str] = None,
               location: Optional[wxcadm.Location] = None
               ):
        """ Create a Hunt Group

        Args:
            name (str): The name of the Hunt Group
            first_name (str): The first name to be used for Caller ID
            last_name (str): The last name to be used for Caller ID
            phone_number (str, optional): The phone number (e.g. DID) for the Hunt Group
            extension (str, optional): The extension for the Hunt Group
            call_policies (dict): The Hunt Group Call Policy. The dict has the following format::

            {
                'policy': 'REGULAR',
                'waitingEnabled': True,
                'noAnswer': {
                    'nextAgentEnabled': False,
                    'nextAgentRings': 2,
                    'forwardEnabled': True,
                    'destination': '5050',
                    'numberOfRings': 3,
                    'systemMaxNumberOfRings': 20,
                    'destinationVoicemailEnabled': False
                },
                'businessContinuity': {
                    'enabled': False,
                    'destination': '6312128008',
                    'destinationVoicemailEnabled': False
                }
            }

            enabled (bool, optional): Whether the Hunt Group is enabled. Defaults to True
            language (str, optional): The language for audio prompts. Defaults to ``Location.announcement_language``
            time_zone (str, optional): The time zone of the Hunt Group. Defaults to ``Location.time_zone``
            location (Location, optional): The Location at which to create the Hunt Group. Only required when the
                :class:`HuntGroupList` is at the Org level. If at the Location level, the selected :class:`Location`
                will be used.

        Returns:
            HuntGroup: The :class:`HuntGroup` instance of the created Hunt Group

        """
        if location is None and isinstance(self.parent, wxcadm.Org):
            raise ValueError("location is required for Org-level HuntGroupList")
        elif location is None and isinstance(self.parent, wxcadm.Location):
            location = self.parent
        log.info(f"Creating Hunt Group at Location {location.name} with name: {name}")
        if location.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        # Get some values if they weren't passed
        if phone_number is None and extension is None:
            raise ValueError("phone_number and/or extension are required")
        if time_zone is None:
            log.debug(f"Using Location time_zone {location.time_zone}")
            time_zone = location.time_zone
        if language is None:
            log.debug(f"Using Location announcement_language {location.announcement_language}")
            language = location.announcement_language

        payload = {
            "name": name,
            "firstName": first_name,
            "lastName": last_name,
            "extension": extension,
            "phoneNumber": phone_number,
            "timeZone": time_zone,
            "languageCode": language,
            "callPolicies": call_policies
        }
        response = webex_api_call("post", f"v1/telephony/config/locations/{location.id}/huntGroups",
                                  payload=payload)
        new_hg_id = response['id']
        self.refresh()
        return self.get(id=new_hg_id)
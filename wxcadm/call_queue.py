from __future__ import annotations

import requests
from typing import Optional, Type, Union
from collections import UserList

import wxcadm.exceptions
from .common import *
from wxcadm import log


class CallQueue:
    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location], id: str, config: Optional[dict] = None):
        """
        .. note::
            CallQueue instances are normally not instantiated manually and are done automatically with the
            :class:`CallQueueList` class initialization.

        """
        self.parent: Union[wxcadm.Org, wxcadm.Location] = parent
        """The parent org of this Call Queue"""
        self.id: str = id
        """The Webex ID of the Call Queue"""
        self.name: str = config.get('name', '')
        """The name of the Call Queue"""
        self.location_id: str = config.get('locationId', '')
        """The Webex ID of the Location associated with this Call Queue"""
        self.phone_number: str = config.get('phoneNumber', '')
        """The DID of the Call Queue"""
        self.extension: str = config.get('extension', '')
        """The extension of the Call Queue"""
        self.enabled: bool = config.get('enabled', False)
        """True if the Call Queue is enabled. False if disabled"""

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def spark_id(self) -> str:
        """ The Spark ID for the Call Queue """
        return decode_spark_id(self.id)

    @property
    def config(self) -> dict:
        """ The configuration of this Call Queue instance """
        log.info(f"Getting Queue config for {self.name}")
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.location_id}/queues/{self.id}")
        config = response
        return config

    @property
    def call_forwarding(self):
        """ The Call Forwarding settings for this Call Queue instance """
        # TODO: The rules within Call Forwarding are weird. The rules come back in this call, but they are
        #       different than the /selectiveRules response. It makes sense to aggregate them, but that probably
        #       requires the object->JSON mapping that we need to do for all classes
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.location_id}/queues/{self.id}"
                                         f"/callForwarding")
        forwarding = response
        return forwarding

    @property
    def agents(self) -> list:
        """ The agents assigned to the Call Queue """
        return self.config['agents']

    def add_agent(self, agent: Union[Person, Workspace],
                  weight: Optional[str] = None,
                  skill: Optional[str] = None,
                  joined: bool = True) -> bool:
        """ Add a Person or Workspace as an Agent to the Call Queue

        Args:
            agent (Person|Workspace): The Person or Workspace to add as the agent
            weight (str, optional): The weight of the agent route when using a weighted Queue
            skill (str, optional): The kill level (1-20) of the agent when using a Skill-Based Queue
            joined (bool, optional): Whether the agent will be joined into the Queue as soon as they are added

        Returns:
            bool: True on success, False otherwise

        """
        pass


    def push(self):
        """Push the contents of the CallQueue.config back to Webex

        Returns:
            CallQueue.config: The updated config attribute pulled from Webex after pushing the change

        """
        log.info(f"Pushing Call Queue config to Webex for {self.name}")
        response = webex_api_call('put', f'v1/telephony/config/locations/{self.location_id}/queues/{self.id}',
                                  payload=self.config)

        return response

    # Method aliases
    get_queue_config = config
    get_queue_forwarding = call_forwarding


class CallQueueList(UserList):
    _endpoint = "v1/telephony/config/queues"
    _endpoint_items_key = "queues"
    _item_endpoint = "v1/telephony/config/locations/{location_id}/queues/{item_id}"
    _item_class = CallQueue

    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location]):
        super().__init__()
        log.debug("Initializing CallQueueList")
        self.parent: Union[wxcadm.Org, wxcadm.Location] = parent
        self.data: list = self._get_data()

    def _get_data(self):
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

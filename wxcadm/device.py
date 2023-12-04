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
        webex_api_call("patch", f"/v1/devices/{self.id}", payload=payload)

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
        webex_api_call("delete", f"v1/devices/{self.id}")
        return True

    @property
    def members(self):
        """ :class:`DeviceMembersList` of the configured lines (i.e. members) on the device """
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
        try:
            response = webex_api_call('get', f"v1/telephony/config/devices/{self.device.id}/members")
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
                              payload={'members': members_list_json})
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
                'allowCallDeclineEnabled': entry.allow_call_decline,
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
        self.first_name: Optional[str] = member_info.get('firstName', None)
        self.last_name: Optional[str] = member_info.get('lastName', None)
        self.phone_number: Optional[str] = member_info.get('phoneNumber', None)
        self.extension: Optional[str] = member_info.get('extension', None)
        self.host_ip: Optional[str] = member_info.get('hostIP', None)
        self.remote_ip: Optional[str] = member_info.get('remoteIP', None)
        self.line_port: Optional[str] = member_info.get('linePort', None)


class DeviceList(UserList):
    _endpoint = "v1/devices"
    _endpoint_items_key = None
    _item_endpoint = "v1/devices/{item_id}"
    _item_class = Device

    def __init__(self, parent: Union[wxcadm.Org, wxcadm.Location]):
        super().__init__()
        log.debug("Initializing DeviceList")
        self.parent: wxcadm.Org | wxcadm.person.Person | wxcadm.workspace.Workspace | wxcadm.Location = parent
        self.data: list = self._get_data()

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
                items.append(self._item_class(parent=self.parent, config=entry))
        else:
            log.info(f"Found {len(response)} items")
            for entry in response:
                items.append(self._item_class(parent=self.parent, config=entry))
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
                if item.display_name.lower() == name.lower():
                    return item
        if spark_id is not None:
            for item in self.data:
                if item.spark_id == spark_id:
                    return item
        return None

    def create(self, model: str,
               mac: Optional[str] = None,
               password: Optional[str] = None,
               person: Optional[wxcadm.person.Person] = None,
               workspace: Optional[wxcadm.workspace.Workspace] = None):
        """ Add a new device to the Workspace, Person or Org

        In order to use this method, you must know the model of the device that you are adding, as expected by the
        Webex API. If you are adding a "Generic IPPhone Customer Managed" device, you can use that value or simply
        send ``model='GENERIC'`` as an alias. You can find the full list of models with the
        :py:meth:`Org.get_supported_devices()` method.

        If the MAC address is passed, a device will be created with the provided MAC address. If no MAC address is
        passed, an Activation Code will be generated and returned as part of the response. Your integration/token must
        have the ``identity:placeonetimepassword_create`` scope to create Activation Codes for devices.

        Args:
            model (str): The model name of the device being added

            mac (str, optional): The MAC address of the device being added

            password (str, optional): Only valid when creating a Generic IPPhone Customer Managed device. If a
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
                are passing a ``workspace`` or ``person`` argument to the method.

        """
        log.info(f"Adding a device to {self.parent.name}")
        if isinstance(self.parent, wxcadm.workspace.Workspace):
            payload = {
                "workspaceId": self.parent.id,
                "model": model
            }
        elif isinstance(self.parent, (wxcadm.person.Person, wxcadm.person.Me)):
            payload = {
                "personId": self.parent.id,
                "model": model
            }
        elif isinstance(self.parent, wxcadm.org.Org):
            if person is not None:
                payload = {
                    "personId": person.id,
                    "model": model
                }
            elif workspace is not None:
                payload = {
                    "workspaceId": workspace.id,
                    "model": model
                }
            else:
                raise ValueError("Device or Workspace must be provided")

        data_needed = False  # Flag that we need to get platform data once we have a Device ID
        if mac is None and model != 'Imagicle Customer Managed':
            # If no MAC address is provided, just generate an activation code for the device
            try:
                response = webex_api_call('post',
                                          'v1/devices/activationCode',
                                          payload=payload)
                log.debug(f"\t{response}")
            except APIError:
                return False

            # Get the ID of the device we just inserted
            device_id = response.get('id', None).replace('=', '')

            results = {
                'device_id': device_id,
                'activation_code': response['code']
            }
        else:
            payload['mac'] = mac
            if model.upper() == "GENERIC" or model == "Generic IPPhone Customer Managed" or model == 'Imagicle ' \
                                                                                                     'Customer Managed':
                if payload['model'] != 'Imagicle Customer Managed':
                    payload[
                        'model'] = "Generic IPPhone Customer Managed"  # Hard-code what the API expects (for now)
                data_needed = True
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
            response = webex_api_call('post', 'v1/devices', payload=payload)
            log.debug(f"\t{response}")

            # Get the ID of the device we just inserted
            device_id = response.get('id', None).replace('=', '')

            results = {
                'device_id': device_id,
                'mac': response['mac'],
                'device_object': Device(self.parent, config=response)
            }

            if data_needed is True:
                response = webex_api_call('get', f'/v1/telephony/config/devices/{device_id}')
                results['sip_auth_user'] = response['owner']['sipUserName']
                results['line_port'] = response['owner']['linePort']
                results['password'] = password
                results['sip_userpart'] = response['owner']['linePort'].split('@')[0]
                results['sip_hostpart'] = response['owner']['linePort'].split('@')[1]
                results['sip_outbound_proxy'] = response['proxy']['outboundProxy']
                results['sip_outbound_proxy_srv'] = f"_sips._tcp.{response['proxy']['outboundProxy']}"

        # Provide the Device instance in the response as well
        return results

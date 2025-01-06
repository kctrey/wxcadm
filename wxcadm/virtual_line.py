from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Union
from collections import UserList
import wxcadm
from .common import *
from .exceptions import *
from wxcadm import log
if TYPE_CHECKING:
    from wxcadm import Org, Location


class VirtualLine:
    def __init__(self, parent: Union[Org, Location], config: Optional[dict] = None):
        self.parent = parent
        """ The :class:`Org` or :class:`Location` to which the Virtual Line belongs """
        self.id: str = ''
        """ The ID of the Virtual Line """
        self.first_name: str = ''
        """ The first name of the Virtual Line """
        self.last_name: str = ''
        """ The last name of the Vierual Line """
        self.caller_id_first_name: str = ''
        """ The Caller ID first name of the Virtual Line """
        self.caller_id_last_name: str = ''
        """ The Caller ID last name of the Virtual Line """
        self.caller_id_number: str = ''
        """ The Caller ID number of the Virtual Line """
        self.external_caller_id_policy: str = ''
        """ The Caller ID Policy for presenting Caller ID externally """
        self.custom_external_caller_id_name: str = ''
        """ The custom Caller ID Name used for external calls """
        self.extension: Optional[str] = None
        """ The Virtual Line extension """
        self.esn: Optional[str] = None
        """ The Virtual Line ESN """
        self.phone_number: Optional[str] = None
        """ The Virtual Line phone number """
        self.location_id: str = ''
        """ The Location ID of the Virtual Line """
        self.billing_plan: str = ''
        """ The Virtual Line Billing Plan """
        self.num_devices_assigned: int = 0
        """ The number of devices that are assigned to the Virtual Line """

        # Dynamic attributes pulled by properties
        self._display_name: Optional[str] = None
        self._directory_search_enabled: Optional[bool] = None
        self._announcement_language: Optional[str] = None
        self._time_zone: Optional[str] = None
        self._devices: Optional[list] = None

        if config:
            self._process_config(config)

    def _process_config(self, config: dict) -> bool:
        self.id = config.get('id', '')
        self.first_name = config.get('firstName', '')
        self.last_name = config.get('lastName', '')
        self.caller_id_first_name = config.get('callerIdFirstName', '')
        self.caller_id_last_name = config.get('callerIdLastName', '')
        self.caller_id_number = config.get('callerIdNumber', '')
        self.external_caller_id_policy = config.get('externalCallerIdNamePolicy', '')
        if 'number' in config.keys():
            self.extension: Optional[str] = config['number'].get('extension', None)
            self.esn: Optional[str] = config['number'].get('esn', None)
            self.phone_number: Optional[str] = config['number'].get('external', None)
        if 'location' in config.keys():
            self.location_id: str = config['location'].get('id', '')
        self.billing_plan: str = config.get('billingPlan', '')
        self.num_devices_assigned: int = config.get('numberOfDevicesAssigned', 0)

        return True

    def _get_details(self) -> bool:
        config = webex_api_call('get', f'v1/telephony/config/virtualLines/{self.id}')
        self._display_name = config.get('displayName', '')
        self._directory_search_enabled = config.get('directorySearchEnabled', False)
        self._announcement_language = config.get('announcementLanguage', '')
        self._time_zone = config.get('timeZone', '')
        return True

    @property
    def org_id(self) -> str:
        """ The Org ID of the Virtual Line """
        return self.parent.org_id

    @property
    def display_name(self) -> str:
        """ The Display Name of the Virtual Line"""
        if self._display_name is None:
            self._get_details()
        return self._display_name

    @property
    def directory_search_enabled(self) -> bool:
        """ Flag to indicate Directory Search """
        if self._directory_search_enabled is None:
            self._get_details()
        return self._directory_search_enabled

    @property
    def announcement_language(self) -> str:
        """ The announcement language """
        if self._announcement_language is None:
            self._get_details()
        return self._announcement_language

    @property
    def time_zone(self) -> str:
        """ The time zone of the Virtual Line"""
        if self._time_zone is None:
            self._get_details()
        return self._time_zone

    def get_call_recording(self):
        """The Call Recording config for the Person

        Returns:
            dict: The Call Recording config for the Person instance

        """
        log.info(f"Getting Call Recording config for {self.display_name}")
        response = webex_api_call('get',
                                             f"v1/telephony/config/virtualLines/{self.id}/callRecording")
        return response

    def enable_call_recording(self, type: str,
                              record_vm: bool = False,
                              announcement_enabled: bool = False,
                              reminder_tone: bool = False,
                              reminder_interval: int = 30,
                              can_play: bool = True,
                              can_download: bool = True,
                              can_delete: bool = True,
                              can_share: bool = True,
                              transcribe: bool = True,
                              ai_summary: bool = True):
        """ Enable and configure Call Recording for the Virtual Line

        .. note::

            Some parameters, such as ``'transcribe'`` and ``'can_play'`` only apply to call recording done by the Webex
            platform. If the recording is being done by another provider, these parameters will have no effect.

        Args:
            type (str): The type of Call Recording. Value must be 'always', 'never', 'always_with_pause' or 'on_demand'
            record_vm (bool, optional): Whether to record Voicemail. Defaults to False
            announcement_enabled (bool, optional): Whether to announce Call Recording. Defaults to False
            reminder_tone (bool, optional): Whether to play a reminder tone. Defaults to False
            reminder_interval (int, optional): Interval in seconds between reminders. Defaults to 30
            can_play (bool, optional): Whether the user can play recordings. Defaults to True.
            can_download (bool, optional): Whether the user can download recordings. Defaults to True.
            can_delete (bool, optional): Whether the user can delete recordings. Defaults to True.
            can_share (bool, optional): Whether the user can share recordings. Defaults to True.
            transcribe (bool, optional): Enable AI transcription of recordings. Defaults to True.
            ai_summary (bool, optional): Enable AI summary of recordings. Defaults to True.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Enabling Call Recording for {self.display_name}")
        type_map = {"always": "Always",
                    "never": "Never",
                    "always_with_pause": "Always with Pause/Resume",
                    "on_demand": "On Demand with User Initiated Start"}
        if type not in type_map.keys():
            raise ValueError("'type' must be 'always', 'never', 'always_with_pause' or 'on_demand'.")
        payload = {"enabled": True,
                   "record": type_map[type],
                   "recordVoicemailEnabled": record_vm,
                   "startStopAnnouncementEnabled": announcement_enabled,
                   "notification": {
                       "type": "Beep",
                       "enabled": reminder_tone,
                       "repeat": {
                           "enabled": reminder_tone,
                           "interval": reminder_interval
                       }
                   },
                   "callRecordingAccessSettings": {
                       "viewAndPlayRecordingsEnabled": can_play,
                       "downloadRecordingsEnabled": can_download,
                       "deleteRecordingsEnabled": can_delete,
                       "shareRecordingsEnabled": can_share
                   },
                   "postCallRecordingSettings": {
                       "transcriptEnabled": transcribe,
                       "summaryAndActionItemsEnabled": ai_summary
                   }
                   }
        response = webex_api_call('put', f"v1/telephony/config/virtualLines/{self.id}/callRecording",
                                  payload=payload, params={'orgId': self.org_id})
        log.debug(f"Response: {response}")
        return True

    def disable_call_recording(self):
        """ Disables Call Recording for the Virtual Line

        This method will return True even if the Virtual Line did not have Call Recording enabled prior to calling
        the method.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Disabling Call Recording for {self.display_name}")
        recording_config = {'enabled': False}
        response = webex_api_call('put', f"v1/telephony/config/virtualLines/{self.id}/callRecording",
                                  payload=recording_config, params={'orgId': self.org_id})
        log.debug(f"Response: {response}")
        return True

    def refresh_config(self) -> bool:
        """ Refresh the Virtual Line configuration from Webex This is especially useful when a new Virtual Line is
        created and the configuration is not known. """
        log.info(f"Refreshing Virtual Line config: {self.id}")
        response = webex_api_call('get', f'v1/telephony/config/virtualLines', params={'id': self.id})
        self._process_config(response['virtualLines'][0])
        return True

    def delete(self) -> bool:
        """ Delete the Virtual Line """
        log.info(f"Deleting Virtual Line: {self.first_name} {self.last_name} ({self.id})")
        webex_api_call('delete', f'v1/telephony/config/virtualLines/{self.id}')
        return False

    def _build_put_payload(self) -> dict:
        payload = {
            'firstName': self.first_name,
            'lastName': self.last_name,
            'displayName': self.display_name,
            'phoneNumber': self.phone_number,
            'extension': self.extension,
            'announcementLanguage': self.announcement_language,
            'callerIdFirstName': self.caller_id_first_name,
            'callerIdLastName': self.caller_id_last_name,
            'callerIdNumber': self.caller_id_number,
            'timeZone': self.time_zone
        }
        return payload

    def update(self, **kwargs):
        """ Update the Virtual Line

        To update attributes, pass those attributes as arguments. For example, to update the :attr:`phone_number`, call
        the method as `update(phone_number='+15552345678')`. To update multiple attributes, include them as arguments.
        For example, `update(first_name='Joe', last_name='User')` will update both the first and last name.

        Args:
            **kwargs: All attributes are supported except :attr:`devices`, wghich has its own methods

        Returns:
            bool: True on success, False otherwise

        Raises:
            AttributeError: Raised when attempting to change a non-existing attribute
            APIError: Raised when the Webex API rejects the change

        """
        log.info(f"Updating Virtual Line with ID {self.id}")
        for attr, val in kwargs.items():
            getattr(self, attr)
            setattr(self, attr, val)
        response = webex_api_call('put', f'v1/telephony/config/virtualLines/{self.id}',
                                  payload=self._build_put_payload())
        return True

    @property
    def ecbn(self) -> dict:
        """ The Emergency Callback Number details of the Virtual Line """
        response = webex_api_call('get', f'v1/telephony/config/virtualLines/{self.id}/emergencyCallbackNumber',
                                  params={'orgId': self.parent.org_id})
        return response

    def set_ecbn(self, value: Union[str, wxcadm.Person, wxcadm.Workspace, wxcadm.VirtualLine]):
        """ Set the ECBN of the Virtual Line

        Valid values are ``'direct'``, ``'location'``, or a :class:`Person`, :class:`Workspace`, or
        :class:`VirtualLine` to set the ECBN to one of those.

        Args:
            value (str, Person, Workspace, VirtualLine): The value to set the ECBN to

        Returns:
            bool: True on success

        """
        if isinstance(value, wxcadm.Person) or \
                isinstance(value, wxcadm.Workspace) or \
                isinstance(value, wxcadm.VirtualLine):
            payload = {
                'selected': 'LOCATION_MEMBER_NUMBER',
                'locationMemberId': value.id
            }
        elif value.lower() == 'direct' or value.lower() == 'direct_line':
            payload = {'selected': 'DIRECT_LINE'}
        elif value.lower() == 'location' or value.lower() == 'location_ecbn':
            payload = {'selected': 'LOCATION_ECBN'}
        else:
            raise ValueError('Unknown value')

        response = webex_api_call('put', f'v1/telephony/config/virtualLines/{self.id}/emergencyCallbackNumber',
                                  params={'orgId': self.org_id}, payload=payload)
        return response


class VirtualLineList(UserList):
    _endpoint = "v1/telephony/config/virtualLines"
    _endpoint_items_key = 'virtualLines'
    _item_endpoint = "v1/telephony/config/virtualLines/{item_id}"
    _item_class = VirtualLine

    def __init__(self, parent: Union[Org, Location]):
        super().__init__()
        log.debug("Initializing VirtualLineList")
        self.parent: Org | Location = parent
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

    def get(self,
            id: Optional[str] = None,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            name: Optional[str] = None) -> Optional[VirtualLine]:
        """ Get the instance associated with a given ID or name.

        When searching by name, both `first_name` and `last_name` are required. Webex does not have a single key value
        other than ID, but the combination of first and last name must be unique. For names with only a single first
        name and single last name, such as 'Joe Smith', the ``name`` argument can be used as a shortcut.

        Args:
            id (str, optional): The Virtual Line ID to find
            first_name (str, optional): The first name of the Virtual Line
            last_name (str, optional): The last name of the Virtual Line
            name (str, optional): The full name (first and last) of the Virtual Line

        Returns:
            VirtualLine: The VirtualLine instance correlating to the given search argument. None is returned if no
                match is found

        Raises:
            ValueError: Raised when the method is called with no arguments or when called with only one name field

        """
        if id is not None:
            for item in self.data:
                if item.id == id:
                    return item
        if first_name is not None or last_name is not None or name is not None:
            if name is not None and first_name is None and last_name is None:
                first_name, last_name = name.split(' ', 1)
            if first_name and last_name:
                for item in self.data:
                    if item.first_name.lower() == first_name.lower() and item.last_name.lower() == last_name.lower():
                        return item
            else:
                raise ValueError("Both first_name and last_name are required to get by name")
        return None

    def create(
            self,
            first_name: str,
            last_name: str,
            phone_number: Optional[str] = None,
            extension: Optional[str] = None,
            location: Union[Location, str, None] = None,
            caller_id_first_name: Optional[str] = None,
            caller_id_last_name: Optional[str] = None,
            caller_id_number: Optional[str] = None
    ):
        """ Add a new Virtual Line

        When the :attr:`virtual_lines` is obtained at the :class:`Org` level, a ``location`` argument must be passed.
        When the :attr:`virtual_lines` is obtained at the :class:`Location` level, the ``location`` argument is
        not needed and assumed to be the :class:`Location` of the :attr:`virtual_lines`.

        Args:
            first_name (str): The first name of the Virtual Line
            last_name (str): The last name of the Virtual Line
            phone_number (str, optional): The phone number (DID) of the Virtual Line
            extension (str, optional): The extension of the Virtual Line
            location (Location, str, optional): The Location ID (str) or :class:`Location` instance
            caller_id_first_name (str, optional): The first name to user for Caller ID, if different from `first_name`
            caller_id_last_name (str, optional): The last name to use for Caller ID, if different from `last_name`
            caller_id_number (str, optional): The phone number to use for Caller ID if different from `phone_number`

        Returns:
            VirtualLine: The :class:`VirtualLine` that was added

        Raises:
            ValueError: Raised when both `extension` and `phone_number` are None. One or both are required
            APIError: Raised when the Virtual Line creation is rejected by the Webex API

        """
        log.info(f"Adding a Virtual Line to {self.parent.name}")
        # Make sure they passed a phone number or extension
        if phone_number is None and extension is None:
            raise ValueError("A phone_number, extension or both is required.")

        # Determine the location to add the VL to
        # If the List is at the Location level, use that Location
        if isinstance(self.parent, wxcadm.Location):
            log.debug(f"Using {self.parent.name} as target Location")
            location = self.parent
        # Get the Location ID to use for the payload
        if isinstance(location, wxcadm.Location):
            log.debug(f"Using {location.name} as Target Location")
            location_id = location.id
        elif isinstance(location, str):
            log.debug(f"Using {location} as target Location")
            location_id = location
        else:
            log.warn(f"Cannot determine target location using {location}")
            raise ValueError("Location or str required for location argument")
        # Build the payload
        payload = {
            'firstName': first_name,
            'lastName': last_name,
            'phoneNumber': phone_number,
            'extension': extension,
            'locationId': location_id,
            'callerIdFirstName': caller_id_first_name,
            'callerIdLastName': caller_id_last_name,
            'callerIdNumber': caller_id_number
        }

        response = webex_api_call('post', self._endpoint, payload=payload)
        new_entry_id = response['id']
        new_entry = self._item_class(self.parent, config={'id': new_entry_id})
        return new_entry

from __future__ import annotations

from typing import Optional, Union
from collections import UserList
import json
import requests

import wxcadm.location
from wxcadm import log
from .common import *


class ComplianceAnnouncementSettings:
    def __init__(self, parent: wxcadm.Org | wxcadm.Location,
                 inboundPSTNCallsEnabled: bool,
                 outboundPSTNCallsEnabled: bool,
                 outboundPSTNCallsDelayEnabled: bool,
                 delayInSeconds: int,
                 useOrgSettingsEnabled: Optional[bool] = None):
        self.parent: wxcadm.Org | wxcadm.Location = parent
        """ The :class:`Org` or :class:`Location` that the settings apply to """
        self.inbound_pstn_calls_enabled: bool = inboundPSTNCallsEnabled
        """ Play compliance announcement for inbound PSTN calls """
        self.outbound_pstn_calls_enabled: bool = outboundPSTNCallsEnabled
        """ Play compliance announcement for outbound PSTN calls """
        self.outbound_pstn_calls_delay_enabled: bool = outboundPSTNCallsDelayEnabled
        """ Delay the compliance announcement for a number of seconds for outbound PSTN calls """
        self.delay: int = delayInSeconds
        """ The number of seconds to delay the message for outbound calls, if enabled """
        self.use_org_settings: Optional[bool] = useOrgSettingsEnabled
        """ For Location-level Compliance Announcements, whether to override the Org settings (False) """

    def to_webex(self) -> dict:
        """ Represent the instance as a dict with the Webex field names as keys

        Returns:
            dict: The dict of Webex-friendly field names::

                {
                    'inboundPSTNCallsEnabled': self.inbound_pstn_calls_enabled,
                    'outboundPSTNCallsEnabled': self.outbound_pstn_calls_enabled,
                    'outboundPSTNCallsDelayEnabled': self.outbound_pstn_calls_delay_enabled,
                    'delayInSeconds': self.delay,
                    'useOrgSettingsEnabled': self.use_org_settings
                }

        """
        webex_dict = {
            'inboundPSTNCallsEnabled': self.inbound_pstn_calls_enabled,
            'outboundPSTNCallsEnabled': self.outbound_pstn_calls_enabled,
            'outboundPSTNCallsDelayEnabled': self.outbound_pstn_calls_delay_enabled,
            'delayInSeconds': self.delay,
            'useOrgSettingsEnabled': self.use_org_settings
        }
        return webex_dict

    def to_json(self) -> str:
        """ Represent the instance as a JSON string

        Returns:
            str: The JSON representation of the configuration

        """
        return json.dumps(self.to_webex())

    def push(self) -> bool:
        """ Push any changes (the existing instance config) back to Webex

        Returns:
            bool: True on success, False otherwise

        """
        if isinstance(self.parent, wxcadm.Org):
            pass
        pass


class Recording:
    """ The class for Converged Recordings """
    def __init__(self, parent: wxcadm.Org, id: str, details: Optional[dict] = None, timezone: Optional[str] = None):
        self._timezone = timezone
        self.parent = parent
        self.id = id
        """ The Recording ID """
        self.details: dict
        """ The full details of the Recording from Webex """
        if details is None:
            self.details = self._get_details()
        else:
            self.details = details

    def _get_details(self):
        params = {'timezone': self._timezone} if self._timezone else None
        response = webex_api_call('get', f'v1/convergedRecordings/{self.id}', params=params)
        return response

    @property
    def status(self) -> str:
        """ The status of the Recording """
        status = self.details.get('status', self._get_details()['status'])
        return status

    @property
    def url(self) -> str:
        """ The URL to download the recording """
        download = self.details.get('temporaryDirectDownloadLinks', self._get_details()['temporaryDirectDownloadLinks'])
        log.debug(download)
        return download['audioDownloadLink']

    @property
    def download_expires(self) -> str:
        """ The expiration date and time of the :attr:`url` """
        download = self.details.get('temporaryDirectDownloadLinks', self._get_details()['temporaryDirectDownloadLinks'])
        return download['expiration']

    @property
    def file_format(self) -> str:
        """ The format of the recording file """
        file_format = self.details.get('format', self._get_details()['format'])
        return file_format

    @property
    def duration(self) -> int:
        """ The duration of the recording, in seconds """
        duration = self.details.get('durationSeconds', self._get_details()['durationSeconds'])
        return duration

    @property
    def file_size(self) -> int:
        """ The size of the recording file, in bytes """
        file_size = self.details.get('sizeBytes', self._get_details()['sizeBytes'])
        return file_size

    @property
    def topic(self) -> str:
        """ The Topic or Description of the Recording """
        topic = self.details.get('topic', "")
        return topic

    @property
    def service_type(self) -> str:
        """ The Service Type that created the Recording """
        service_type = self.details.get('serviceType', self._get_details()['serviceType'])
        return service_type

    @property
    def storage_region(self) -> str:
        """ The region where the Recording is stored """
        region = self.details.get('storageRegion', self._get_details()['storageRegion'])
        return region

    @property
    def created(self) -> str:
        """ The date and time the recording file was created """
        created = self.details.get('createTime', self._get_details()['createTime'])
        return created

    @property
    def recorded(self) -> str:
        """ The date and time the call was recorded """
        recorded = self.details.get('timeRecorded', self._get_details()['timeRecorded'])
        return recorded

    @property
    def owner_id(self) -> str:
        """ The UUID of the :class:`Person`, :class:`Workspace` or :class:`VirtualLine` that was recorded """
        owner_id = self.details.get('ownerId', self._get_details()['ownerId'])
        return owner_id

    @property
    def owner_type(self) -> str:
        """ The type (user, workspace, virtual line) of the :attr:`owner_id` """
        owner_type = self.details.get('ownerType', self._get_details()['ownerType'])
        return owner_type

    @property
    def owner_email(self) -> str:
        """ The email address of the owner, if owned by something that supports email address """
        owner_email = self.details.get('ownerEmail', self._get_details()['ownerEmail'])
        return owner_email

    @property
    def location_id(self) -> Optional[str]:
        """ For Calling service recordings, the Location ID of the :attr:`owner_id` """
        if self.service_type.lower() != 'calling':
            return None
        location_id = self.details['serviceData']['locationId']
        return location_id

    @property
    def call_session_id(self) -> Optional[str]:
        """ For Calling service recordings, the Call Session ID of the Recording """
        if self.service_type.lower() != 'calling':
            return None
        session = self.details['serviceData']['callSessionId']
        return session

    def download(self, filename: str):
        """ Download the recording file to the local machine

        Args:
            filename (str): The filename to save the Recording to

        Returns:
            bool: True on success

        """
        response = requests.get(self.url)
        with open(filename, 'wb') as f:
            f.write(response.content)
        return True


class RecordingList(UserList):
    _endpoint = 'v1/admin/convergedRecordings'
    _endpoint_items_key = None
    _item_endpoint = 'v1/convergedRecordings/{item_id}'
    _item_class = Recording

    def __init__(self, parent: wxcadm.Org,
                 from_date_time: Optional[str] = None,
                 to_date_time: Optional[str] = None,
                 status: Optional[str] = None,
                 service: Optional[str] = None,
                 owner: Optional[Union[wxcadm.Person, wxcadm.Workspace, wxcadm.VirtualLine]] = None,
                 region: Optional[str] = None,
                 location: Optional[wxcadm.Location] = None
                 ):
        super().__init__()
        log.debug("Initializing RecordingList")
        self.parent: wxcadm.Org = parent
        self.params = {'max': 100}
        if from_date_time is not None:
            self.params['from'] = str(from_date_time)
        if to_date_time is not None:
            self.params['to'] = str(to_date_time)
        if status is not None:
            self.params['status'] = str(status)
        if service is not None:
            self.params['serviceType'] = str(service)
        if owner is not None:
            self.params['ownerId'] = str(owner.id)
        if region is not None:
            self.params['storageRegion'] = str(region)
        if location is not None:
            self.params['locationId'] = location.id
        self.data: list = self._get_data()

    def _get_data(self) -> list:
        log.debug(f"_get_data() started with params {self.params}")
        response = webex_api_call('get', self._endpoint, params=self.params)

        items = []
        for entry in response:
            items.append(self._item_class(parent=self.parent, id=entry['id'], details=entry))
        return items

    def refresh(self):
        """ Refresh the list of instances from Webex

        Returns:
            bool: True on success, False otherwise.

        """
        self.data = self._get_data()
        return True

    def get(self, id: str):
        """ Get the instance associated with a given Recording ID

        Args:
            id (str): The Recording ID to find

        Returns:
            Recording: The :class:`Recording` instance correlating with the given ID

        """
        for item in self.data:
            if item.id == id:
                return item
        return None

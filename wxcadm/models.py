from typing import NamedTuple, Optional, Union
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config

import wxcadm
from .common import *


class LocationEmergencySettings(NamedTuple):
    """ Enhanced Emergency Call Settings (i.e. RedSky settings) for a Location """
    integration: bool
    """ Whether location data is being sent to RedSky """
    routing: bool
    """ Whether 911 calls are being routed to RedSky"""


@dataclass_json
@dataclass
class OutboundProxy:
    """ Outbound Proxy configuration """
    service_type: str = field(metadata=config(field_name="sipAccessServiceType"))
    """ What the Outbound Proxy is used for """
    dns_type: str = field(metadata=config(field_name="dnsType"))
    """ The type of DNS record represented by the Outbound Proxy """
    proxy_address: str = field(metadata=config(field_name="outboundProxy"))
    """ The hostname of the Outbound Proxy """
    srv_prefix: Optional[str] = field(metadata=config(field_name="srvPrefix"), default=None)
    """ The SRV prefix to use if the DNS type is SRV """
    cname_records: Optional[str] = field(metadata=config(field_name="cnameRecords"), default=None)
    """ Any CNAME records associated with the Outbound Proxy """
    attachment_updated: bool = field(metadata=config(field_name="attachmentUpdated", exclude=lambda t: True), default=False)
    """ Whether the Outbound Proxy was updated """

@dataclass_json
@dataclass
class BargeInSettings:
    parent: object = field(repr=False)
    """ Barge-In Settings for a Person or Workspace """
    enabled: bool = field(metadata=config(field_name="enabled"))
    """ Whether Barge-In is enabled """
    tone_enabled: bool = field(metadata=config(field_name="toneEnabled"))
    """ Whether the Barge-In tone is enabled """

    def __post_init__(self):
        if isinstance(self.parent, wxcadm.Workspace):
            self._url = f"v1/telephony/config/workspaces/{self.parent.id}/bargeIn"
        else:
            self._url = f"v1/people/{self.parent.id}/features/bargeIn"

    def set_enabled(self, enabled: bool) -> bool:
        """ Set the enabled state of the Barge-In settings """
        payload = {"enabled": enabled, "toneEnabled": self.tone_enabled}
        response = webex_api_call('put', self._url, payload=payload,
                                  params={'orgId': self.parent.org_id})
        if response:
            return True
        else:
            return False

    def set_tone_enabled(self, enabled: bool) -> bool:
        """ Set the tone enabled state of the Barge-In settings """
        payload = {"enabled": self.enabled, "toneEnabled": enabled}
        response = webex_api_call('put', self._url, payload=payload,
                                  params={'orgId': self.parent.org_id})
        if response:
            return True
        else:
            return False



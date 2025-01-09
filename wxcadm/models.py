from typing import NamedTuple, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config


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



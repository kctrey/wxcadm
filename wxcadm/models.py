from typing import NamedTuple, Optional

class LocationEmergencySettings(NamedTuple):
    """ Enhanced Emergency Call Settings (i.e. RedSky settings) for a Location """
    integration: bool
    """ Whether location data is being sent to RedSky """
    routing: bool
    """ Whether 911 calls are being routed to RedSky"""

class OutboundProxy(NamedTuple):
    service_type: str
    """ What the Outbound Proxy is used for """
    dns_type: str
    """ The type of DNS record represented by the Outbound Proxy """
    proxy_address: str
    """ The hostname of the Outbound Proxy """
    srv_prefix: Optional[str] = None
    """ The SRV prefix to use if the DNS type is SRV """
    cname_records: Optional[str] = None
    """ Any CNAME records associated with the Outbound Proxy """
    attachment_updated: bool = False
    """ Whether the Outbound Proxy was updated """



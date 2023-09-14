from __future__ import annotations

from typing import Optional
import json

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


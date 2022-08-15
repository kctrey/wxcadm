from __future__ import annotations

from collections import UserList
from dataclasses import dataclass, field
from typing import Union
from wxcadm import log
from .common import *


class CallRouting:
    def __init__(self, org: Org):
        self.org = org
        pass

    @property
    def trunks(self):
        return Trunks(self.org)


class Trunks(UserList):
    def __init__(self, org: Org):
        log.info('Initializing Trunks instance')
        super().__init__()
        self.org = org
        self.data = []
        items = webex_api_call('get', '/v1/telephony/config/premisePstn/trunks')
        log.debug(f'Trunks from Webex: {items}')
        for item in items['trunks']:
            this_trunk = Trunk(self.org, **item)
            self.data.append(this_trunk)


@dataclass
class Trunk:
    org: Org = field(repr=False)
    """ The Org to which the Trunk belongs """
    id: str
    """ The unique identifier of the Trunk """
    name: str
    """ The text name of the Trunk """
    location: Union[dict, Location]
    """ The Location instance associated with the Trunk """
    inUse: bool
    """ Whether the Trunk is in use """
    trunkType: str
    """ The type of Trunk, either 'REGISTERING' or 'CERTIFICATE_BASED' """

    def __post_init__(self):
        log.debug(f'Finding Location instance: {self.location}')
        # Since we only have a dict of the trunk location, go get the actual Location instance
        my_location = self.org.get_location(id=self.location['id'])
        if my_location is not None:
            self.location = my_location

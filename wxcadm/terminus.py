from __future__ import annotations

import requests
import wxcadm
from wxcadm import log
from .common import *
from .exceptions import *


class Terminus:
    """The Terminus class handles API calls using the Terminus API."""

    def __init__(self, org: wxcadm.Org, access_token: str):
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the "customer" ID from the Org ID
        spark_id = decode_spark_id(org.id)
        self._customer = spark_id.split("/")[-1]

        self._url_base = f"https://terminus.huron-dev.com/api/v2/customers/{self._customer}/"
        self._server = "https://terminus.huron-dev.com"

    def get_locations(self):
        log.info("Getting locations from Terminus")
        r = requests.get(self._url_base + "locations", headers=self._headers)
        if r.ok:
            locations = r.json()
            for location in locations:
                webex_location = self._parent.locations.get(name=location['name'])
                webex_location.terminus_config = location
            return locations
        else:
            raise APIError("Your API Access Token does not have permission to get the locations from Terminus.")

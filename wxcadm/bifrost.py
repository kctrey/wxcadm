from __future__ import annotations

import requests
import wxcadm
from .exceptions import *
from .common import *


class Bifrost:
    """The Bifrost class handles API calls using the Bifrost API."""

    def __init__(self, org: wxcadm.Org, access_token: str):
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the "customer" ID from the Org ID
        spark_id = decode_spark_id(org.id)
        self._customer = spark_id.split("/")[-1]

        self._url_base = f"https://bifrost-a.wbx2.com/api/v2/customers/{self._customer}/"
        self._server = "https://bifrost-a.wbx2.com"

    def get_location(self):
        locations = []
        params = {"limit": 2000, "offset": 0}   # Default values for the numbers pull

        get_more = True     # Bool to let us know to keep pulling more numbers
        next_url = None
        while get_more:
            if next_url is None:
                r = requests.get(self._url_base + f"locations", headers=self._headers, params=params)
            else:
                r = requests.get(next_url, headers=self._headers)
            if r.status_code == 200:
                response = r.json()
                locations.extend(response['locations'])
                if "next" in response['paging']:
                    get_more = True
                    next_url = response['paging']['next']
                else:
                    get_more = False
            elif r.status_code == 403:
                raise TokenError("Your API Access Token doesn't have permission to use this API call")
            else:
                raise APIError(f"The Bifrost locations call did not return a successful value")

        for location in locations:
            if "name" in location:
                webex_location = self._parent.locations.get(name=location['name'])
                webex_location.bifrost_config = location
        return locations

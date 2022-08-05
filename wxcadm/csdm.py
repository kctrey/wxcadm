from __future__ import annotations

import base64

from wxcadm import log

class CSDM:
    """The base class for dealing with devices"""
    def __init__(self, org: Org, access_token: str):
        """ Initialize a CSDM instance for an :class:`Org`

        Args:
            org (Org): The Org instance which is the parent of this CSDM instance
            access_token (str): The API Access Token that is used to access the CSDM API. Usually the same access
                token that is used by the Org
        """

        log.info("Initializing CSDM instance")
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the CSDM "organization" ID from the Org ID
        org_id_bytes = base64.b64decode(org.id + "===")
        org_id_decoded = org_id_bytes.decode("utf-8")
        self._organization = org_id_decoded.split("/")[-1]

        self._url_base = f"https://csdm-a.wbx2.com/csdm/api/v1/organization/{self._organization}/devices/"
        self._server = "https://csdm-a.wbx2.com"

        self._devices: list = []

    def get_devices(self, with_location: bool = False):
        """ Get a list of all the Device instances from CSDM

        Args:
            with_location (bool, optional): Whether to populate the .location attribute with the Webex Calling
                :class:`Location` instance. The API calls to do this take some time, so it defaults to **False**.

        Returns:
            list[Device]: A list of all the :class:`Device` instances

        .. warning::

            This method requires the CP-API access scope.

        """
        log.info("Getting devices from CSDM")
        devices_from_csdm = []
        payload =  {"query": None,
                    "aggregates": ["connectionStatus",
                                   "category",
                                   "callingType"
                                   ],
                    "size": 100,
                    "from": 0,
                    "sortField": "category",
                    "sortOrder": "asc",
                    "initial": True,
                    "translatedQueryString": ""
                    }
        r = requests.post(self._url_base + "_search", headers=self._headers, json=payload)
        if r.ok:
            response = r.json()
            log.debug(f"Received {len(response['hits']['hits'])} devices out of {response['hits']['total']}")
            devices_from_csdm.extend(response['hits']['hits'])
            # If the total number of devices is greater than what we received, we need to make the call again
            keep_going = True
            while keep_going:
                if len(devices_from_csdm) < response['hits']['total']:
                    log.debug("Getting more devices")
                    payload['from'] = len(devices_from_csdm)
                    r = requests.post(self._url_base + "_search", headers=self._headers, json=payload)
                    if r.ok:
                        response = r.json()
                        log.debug(f"Received {len(response['hits']['hits'])} more devices")
                        devices_from_csdm.extend(response['hits']['hits'])
                    else:
                        log.error("Failed getting more devices")
                        raise CSDMError("Error getting more devices")
                else:
                    keep_going = False
        else:
            log.error(("Failed getting devices"))
            raise CSDMError("Error getting devices")

        self._devices = []
        log.debug("Creating Device instances")
        for device in devices_from_csdm:
            this_device = Device(self, device)
            if with_location is True:
                # Get the device location with another search via CPAPI
                log.debug(f"Getting Device Location via CPAPI: {this_device.display_name}")
                if "ownerId" in device:
                    device_location: Location = self._parent._cpapi.get_workspace_calling_location(device['ownerId'])
                    log.debug(f"\tLocation: {device_location.name}")
                    this_device.calling_location = device_location
            self._devices.append(this_device)

        return self._devices

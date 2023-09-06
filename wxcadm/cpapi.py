from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .person import Person
import requests
import base64
import os
from requests_toolbelt import MultipartEncoder
import wxcadm
from wxcadm import log
from .exceptions import *
from .common import *


class CPAPI:
    """The CPAPI class handles API calls using the CP-API, which is the native API used by Webex Control Hub.

    .. note::
            CPAPI instances are normally not instantiated manually and are done automatically with various Org methods.

    .. warning::

            All the methods in this class require an API Access Token with the CP-API scope.
    """

    def __init__(self, org: wxcadm.Org, access_token: str):
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the "customer" ID from the Org ID
        spark_id = decode_spark_id(org.id)
        self._customer = spark_id.split("/")[-1]

        self._url_base = f"https://cpapi-a.wbx2.com/api/v1/customers/{self._customer}/"
        self._server = "https://cpapi-a.wbx2.com"

    def set_global_vm_pin(self, pin: str):
        """Set the Org-wide default VM PIN

        Args:
            pin (str): The PIN to set as the global default

        Returns:
            bool: True if successful

        Raises:
            ValueError: Raised when the PIN value is rejected by Webex, usually because the PIN doesn't comply
                with the security policy.

        """
        log.info("Setting Org-wide default VM PIN")
        payload = {
            "defaultVoicemailPinEnabled": True,
            "defaultVoicemailPin": str(pin)
        }
        r = requests.patch(self._url_base + "features/voicemail/rules",
                           headers=self._headers, json=payload)
        if r.ok:
            return True
        if r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise ValueError

    def clear_global_vm_pin(self):
        log.info("Clearing Org-wide default VM PIN")
        payload = {
            "defaultVoicemailPinEnabled": False,
        }
        r = requests.patch(self._url_base + f"features/voicemail/rules",
                           headers=self._headers, json=payload)
        return r.text

    def reset_vm_pin(self, person: Person, pin: str = None):
        log.info(f"Resetting VM PIN for {person.email}")
        user_id = person.spark_id.split("/")[-1]

        if pin is not None:
            self.set_global_vm_pin(pin)

        r = requests.post(self._url_base + f"users/{user_id}/features/voicemail/actions/resetpin/invoke",
                          headers=self._headers)
        if r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")

        if pin is not None:
            self.clear_global_vm_pin()

        return True

    def get_numbers(self):
        # This method is deprecated and will likely be removed eventually. The Webex API now supports a Numbers GET
        numbers = []
        params = {"limit": 2000, "offset": 0}   # Default values for the numbers pull

        get_more = True     # Bool to let us know to keep pulling more numbers
        next_url = None
        while get_more:
            if next_url is None:
                r = requests.get(self._url_base + f"numbers", headers=self._headers, params=params)
            else:
                r = requests.get(next_url, headers=self._headers)
            if r.status_code == 200:
                response = r.json()
                numbers.extend(response['numbers'])
                if "next" in response['paging']:
                    get_more = True
                    next_url = response['paging']['next']
                else:
                    get_more = False
            elif r.status_code == 403:
                raise TokenError("Your API Access Token doesn't have permission to use this API call")
            else:
                raise APIError(f"The CPAPI numbers call did not return a successful value")

        for number in numbers:
            if "owner" in number:
                if "type" in number['owner'] and number['owner']['type'] == "USER":
                    user_str = f"ciscospark://us/PEOPLE/{number['owner']['id']}"
                    user_bytes = user_str.encode("utf-8")
                    base64_bytes = base64.b64encode(user_bytes)
                    base64_id = base64_bytes.decode('utf-8')
                    base64_id = base64_id.rstrip("=")
                    number['owner']['id'] = base64_id

        return numbers

    def change_workspace_caller_id(self, workspace_id: str, name: str, number: str):
        """ Changes the Caller ID for a Workspace using the CPAPI

        Since Webex Calling uses a different Workspace ID than the CPAPI, this method requires the ID that is recognized
        by CPAPI. The ``name`` and ``number`` arguments take the literal value to be written in the CPAPI payload. The
        methods in other classes that call this method are responsible for sending the correct value to be used.

        Args:
            workspace_id (str): The CPAPI Workspace (Place) ID
            name (str): The value to send to the CPAPI as the "externalCallerIdNamePolicy"
            number (str): The value to send to the CPAPI as the "selected" value

        Returns:
            bool: True on success. False otherwise

        Raises:
            wxcadm.exceptions.APIError: Raised when there is a problem with the API call

        """
        payload = {"externalCallerIdNamePolicy": name,
                   "selected": number}
        r = requests.patch(self._url_base + f"places/{workspace_id}/features/callerid",
                           headers=self._headers, json=payload)
        if r.ok:
            return True
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError("CPAPI failed to update Caller ID for Workspace")

    def get_workspace_calling_location(self, workspace_id: str):
        """ Gets the Location instance associated with a Workspace

        Because Webex Calling uses a different Location than th WorkspaceLocation, sometimes an admin needs to take
        action based on the Calling Location instead. This method takes the ID of the Workspace (from the Device
        instance held in the Webex.Org.devices list) and returns the :class:`Location` instance.

        Args:
            workspace_id (str): The Workspace ID (Device.owner_id) to match on

        Returns:
            Location: The Location instance for the Workspace. None is returned if there is no match.

        Raises:
            wxcadm.exceptions.APIError: Raised when there is a problem getting data from the API

        """
        log.info("CPAPI - Getting Calling Location")
        r = requests.get(self._url_base + f"places/{workspace_id}", headers=self._headers)
        if r.status_code == 200:
            response = r.json()
            location = self._parent.locations.get(name=response['location']['name'])
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError("Something went wrong getting the Workspace Calling Location")
        return location

    def upload_moh_file(self, location_id: str, filename: str):
        log.info("CPAPI - Uploading MOH File")
        # Calculate the "locations" ID from the Org ID
        loc_id_bytes = base64.b64decode(location_id + "===")
        loc_id_decoded = loc_id_bytes.decode("utf-8")
        location_id = loc_id_decoded.split("/")[-1]
        upload_as = os.path.basename(filename)
        content = open(filename, "rb")
        must_close = True

        encoder = MultipartEncoder(fields={"file": (upload_as, content, 'audio/wav')})
        log.info(encoder)
        r = requests.post(self._url_base + f"locations/{location_id}/features/musiconhold/actions/announcement",
                          headers={"Content-Type": encoder.content_type, **self._headers},
                          data=encoder)
        if must_close is True:
            content.close()
        if r.ok:
            return True
        elif r.status_code == 403:
            log.debug(f"Request headers: {r.request.headers}")
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError(f"Something went wrong uploading the MOH file: {r.text}")

    def upload_aa_greeting(self, autoattendant, type: str, filename: str):
        log.info("CPAPI - Uploading Auto Attendant Greeting")
        aa_id = autoattendant.spark_id.split("/")[-1]
        location_id = autoattendant.location.spark_id.split("/")[-1]
        if type == "business_hours":
            type = "businessgreetingupload"
        elif type == "after_hours":
            type = "afterhoursgreetingupload"
        else:
            raise ValueError("Valid type values are 'business_hours' and 'after_hours'")

        upload_as = os.path.basename(filename)
        content = open(filename, "rb")
        must_close = True
        encoder = MultipartEncoder(fields={"file": (upload_as, content, 'audio/wav')})
        url = self._url_base + f"locations/{location_id}/features/autoattendants/{aa_id}/actions/{type}/invoke"
        r = requests.post(url,
                          params={"customGreetingEnabled": True},
                          headers={"Content-Type": encoder.content_type, **self._headers},
                          data=encoder)
        if must_close is True:
            content.close()
        if r.ok:
            return True
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError(f"Something went wrong uploading the Greeting file: {r.text}")

    def set_custom_aa_greeting(self, autoattendant, type: str, filename: str):
        log.info("CPAPI - Setting Custom AA Greeting")
        aa_id = autoattendant.spark_id.split("/")[-1]
        location_id = autoattendant.location.spark_id.split("/")[-1]
        upload_as = os.path.basename(filename)
        if type == "business_hours":
            type = "businessHoursMenu"
        elif type == "after_hours":
            type = "afterHoursMenu"
        else:
            raise ValueError("Valid type values are 'business_hours' and 'after_hours'")
        config_dict = autoattendant.config[type]
        config_dict['greeting'] = "CUSTOM"
        config_dict['audioFile']['name'] = upload_as
        config_dict['audioFile']['mediaType'] = "WAV"

        payload = {"enabled": autoattendant.config['enabled'], "name": autoattendant.config['name'], **config_dict}

        r = requests.patch(self._url_base + f"locations/{location_id}/features/autoattendants/{aa_id}",
                           headers=self._headers, json=payload)

        if r.ok:
            return True
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError(f"Something went wrong setting the Custom Greeting: {r.text}")

    def set_custom_moh(self, location_id: str, filename: str):
        log.info("CPAPI - Setting Custom MOH")
        # Calculate the "locations" ID from the Org ID
        loc_id_bytes = base64.b64decode(location_id + "===")
        loc_id_decoded = loc_id_bytes.decode("utf-8")
        location_id = loc_id_decoded.split("/")[-1]
        payload = {"callHold": True, "callPark": True, "greeting": "CUSTOM", "description": filename}
        r = requests.patch(self._url_base + f"locations/{location_id}/features/musiconhold",
                           headers=self._headers, json=payload)
        if r.ok:
            return True
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError(f"Something went wrong setting the MOH: {r.text}")

    def set_default_moh(self, location_id: str):
        log.info("CPAPI - Setting Default MOH")
        # Calculate the "locations" ID from the Org ID
        loc_id_bytes = base64.b64decode(location_id + "===")
        loc_id_decoded = loc_id_bytes.decode("utf-8")
        location_id = loc_id_decoded.split("/")[-1]
        # The CPAPI PATCH needs the MOH filename, even for Default, so we need to get what's there already
        r = requests.get(self._url_base + f"locations/{location_id}/features/musiconhold",
                         headers=self._headers)
        current_config = r.json()
        payload = {"callHold": True, "callPark": True, "greeting": "SYSTEM", "description": current_config['description']}
        r = requests.patch(self._url_base + f"locations/{location_id}/features/musiconhold",
                           headers=self._headers, json=payload)
        if r.ok:
            return True
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError(f"Something went wrong setting the MOH: {r.text}")

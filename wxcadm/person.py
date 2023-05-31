from __future__ import annotations

import requests
from requests_toolbelt import MultipartEncoder
import base64
import os
from typing import Optional, Type
from dataclasses import dataclass, field
from collections import UserList

import wxcadm.exceptions
from .common import *
from .xsi import XSI
from .device import Device

from wxcadm import log


class Person:
    def __init__(self, user_id, parent: Type[Org] = None, config: dict = None):
        """ Initialize a new Person instance.

        If only the `user_id` is provided, the API calls will be made to get
        the config from Webex. To save on API calls, the config can be provided which will set the attributes
        without an API call.

        Args:
            user_id (str): The Webex ID of the person
            parent (object, optional): The parent object that created the Person instance. Used when the Person
                is created within the Org instance
            config (dict, optional): A dictionary of raw values from the `GET v1/people` items. Not normally used
                except for automated people population from the Org init.

        """
        self.id = user_id
        """The Webex ID of the Person"""
        self._parent = parent
        """The parent instance that created this Person"""
        # Attributes
        self.email: str = ""
        """The user's email address"""
        self.first_name: str = ""
        """The user's first name"""
        self.last_name: str = ""
        """The user's last name"""
        self.display_name: str = ""
        """The user's name as displayed in Webex"""
        self.wxc: bool = False
        '''True if this is a Webex Calling User'''
        self.licenses: list = []
        """List of licenses assigned to the person"""
        self.location: str = ""
        """The Webex ID of the user's assigned location"""
        self.roles: list = []
        """ The role IDs assigned to this Person in Webex"""
        self.vm_config: dict = {}
        '''Dictionary of the VM config as returned by Webex API with :meth:`get_vm_config()`'''
        self.call_recording: dict = {}
        """Dictionary of the Recording config as returned by Webex API with :meth:`get_call_recording()`"""
        self.barge_in: dict = {}
        """Dictionary of Barge-In config as returned by Webex API with :meth:`get_barge_in`"""
        self.call_forwarding: dict = {}
        """Dictionary of the Call Forwarding config as returned by Webex API 
        with :meth:`get_call_forwarding()`"""
        self.caller_id: dict = {}
        """Dictionary of Caller ID config as returned by Webex API with :meth:`get_caller_id()`"""
        self.intercept: dict = {}
        """Dictionary of Call Intercept config as returned by Webex API with :meth:`get_intercept()`"""
        self.dnd: dict = {}
        """Dictionary of DND settings as returned by Webex API with :meth:`get_dnd()`"""
        self.calling_behavior: dict = {}
        """Dictionary of Calling Behavior as returned by Webex API with :meth:`get_calling_behavior()`"""
        self.monitoring: dict = {}
        """Dictionary of Monitoring settings as returned by Webex API with :meth:`get_monitoring()`"""
        self.hoteling: dict = {}
        """Dictionary of Hoteling settings as returned by Webex API with :meth:`get_hoteling()`"""
        self.xsi = None
        """Holds the XSI instance when created with the :meth:`start_xsi()` method."""
        self.numbers: list = []
        """The phone numbers for this person from Webex CI"""
        self.extension: Optional[str] = None
        """The extension for this person"""
        self._hunt_groups: list = []
        """A list of the Hunt Group instances that this user is an Agent for"""
        self._call_queues: list = []
        """A list of the Call Queue instances that this user is an Agent for"""
        self.outgoing_permission: dict = {}
        """Dictionary of Outgoing Permission config returned by Webex API
        with :meth:`get_outgoing_permission()`"""
        self.applications_settings = None
        """ The Application Services Settings for this Person"""
        self.executive_assistant = None

        # API-related attributes
        self._headers = parent._headers
        self._params = {"orgId": parent.id, "callingData": "true"}

        # If the config was passed, process it. If not, make the API call for the Person ID and then process
        if config:
            self.__process_api_data(config)
        else:
            response = self.__get_webex_data(f"v1/people/{self.id}")
            self.__process_api_data(response)

    def __process_api_data(self, data: dict):
        """Takes the API data passed as the `data` argument and parses it to the instance attributes.

        Args:
            data (dict): A dictionary of the raw data returned by the `v1/people` API call

        """
        self.email = data['emails'][0]
        self.extension = data.get("extension", "")
        self.location = data.get("locationId", "")
        self.display_name = data.get("displayName", "")
        self.first_name = data.get("firstName", "")
        self.last_name = data.get("lastName", "")
        self.roles = data.get("roles", [])
        self.numbers = data.get("phoneNumbers", [])
        self.licenses = data.get("licenses", [])
        for license in self.licenses:
            if license in self._parent.wxc_licenses:
                self.wxc = True

    def __str__(self):
        return f"{self.email},{self.display_name}"

    def __repr__(self):
        return self.id

    # The following is to simplify the API call. Eventually I may open this as a public method to
    # allow arbitrary API calls
    def __get_webex_data(self, endpoint: str, params: dict = None):
        """ Issue a GET to the Webex API

        Args:
            endpoint (str): The endpoint of the call (i.e. "v1/people" or "/v1/people/{Person.id}")
            params (dict): Any additional params to be passed in the query (i.e. {"callingData":"true"}

        Returns:
            dict: The response from the Webex API

        """
        if params is None:
            params = {}
        log.debug(f"__get_webex_data started using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.get(_url_base + endpoint, headers=self._headers, params=my_params)
        if r.status_code in [200]:
            response = r.json()
            return response
        else:
            return False

    def __put_webex_data(self, endpoint: str, payload: dict, params: Optional[dict] = None):
        """Issue a PUT to the Webex API

        Args:
            endpoint: The endpoint of the call (i.e. "v1/people" or "/v1/people/{Person.id}")
            payload: A dict to send as the JSON payload of the PUT
            params: Any additional params to be passed in the query (i.e. {"callingData":"true"}

        Returns:
            bool: True if successful, False if not

        """
        if params is None:
            params = {}
        log.debug(f"__put_webex_data started using {endpoint}")
        my_params = {**params, **self._params}
        log.debug(f"Params: {params}")
        log.debug(f"Payload: {payload}")
        r = requests.put(_url_base + endpoint, headers=self._headers, params=my_params, json=payload)
        if r.ok:
            log.info("Push successful")
            return True
        else:
            log.warning("__put_webex_data() failed")
            log.debug(f"[{r.status_code}] {r.text}")
            return False

    @property
    def spark_id(self):
        """ The internal identifier used within Webex """
        user_id_bytes = base64.b64decode(self.id + "===")
        spark_id = user_id_bytes.decode("utf-8")
        return spark_id

    def role_names(self):
        """ Returns a list of the user's Roles, using the Role Name rather than the Role ID

        Returns:
            list: A list of Role names. None is returned if the Person has no administrative Roles

        """
        if len(self.roles) > 0:
            roles = []
            for role in self.roles:
                roles.append(self._parent.roles[role])
                return roles
            else:
                return None


    def assign_wxc(self, location: Type[Location], phone_number: str = None, extension: str = None):
        """ Assign Webex Calling to the user, along with a phone number and/or an extension.

        Args:
            location (Location): The Location instance to assign the Person to.
            phone_number (str, optional): The phone number to assign to the Person.
            extension (str, optional): The extension to assign to the Person

        Returns:
            bool: True on success, False if otherwise

        """
        # To assign Webex Calling to a Person, we need to find the License ID for Webex Calling Professional
        license = self._parent.get_wxc_person_license()
        self.licenses.append(license)

        # Call the update_person() method to update the new values.
        success = self.update_person(numbers=[{"type": "work", "value": phone_number}],
                                     extension=extension, location=location.id)
        if success:
            return True
        else:
            return False

    def start_xsi(self, get_profile: bool = False, cache: bool = False):
        """Starts an XSI session for the Person

        Args:
            get_profile (bool, optional): Whether to automatically get the XSI profile for the Person. Defaults to False
            cache (bool, optional): Whether to cache results so that the data doesn't need to be re-pulled from Webex.
                Defaults to False.

        Returns:
            XSI: The XSI instance for this Person
        """
        self.xsi = XSI(self, get_profile=get_profile, cache=cache)
        return self.xsi

    def reset_vm_pin(self, pin: str = None):
        """Resets the user's voicemail PIN.

        If no PIN is provided, the reset command is sent, and assumes that
        a default PIN exists for the organization. Because of the operation of Webex, if a PIN is provided, the
        method will temporarily set the Org-wide PIN to the chosen PIN, then does the reset, then un-sets the
        Org default in Control Hub. ***This can cause unintended consequences if a PIN is provided and the Org
        already has a default PIN** because that PIN will be un-set at the end of this method.

        Args:
            pin (str): The new temporary PIN to set for the Person

        Returns:
            bool: True on success, False otherwise

        .. warning::

            This method requires the CP-API access scope if you are going to specify the PIN. A "reset only" does not
            require any special access.

        """
        log.info(f"Resetting VM PIN for {self.email}")
        if pin is not None:
            self._parent._cpapi.reset_vm_pin(self, pin=pin)
            return True
        else:
            r = requests.post(_url_base + f"v1/people/{self.id}/features/voicemail/actions/resetPin/invoke",
                              headers=self._headers)
            if r.ok:
                return True
            else:
                log.warning("Reset VM PIN API call failed")
                return False

    def get_full_config(self):
        """
        Fetches all of the Webex Calling settings for the Person. Due to the number of API calls, this
        method is not performed automatically on Person init and should be called for each Person during
        any subsequent processing. If you are only interested in one of the features, calling that method
        directly can significantly improve the time to return data.

        """
        log.info(f"Getting the full config for {self.email}")
        if self.wxc:
            self.get_call_forwarding()
            self.get_vm_config()
            self.get_caller_id()
            self.get_call_recording()
            self.get_dnd()
            self.get_calling_behavior()
            self.get_caller_id()
            self.get_hoteling()
            self.get_barge_in()
            self.get_intercept()
            self.get_monitoring()
            self.get_outgoing_permission()
            return self
        else:
            log.info(f"{self.email} is not a Webex Calling user.")

    @property
    def usergroup(self):
        """ The :py:class:`UserGroup` that the Person is assigned to

        Returns:
            UserGroup: The :py:class:`UserGroup`. None is returned if the Person is not assigned to a Group

        """
        return self._parent.usergroups.find_person_assignment(self)

    @property
    def devices(self):
        """ List of :py:class:`Device` instances for the Person

        Returns:
            List

        """
        log.info(f"Collecting devices for {self.display_name}")
        devices = []
        response = webex_api_call('get', f'/v1/telephony/config/people/{self.id}/devices')
        log.debug(f"{response}")
        for item in response['devices']:
            this_device = Device(self, item)
            devices.append(this_device)
        return devices

    def add_device(self, model: str, mac: Optional[str] = None, password: Optional[str] = None):
        """ Add a new device to the Person

        In order to use this method, you must know the model of the device that you are adding, as expected by the
        Webex API. If you are adding a "Generic IPPhone Customer Managed" device, you can use that value or simply
        send ``model='GENERIC'`` as an alias. You can find the full list of models with the
        :py:meth:`Org.get_supported_devices()` method.

        If the MAC address is passed, a device will be created with the provided MAC address. If no MAC address is
        passed, an Activation Code will be generated and returned as part of the response. Your integration/token must
        have the ``identity:placeonetimepassword_create`` scope to create Activation Codes for devices.

        Args:
            model (str): The model name of the device being added
            mac (str, optional): The MAC address of the device being added
            password (str, optional): Only valid when creating a Generic IPPhone Customer Managed device. If a
                password is not provided, the Webex API will generate a unique, compliant SIP password and return it
                in the response.

        Returns:
            dict: The dict values vary based on the type of device being activated. If the device fails for any reason,
                False will be returned. At the moment, Webex doesn't provide very useful failure reasons, but those may
                be added to the return value when they are available.

        """
        log.info(f"Adding a device to {self.display_name}")
        payload = {
            "personId": self.id,
            "model": model
        }
        data_needed = False  # Flag that we need to get platform data once we have a Device ID
        if mac is None:
            # If no MAC address is provided, just generate an activation code for the device
            try:
                response = webex_api_call('post',
                                          '/v1/devices/activationCode',
                                          payload=payload,
                                          params={'orgId': self._parent.id})
                log.debug(f"\t{response}")
            except wxcadm.exceptions.APIError:
                return False

            # Get the ID of the device we just inserted
            device_id = response.get('id', None).replace('=', '')

            results = {
                'device_id': device_id,
                'activation_code': response['code']
            }
        else:
            payload['mac'] = mac
            if model.upper() == "GENERIC" or model.upper() == "Generic IPPhone Customer Managed":
                payload['model'] = "Generic IPPhone Customer Managed"  # Hard-code what the API expects (for now)
                data_needed = True
                if password is None:    # Generate a unique password
                    response = webex_api_call('POST',
                                                  f'/v1/telephony/config/locations/{self.location}/actions/'
                                                  f'generatePassword/invoke')
                    password = response['exampleSipPassword']
                payload['password'] = password
            response = webex_api_call('post', '/v1/devices', payload=payload)
            log.debug(f"\t{response}")

            # Get the ID of the device we just inserted
            device_id = response.get('id', None).replace('=', '')

            results = {
                'device_id': device_id,
                'mac': response['mac']
            }

            if data_needed is True:
                response = webex_api_call('get', f'/v1/telephony/config/devices/{device_id}')
                results['sip_auth_user'] = response['owner']['sipUserName']
                results['line_port'] = response['owner']['linePort']
                results['password'] = password
                results['sip_userpart'] = response['owner']['linePort'].split('@')[0]
                results['sip_hostpart'] = response['owner']['linePort'].split('@')[1]
                results['sip_outbound_proxy'] = response['proxy']['outboundProxy']
                results['sip_outbound_proxy_srv'] = f"_sips._tcp.{response['proxy']['outboundProxy']}"

        # Provide the Device instance in the response as well
        results['device_object'] = self._parent.get_device_by_id(device_id)
        return results

    @property
    def hunt_groups(self):
        """The Hunt Groups that this user is an Agent for.

        Returns:
            list[HuntGroup]: A list of the `HuntGroup` instances the user belongs to

        """
        log.info(f"Getting Hunt Groups for {self.email}")
        # First, we need to make sure we know about the Org's Hunt Groups. If not, pull them.
        if self._parent.hunt_groups is None:
            self._parent.get_hunt_groups()
        hunt_groups = []
        for hg in self._parent.hunt_groups:
            # Step through the agents for the Hunt Group to see if this person is there
            for agent in hg.agents:
                if agent['id'] == self.id:
                    hunt_groups.append(hg)
        self._hunt_groups = hunt_groups
        return self._hunt_groups

    @property
    def call_queues(self):
        """The Call Queues that this user is an Agent for.

        Returns:
            list[CallQueue]: A list of the `CallQueue` instances the user belongs to

        """
        log.info(f"Getting Hunt Groups for {self.email}")
        # First, we need to make sure we know about the Org's Hunt Groups. If not, pull them.
        if self._parent.call_queues is None:
            self._parent.get_call_queues()
        call_queues = []
        for cq in self._parent.call_queues:
            # Step through the agents for the Hunt Group to see if this person is there
            for agent in cq.config['agents']:
                if agent['id'] == self.id:
                    call_queues.append(cq)
        self._call_queues = call_queues
        return self._call_queues

    def get_call_forwarding(self):
        """Get the Call Forwarding config for the Person

        Returns:
            dict: The Call Forwarding config for the Person instance
        """
        log.info(f"Getting Call Forwarding config for {self.email}")
        self.call_forwarding = self.__get_webex_data(f"v1/people/{self.id}/features/callForwarding")
        return self.call_forwarding

    def get_barge_in(self):
        """Get the Barge-In config for the Person

        Returns:
            dict: The Barge-In config for the Person instannce
        """
        log.info(f"Getting Barge-In config for {self.email}")
        self.barge_in = self.__get_webex_data(f"v1/people/{self.id}/features/bargeIn")
        return self.barge_in

    def push_barge_in(self, config: dict):
        """ Push the Barge-In config to Webex

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Barge-In config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/bargeIn", payload=config)
        if success:
            return True
        else:
            log.warning(f"The Barge-In config push failed")
            return False

    def get_vm_config(self):
        """Fetch the Voicemail config for the Person from the Webex API"""
        log.info(f"Getting VM config for {self.email}")
        self.vm_config = self.__get_webex_data(f"v1/people/{self.id}/features/voicemail")
        return self.vm_config

    def push_vm_config(self, vm_config: dict = None):
        """ Push the Voicemail config back to Webex

        If the vm_config dict is provided, it will be sent as the payload to Webex. If it is omitted, the current
        Person.call_forwarding attributes will be sent.

        Args:
            vm_config (dict, optional: The vm_config dictionary to push to Webex

        Returns:
            dict: The new config that was sent back by Webex. False is returned if the API call fails.

        """
        log.info(f"Pushing VM Config for {self.email}")
        if vm_config is not None:
            payload = vm_config
        else:
            payload = self.vm_config
        success = self.__put_webex_data(f"v1/people/{self.id}/features/voicemail", payload)
        if success:
            self.get_vm_config()
            return self.vm_config
        else:
            return False

    def upload_busy_greeting(self, filename: str, activate: bool = True):
        """ Upload a WAV file to be used as the Person's Voicemail Busy Greeting

        This method does not check the format of the WAV file or provide any media conversion. The file should be in
        the correct format to be accepted by Webex. Files in the wrong format will fail and the method will return
        False.

        Args:
            filename (str): The filename (and path, if needed) of the WAV file to upload
            activate (bool, optional): Whether to activate this as the current Busy greeting. Defaults to True

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Uploading VB Busy Greeting for {self.email}")
        upload_as = os.path.basename(filename)
        content = open(filename, "rb")
        encoder = MultipartEncoder(fields={"file": (upload_as, content, 'audio/wav')})
        log.debug(f"File Encoder: {encoder}")
        r = requests.post(_url_base + f"v1/people/{self.id}/features/voicemail/actions/uploadBusyGreeting/invoke",
                          headers={"Content-Type": encoder.content_type, **self._headers},
                          data=encoder)
        content.close()
        if r.ok:
            if activate is True:
                vm_config = self.get_vm_config()
                vm_config['sendBusyCalls']['greeting'] = "CUSTOM"
                self.push_vm_config(vm_config)
            return True
        else:
            log.warning(f"The Greeting upload failed: {r.text}")
            return False

    def upload_no_answer_greeting(self, filename: str, activate: bool = True):
        """ Upload a WAV file to be used as the Person's Voicemail No Answer Greeting

        This method does not check the format of the WAV file or provide any media conversion. The file should be in
        the correct format to be accepted by Webex. Files in the wrong format will fail and the method will return
        False.

        Args:
            filename (str): The filename (and path, if needed) of the WAV file to upload
            activate (bool, optional): Whether to activate this as the current No Answer greeting. Defaults to True

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Uploading VB No Answer Greeting for {self.email}")
        upload_as = os.path.basename(filename)
        content = open(filename, "rb")
        encoder = MultipartEncoder(fields={"file": (upload_as, content, 'audio/wav')})
        log.debug(f"File Encoder: {encoder}")
        r = requests.post(_url_base + f"v1/people/{self.id}/features/voicemail/actions/uploadNoAnswerGreeting/invoke",
                          headers={"Content-Type": encoder.content_type, **self._headers},
                          data=encoder)
        content.close()
        if r.ok:
            if activate is True:
                vm_config = self.get_vm_config()
                vm_config['sendUnansweredCalls']['greeting'] = "CUSTOM"
                self.push_vm_config(vm_config)
            return True
        else:
            log.warning(f"The Greeting upload failed: {r.text}")
            return False

    def push_cf_config(self, cf_config: dict = None):
        """ Pushes the Call Forwarding config back to Webex

        If the cf_config dict is provided, it will be sent as the PUT payload. If it is omitted, the current
        Person.call_forwarding attributes will be sent

        Args:
            cf_config (dict, optional): The cf_config dictionary to push to Webex

        Returns:
            dict: The new config that was sent back by Webex

        """
        log.info(f"Pushing CF Config for {self.email}")
        if cf_config is not None:
            payload = cf_config
        else:
            payload = self.call_forwarding
        success = self.__put_webex_data(f"v1/people/{self.id}/features/callForwarding", payload)
        if success:
            self.get_call_forwarding()
            return self.call_forwarding
        else:
            return False

    def enable_vm_to_email(self, email: str = None, push=True):
        """
        Change the Voicemail config to enable sending a copy of VMs to specified email address. If the email param
        is not present, it will use the Person's email address as the default.

        Args:
            email (optional): The email address to send VMs to.
            push (optional): Whether to immediately push the change to Webex. Defaults to True.

        Returns:
            dict: The `Person.vm_config` attribute

        """
        if not self.vm_config:
            self.get_vm_config()
        if email is None:
            email = self.email
        self.vm_config['emailCopyOfMessage']['enabled'] = True
        self.vm_config['emailCopyOfMessage']['emailId'] = email
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def disable_vm_to_email(self, push=True):
        """ Change the Voicemail config to disable sending a copy of VMs to specified email address.

        Args:
            push (bool, optional): Whether to immediately push the change to Webex. Defaults to True.

        Returns:
            dict: The `Person.vm_config` attribute

        """
        log.info(f"Disabling VM-to-email for {self.email}")
        if not self.vm_config:
            self.get_vm_config()
        self.vm_config['emailCopyOfMessage']['enabled'] = False
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def enable_vm_notification(self, email: str = None, push=True):
        """
        Change the Voicemail config to enable voicemail notification to specified email address. If the email param
        is not present, it will use the Person's email address as the default.

        Args:
            email (optional): The email address to send VMs to.
            push (optional): Whether to immediately push the change to Webex. Defaults to True.

        Returns:
            dict: The `Person.vm_config` attribute
        """
        if not self.vm_config:
            self.get_vm_config()
        if email is None:
            email = self.email
        self.vm_config['notifications']['enabled'] = True
        self.vm_config['notifications']['destination'] = email
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def disable_vm_notification(self, email: str = None, push=True):
        """
        Change the Voicemail config to disable voicemail notification to specified email address. If the email param
        is not present, it will use the Person's email address as the default.

        Args:
            email (optional): The email address to send VMs to.
            push (optional): Whether to immediately push the change to Webex. Defaults to True.

        Returns:
            dict: The `Person.vm_config` attribute
        """
        if not self.vm_config:
            self.get_vm_config()
        if email is None:
            email = self.email
        self.vm_config['notifications']['enabled'] = False
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def set_voicemail_rings(self, rings: int, push=True):
        """ Set the number of rings before an Unanswered call is sent to Voicemail

        Args:
            rings (int): The number of rings
            push (bool, optional): Whether to immediately push the change to Webex. Defaults to True.

        Returns:
            dict: The `Person.vm_config` attribute

        """
        if not self.vm_config:
            self.get_vm_config()
        self.vm_config['sendUnansweredCalls']['numberOfRings'] = rings
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def get_intercept(self):
        """Gets the Intercept config for the Person

        Returns:
            dict: The Intercept config for the Person instance

        """
        log.info("get_intercept() started")
        self.intercept = self.__get_webex_data(f"v1/people/{self.id}/features/intercept")
        return self.intercept

    def push_intercept(self, config: dict):
        """ Push the Intercept config to Webex

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Intercept config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/intercept", payload=config)
        if success:
            return True
        else:
            log.warning("The Intercept config push failed")
            return False

    def get_call_recording(self):
        """The Call Recording config for the Person

        Returns:
            dict: The Call Recording config for the Person instance

        """
        log.info(f"Getting Call Recording config for {self.email}")
        self.call_recording = self.__get_webex_data(f"v1/people/{self.id}/features/callRecording")
        return self.call_recording

    def push_call_recording(self, config: dict):
        """ Push the Call Recording config to Webex

        Args:
            config (dict): The Call Recording config as defined by the Webex API specification

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Call Recording config for {self.email}")
        # The payload from Webex has the Dubber Service Provider info, which isn't supported by the PUT
        # We have to delete those keys if they exist before sending it
        clean_config = config.copy()
        clean_config.pop("serviceProvider", None)
        clean_config.pop("externalGroup", None)
        clean_config.pop("externalIdentifier", None)
        success = self.__put_webex_data(f"v1/people/{self.id}/features/callRecording", payload=clean_config)
        if success:
            return True
        else:
            log.warning("The Call Recording config push failed")
            return False

    def get_monitoring(self):
        """ Get the Monitoring config for the Person

        Returns:
            dict: The Monitoring config for the Person instance

        """
        log.debug(f"Getting Monitoring config for {self.email}")
        self.monitoring = self.__get_webex_data(f"v1/people/{self.id}/features/monitoring")
        return self.monitoring

    def push_monitoring(self, config: dict):
        """ Push the Monitoring config to Webex

        Args:
            config (dict): The Monitoring config as defined by the Webex API specification.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Monitoring config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/monitoring", payload=config)
        if success:
            return True
        else:
            log.warning("The Monitoring config push failed")
            return False

    def get_hoteling(self) -> dict:
        """ Get the Hoteling config for the Person

        Returns:
            dict: The Hoteling config for the Person instance

        """
        log.info(f"Getting Hoteling config for {self.email}")
        self.hoteling = self.__get_webex_data(f"v1/people/{self.id}/features/hoteling")
        return self.hoteling

    def push_hoteling(self, config: dict) -> bool:
        """ Push the Hoteling config to Webex

        Args:
            config (dict): The Hoteling config as defined by the Webex API specification

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Hoteling config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/hoteling", payload=config)
        if success:
            self.get_hoteling()
            return True
        else:
            log.warning("The Hoteling config push failed")
            return False

    def get_outgoing_permission(self):
        """ Get the Outgoing Calling Permission for the Person """
        log.info(f"Getting Outbound Calling Permission config for {self.email}")
        self._outgoing_permission = self.__get_webex_data(f"v1/people/{self.id}/features/outgoingPermission")
        return self._outgoing_permission

    def push_outgoing_permission(self, config: dict) -> bool:
        """ Sets the Outgoing Call Permission using the provided dict

        Args:
            config (dict): The Outgoing Call Permission config as defined by the Webex API specification

        Returns:
            bool: True on success, False otherwise.

        """
        log.info(f"Pushing Outgoing Calling Permission config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/outgoingPermission", payload=config)
        if success:
            self.get_outgoing_permission()
            return True
        else:
            log.warning("The Outgoing Permission push failed")
            return False

    def get_caller_id(self) -> dict:
        """ Get the Caller ID config for the Person

        Returns:
            dict: The Called ID config for the Person instance

        """
        log.info(f"Getting Caller ID config for {self.email}")
        self.caller_id = self.__get_webex_data(f"v1/people/{self.id}/features/callerId")
        return self.caller_id

    def push_caller_id(self, config: dict) -> bool:
        """ Push the Caller ID config to Webex

        This method differs from :meth:`Person.set_caller_id()`. It sends the config dict directly.
        :meth:`Person.set_caller_id()` builds the config dict itself so that you don't have to know all of the
        intricacies of the API specification. In most cases, that method is preferable.

        Args:
            config (dict): The Caller ID config as defined by the Webex API specification

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Caller Id config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/callerId", payload=config)
        if success:
            self.get_caller_id()
            return True
        else:
            log.warning("The Caller ID config push failed")
            return False

    def set_caller_id(self, name: str, number: str):
        """ Change the Caller ID for a Person

        Args:
            name (str): The name to set as the Caller ID Name. Also accepts keywords: ``direct`` sets the name to the
                user's name in Webex. ``location`` sets the name to the name of the Location.
            number (str): The number to set as the Caller ID.  Also accepts keywords: ``direct`` sets the number to the
                user's DID in Webex. ``location`` sets the name to the main number of the Location.

        Returns:
            bool: True on success

        Raises:
            wxcadm.exceptions.APIError: Raised when there is a problem with the API call

        """
        log.info(f"Settting Caller ID for {self.email}")
        log.debug(f"\tNew Name: {name}\tNew Number: {number}")
        payload = {}
        # Handle the possible number values
        if number.lower() == "direct":
            payload['selected'] = "DIRECT_LINE"
        elif number.lower() == "location":
            payload['selected'] = "LOCATION_NUMBER"
        else:
            payload['selected'] = "CUSTOM"
            payload['customNumber'] = number
        # Then deal with possible name values
        if name.lower() == "direct":
            payload['externalCallerIdNamePolicy'] = "DIRECT_LINE"
        elif name.lower() == "location":
            payload['externalCallerIdNamePolicy'] = "LOCATION"
        else:
            payload['externalCallerIdNamePolicy'] = "OTHER"
            payload['customExternalCallerIdName'] = name

        success = self.push_caller_id(config=payload)
        if success:
            return True
        else:
            return False

    def get_dnd(self) -> dict:
        """ Get the Do Not Disturb (DND) config for the Person

        Returns:
            dict: The DND config for the Person instance

        """
        log.info(f"Getting DND config for {self.email}")
        self.dnd = self.__get_webex_data(f"v1/people/{self.id}/features/doNotDisturb")
        return self.dnd

    def push_dnd(self, config: dict) -> bool:
        """ Push the Do Not Disturb (DND) config to Webex

        Args:
            config (dict): The DND confirguration to push

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing DND config for {self.email}")
        log.debug(f"\tConfig: {config}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/doNotDisturb", payload=config)
        if success:
            return True
        else:
            log.warning("The DND config push failed")
            return False

    def get_calling_behavior(self) -> dict:
        """ Get the Calling Behavior config for the Person

        Returns:
            dict: The Calling Behavior config for the Person instance

        """
        log.info(f"Getting Calling Behavior for {self.email}")
        self.calling_behavior = self.__get_webex_data(f"v1/people/{self.id}/features/callingBehavior")
        return self.calling_behavior

    def push_calling_behavior(self, config: dict) -> bool:
        """ Push the Calling Behavior config to Webex

        Args:
            config (dict): The Calling Behavior config

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Calling Behavior for {self.email}")
        log.debug(f"\tConfig: {config}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/callingBehavior", payload=config)
        if success:
            return True
        else:
            log.warning("The Calling Behavior config push failed")
            return False

    def get_applications_settings(self) -> dict:
        """ Get the Application Services settings for the Person

        Returns:
            dict: The Application Services settings for the Person instance

        """
        log.info(f"Getting Applications Settings for {self.email}")
        self.applications_settings = self.__get_webex_data(f"v1/people/{self.id}/features/applications")
        return self.applications_settings

    def push_applications_settings(self, config: dict) -> bool:
        """ Push the Applications Services settings to Webex

        Args:
            config (dict): The Applications Services Settings config

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Pushing Applications Settings for {self.email}")
        log.debug(f"\tConfig: {config}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/applications", payload=config)
        if success:
            return True
        else:
            log.warning("The Applications Settings config push failed")
            return False

    def license_details(self):
        """Get the full details for all of the licenses assigned to the Person

        Returns:
            list[dict]: List of the license dictionaries

        """
        log.info(f"Getting license details for {self.email}")
        license_list = []
        for license in self.licenses:
            for org_lic in self._parent.licenses:
                if license == org_lic['id']:
                    license_list.append(org_lic)
        return license_list

    def refresh_person(self, raw: bool = False):
        """
        Pull a fresh copy of the Person details from the Webex API and update the instance. Useful when changes
        are made outside of the script or changes have been pushed and need to get updated info.

        Args:
            raw (bool, optional): Return the "raw" config from the as a dict. Useful when making changes to
                the user, because you have to send all of the values over again.

        Returns:
            bool: True if successful, False if not

        """
        response = self.__get_webex_data(f"v1/people/{self.id}")
        if response:
            self.__process_api_data(response)
            if raw:
                return response
            else:
                return True
        else:
            return False

    def update_person(self,
                      email=None,
                      numbers=None,
                      extension=None,
                      location=None,
                      display_name=None,
                      first_name=None,
                      last_name=None,
                      roles=None,
                      licenses=None):
        """Update the Person in Webex.

        Pass only the arguments that you want to change. Other attributes will be populated
        with the existing values from the instance. *Note:* This allows changes directly to the instance attrs to
        be pushed to Webex. For example, changing Person.extension and then calling `update_person()` with no
        arguments will still push the extension change. This allows for a lot of flexibility if a method does not
        exist to change the desired value. It is also the method other methods use to push their changes to Webex.

        Args:
            email (str): The email address of the Person
            numbers (list): The list of number dicts ("type" and "value" keys)
            extension (str): The user's extension
            location (str): The Location ID for the user. Note that this can't actually be changed yet.
            display_name (str): The Display Name for the Person
            first_name (str): The Person's first name
            last_name (str): The Person's last name
            roles (list): List of Role IDs
            licenses (list): List of License IDs

        Returns:
            bool: True if successful. False if not.

        """
        # Build the payload using the arguments and the instance attrs
        payload = {}
        if email is None:
            email = self.email
        payload['emails'] = [email]
        if numbers is None:
            numbers = self.numbers
        payload['phoneNumbers'] = numbers
        if extension is None:
            if self.extension:
                extension = self.extension
        payload['extension'] = extension
        if location is None:
            location = self.location
        payload['location'] = location
        if display_name is None:
            display_name = self.display_name
        payload['displayName'] = display_name
        if first_name is None:
            first_name = self.first_name
        payload['firstName'] = first_name
        if last_name is None:
            last_name = self.last_name
        payload['lastName'] = last_name
        if roles is None:
            roles = self.roles
        payload['roles'] = roles
        if licenses is None:
            licenses = self.licenses
        payload['licenses'] = licenses

        params = {"callingData": "true"}
        success = self.__put_webex_data(f"v1/people/{self.id}", payload, params)
        if success:
            self.refresh_person()
            return True
        else:
            return False

    def set_calling_only(self) -> bool:
        """
        Removes the Messaging and Meetings licenses, leaving only the Calling capability.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Setting {self.email} to Calling-Only")
        # First, iterate the existing licenses and remove the ones we don't want
        # Build a list that contains the values to match on to remove
        remove_matches = ["messaging",
                          "meeting",
                          "free"]
        new_licenses = []
        for license in self.licenses:
            log.debug(f"Checking license: {license}")
            lic_name = self._parent.get_license_name(license)
            log.debug(f"License Name: {lic_name}")
            if any(match in lic_name.lower() for match in remove_matches):
                if "screen share" in lic_name.lower():
                    log.debug(f"{lic_name} matches but is needed")
                    new_licenses.append(license)
                else:
                    log.debug(f"License should be removed")
                    continue
            else:
                log.debug(f"Keeping license")
                new_licenses.append(license)

        success = self.update_person(licenses=new_licenses)
        if success:
            return True
        else:
            log.warning("The Set Calling Only command failed")
            return False


    def change_phone_number(self, new_number: str, new_extension: str = None):
        """ Change a person's phone number and extension

        Args:
            new_number (str): The new phone number for the person
            new_extension (str, optional): The new extension, if changing. Omit to leave the same value.

        Returns:
            bool: True on success, False otherwise

        """
        if not new_extension:
            if self.extension:
                extension = self.extension
            else:
                extension = None
        else:
            extension = new_extension
        log.info(f"Changing phone number for {self.email} to {new_number} with extension: {str(new_extension)}")

        # Call the update_person() method
        success = self.update_person(numbers=[{"type": "work", "value": new_number}], extension=extension)
        if success:
            self.refresh_person()
            return True
        else:
            log.warning("Updating the phone number config failed")
            return False


    def disable_call_recording(self):
        """ Disables Call Recording for the Person

        This method will return True even if the Person did not have Call Recording enabled prior to calling
        the method.

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Disabling Call Recording for {self.email}")
        recording_config = self.get_call_recording()
        recording_config['enabled'] = False
        self.call_recording = recording_config

    def enable_call_recording(self, type: str,
                              record_vm: bool = False,
                              announcement_enabled: bool = False,
                              reminder_tone: bool = False,
                              reminder_interval: int = 30):

        type_map = {"always": "Always",
                    "never": "Never",
                    "always_with_pause": "Always with Pause/Resume",
                    "on_demand": "On Demand with User Initiated Start"}
        if type not in type_map.keys():
            raise ValueError("'type' must be 'always', 'never', 'always_with_pause' or 'on_demand'.")
        payload = {"enabled": True,
                   "record": type_map[type],
                   "recordVoicemailEnabled": record_vm,
                   "startStopAnnouncementEnabled": announcement_enabled,
                   "notification": {
                       "type": "beep",
                       "enabled": reminder_tone,
                       "repeat": {
                           "enabled": reminder_tone,
                           "interval": reminder_interval
                           }
                       }
                  }
        success = self.push_call_recording(payload)
        if success:
            return True
        else:
            return False

    def get_executive_assistant(self):
        """ Get the Executive Assistant config for the Person

        Returns:
            dict: The Executive Assistant config for the Person instance

        """
        log.info(f"Getting Executive Assistant config for {self.email}")
        self.executive_assistant = self.__get_webex_data(f"v1/people/{self.id}/features/executiveAssistant")
        return self.executive_assistant

    def push_executive_assistant(self, config: dict) -> bool:
        """ Push the Exectuve Assistant config to Webex

        Args:
            config (dict): The Executive Assistant Config

        Returns:
             bool: True on success, False otherwise

        """
        log.info(f"Pushing Executive Assistant config for {self.email}")
        log.debug(f"\tConfig: {config}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/executiveAssistant", payload=config)
        if success:
            return True
        else:
            log.warning("The Executive Assistant config push failed")
            return False

    @property
    def wxc_numbers(self):
        """ All the phone numbers for the user from the Webex Calling platform.

        Unlike the :py:meth:`Person.numbers` property, which only reads the data from Webex Common Identity, this
        property pulls the data from the Webex Calling platform, so it includes the Primary number as well as any
        Alias numbers and doesn't include any Active Directory data.

        Returns:
            dict: Dict of numbers properties as defined at https://developer.webex.com/docs/api/v1/webex-calling-person-settings/get-a-list-of-phone-numbers-for-a-person

        """
        return webex_api_call('get', f'/v1/people/{self.id}/features/numbers')

class Me(Person):
    """ The class representing the token owner. Some methods are only available at an owner scope. """
    def __init__(self, user_id, parent: Org = None, config: dict = None):
        super().__init__(user_id, parent, config)

    def get_voice_messages(self, unread: bool = False):
        """ Get all the Voice Messages for the Me instance

        Args:
            unread (bool, optional): Whether to only return Unread messages. Default is False

        Returns:
            list[VoiceMessage]: A list of all of the :py:class:`VoiceMessage` instances

        """
        messages = []
        # Something funky about this API call needing more headers
        data = webex_api_call("get", "v1/telephony/voiceMessages")
        for item in data:
            if item['read'] is True and unread is True:
                continue
            else:
                m = VoiceMessage(**item)
            messages.append(m)
        return messages

    @property
    def voicemail_summary(self) -> Optional[dict]:
        """ A summary of the number of read and unread Voice Messages

        Returns:
            dict: A dict of the Voice Message summary in the format::

                {
                    'newMessages': int,
                    'oldMessages': int,
                    'newUrgentMessages': int,
                    'oldUrgentMessages': int
                }

        """
        data: dict = webex_api_call('get', 'v1/telephony/voiceMessages/summary')
        if data:
            return data
        else:
            return None


@dataclass
class VoiceMessage:
    id: str
    """ The unique identifier for the Voice Message """
    duration: int
    """ The duration (in seconds) of the Voice Message. Not present for a fax message."""
    callingParty: dict
    """ The Calling Party's details """
    read: bool
    """ True is the Voice Message has been read/heard """
    created: str
    """ The date and time the Voice Message was created """
    urgent: bool = False
    """ True if the Voice Message has been marked Urgent """
    confidential: bool = False
    """ True if the Voice Message has been marked Confidential """
    faxPageCount: Optional[int] = None
    """ Number of pages in the fax. On"""

    def mark_read(self) -> bool:
        """ Mark the message as read within Webex

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Marking Voice Message as read: {self.id}")
        payload = {"messageId": self.id}
        success = webex_api_call("post", "v1/telephony/voiceMessages/markAsRead", payload=payload)
        if success:
            return True
        else:
            log.warning("Something went wrong marking the message read.")
            return False

    def mark_unread(self) -> bool:
        """ Mark the message as unread within Webex

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Marking Voice Message as unread: {self.id}")
        payload = {"messageId": self.id}
        success = webex_api_call("post", "v1/telephony/voiceMessages/markAsUnread", payload=payload)
        if success:
            return True
        else:
            log.warning("Something went wrong marking the message unread.")
            return False

    def delete(self) -> bool:
        """ Delete the Voice Message

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Deleting Voice Message with ID {self.id}")
        success = webex_api_call("delete", f"v1/telephony/voiceMessages/{self.id}")
        if success:
            return True
        else:
            log.warning("The Voice Message delete failed")
            return False


class UserGroups(UserList):
    """ UserGroups is the parent class for :py:class:`UserGroup`, providing methods for the list of Groups """
    def __init__(self, parent: Org):
        log.info("Initializing UserGroups instance")
        super().__init__()
        self.parent = parent
        self.data = []
        response = webex_api_call("get", "v1/groups")
        groups = response['groups']
        log.debug(f"Webex returned {len(groups)} Groups")
        for group in groups:
            usergroup = UserGroup(parent=self.parent, **group)
            self.data.append(usergroup)

    def create_group(self, name: str,
                     description: str = '',
                     members: Optional[list] = None) -> bool:
        """ Create a new UserGroup

        Args:
            name (str): The name of the Group
            description (str, optional): An optional description of the Group
            members (list[Person], optional): An optional list of :py:class:`Person` instances to add to the Group

        Returns:
            bool: True on success, False otherwise

        """
        payload = {'displayName': name, 'orgId': self.parent.id, 'description': description}
        if members is not None:
            payload['members'] = []
            for member in members:
                payload['members'].append({'id': member.id})
        response = webex_api_call('post', 'v1/groups', payload=payload)
        if response:
            log.info(f"New UserGroup {name} created")
            new_group = UserGroup(parent=self.parent, **response)
            self.data.append(new_group)
            return True
        else:
            log.info("Failed to create new UserGroup")
            return False

    def find_person_assignment(self, person: Person):
        for group in self.data:
            for member in group.members:
                if member.id == person.id:
                    return group
        return None


@dataclass()
class UserGroup:
    """ The UserGroup class holds all the User Groups available within the Org"""
    parent: Org = field(repr=False)
    """ The Org instance that owns the Group """
    id: str
    """ The unique ID of the Group """
    displayName: str
    """ The name of the Group """
    orgId: str = field(repr=False)
    """ The Org ID to which the Group belongs """
    created: str = field(repr=False)
    """ The timestamp indicating when the Group was created """
    lastModified: str = field(repr=False)
    """ The timestamp indicating the last time the Group was modified """
    # Changed 3.0.0 - This field no longer comes back in the API response. Not sure if it will be re-added
    usage: str = field(init=True, repr=True, default='Unknown')
    """ The Group usage type. This is a value that was provided by Webex but has been removed """
    memberSize: int = field(init=True, repr=False, default=0)
    """ The number of members in the group only if returned by Webex """
    members: list = field(init=True, repr=False, default=None)
    """ A list of all of the :py:class:`Person` instances within the Group """
    description: str = field(repr=False, default='')
    """ The long description of the Group """

    def __post_init__(self):
        self._get_members()

    def _get_members(self):
        response = webex_api_call("get", f"/v1/groups/{self.id}/members")
        items = response['members']
        # If there are more than 500 members, we need to go get the rest, and the Groups API handles this
        # differently than all the other APIs. This is probably going to break things if they ever fix the Groups
        # API, but we'll handle that when it happens

        people = []
        for item in items:
            person = self.parent.get_person_by_id(item['id'])
            if person is None:
                people.append(item['id'])
            else:
                people.append(person)
        self.members = people

    def delete(self) -> bool:
        """ Delete the Group

        Returns:
            bool: True on success, False otherwise

        """
        response = webex_api_call('delete', f'v1/groups/{self.id}')
        if response:
            log.info(f'Successfully deleted UserGroup {self.displayName}')
            return True
        else:
            log.warning(f'Failed to delete UserGroup {self.displayName}')
            return False

    def add_member(self, person: Person) -> bool:
        """ Add a Person to the Group

        Args:
            person (Person): The :py:class:`Person` instance to add

        Returns:

        """
        payload = {"members" : [{"id": person.id, "operation": "add"}]}
        response = webex_api_call("patch", f"v1/groups/{self.id}", payload=payload)
        if response:
            return True
        else:
            return False

    def delete_member(self, person: Person) -> bool:
        """ Delete the specified Person from the Group

        Args:
            person (Person): The :py:class:`Person` instance to delete

        Returns:
            bool: True on success, False otherwise

        """
        payload = {"members": [{'id': person.id, 'operation': 'delete'}]}
        response = webex_api_call('patch', f'v1/groups/{self.id}', payload=payload)
        if response:
            return True
        else:
            return False

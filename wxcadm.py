import json.decoder

import requests
import logging
import base64

# TODO: Eventually I would like to use dataclasses, but it will be a heavy lift

# TODO: There is a package-wide problem where we have Webex-native data and instance attributes that we write
#       to make the instances easier to work with. I have kept the native data because it is easier to push back
#       to Webex and safer in case the API changes. Ideally, we should store all attributes in ways that a user
#       would want them and pack them back into JSON as needed. In the meantime, like in the CallQueues object
#       I end up with the same values in multiple attributes, which is a bad idea.

# Set up logging
logging.basicConfig(level=logging.INFO,
                    filename="wxcadm.log",
                    format='%(asctime)s %(module)s:%(levelname)s:%(message)s')
# Some functions available to all classes and instances (optionally)
# TODO Lots of stuff probably could be moved here since there are common functions in most classes
_url_base = "https://webexapis.com/"


class OrgError(Exception):
    def __init__(self, message):
        super().__init__(message)


class APIError(Exception):
    def __init__(self, message):
        """The base class for any exceptions dealing with the API"""
        super().__init__(message)


class TokenError(APIError):
    def __init__(self, message):
        """Exceptions dealing with the Access Token itself"""
        super().__init__(message)


class PutError(APIError):
    def __init__(self, message):
        """Exception class for problems putting values back into Webex"""
        super().__init__(message)


class Webex:
    # TODO List
    #    Add token refresh, just for completeness

    def __init__(self, access_token, create_org=True, get_people=True, get_locations=True, get_xsi=False):
        logging.info("Webex instance initialized")
        # The access token is the only thing that we need to get started
        self._access_token: str = access_token
        # The Authorization header is going to be used by every API call in the package.
        # Might want to make it something global so we don't have to inherit it across all of the children
        self._headers: dict = {"Authorization": "Bearer " + access_token}
        logging.debug(f"Setting Org._headers to {self._headers}")

        # Instance attrs
        self.orgs: list[Org] = []
        '''A list of the Org instances that this Webex instance can manage'''
        # Get the orgs that this token can manage
        logging.debug(f"Making API call to v1/organizations")
        r = requests.get(_url_base + "v1/organizations", headers=self._headers)
        # Handle an invalid access token
        if r.status_code != 200:
            raise TokenError("The Access Token was not accepted by Webex")
        response = r.json()
        # Handle when no Orgs are returned. This is pretty rare
        if len(response['items']) == 0:
            raise OrgError
        # If a token can manage a lot of orgs, you might not want to create them all, because
        # it can take some time to do all of the API calls and get the data back
        if not create_org:
            logging.info("Org initialization not requested. Storing orgs.")
            self.orgs = response['items']
            return
        else:
            logging.info("Org initialization requested. Collecting orgs")
            for org in response['items']:
                # This builds an Org instance for every Org, so be careful
                # if the user manages multiple orgs
                logging.debug(f"Processing org: {org['displayName']}")
                org = Org(org['displayName'], org['id'],
                          people=get_people, locations=get_locations, xsi=get_xsi, parent=self)
                self.orgs.append(org)
            # Most users have only one org, so to make that easier for them to work with
            # we are also going to put the orgs[0] instance in the org attr
            # That way both .org and .orgs[0] are the same
            if len(self.orgs) == 1:
                logging.debug(f"Only one org found. Storing as Webex.org")
                self.org = self.orgs[0]

    @property
    def headers(self):
        return self._headers


class Org:
    def __init__(self, name: str, id: str, people: bool = True,
                 locations: bool = True, xsi: bool = False, parent: Webex = None):
        """
        Initialize an Org instance

        Args:
            name (str): The Organization name
            id (str): The Webex ID of the Organization
            people (bool, optional): Whether to automatically get all people for the Org
            locations (bool, optional): Whether to automatically get all of the locations for the Org
            xsi (bool, optional): Whether to automatically get the XSI Endpoints for the Org
            parent (Webex, optional): The parent Webex instance that owns this Org. Usually `_parent=self`

        Returns:
            Org: This instance of the Org class
        """

        # Instance attrs
        self.call_queues: list[CallQueue] = []
        """The Call Queues for this Org"""
        self.hunt_groups: list[HuntGroup] = []
        """The Hunt Groups for this Org"""
        self.pickup_groups: list[PickupGroup] = []
        'A list of the PickupGroup instances for this Org'
        self.locations: list[Location] = []
        'A list of the Location instances for this Org'
        self.name: str = name
        'The name of the Organization'
        self.id:  str = id
        '''The Webex ID of the Organization'''
        self.xsi: dict = {}
        self._params: dict = {"orgId": self.id}
        self.licenses: list[dict] = []
        '''A list of all of the licenses for the Organization as a dictionary of names and IDs'''
        self.people: list[Person] = []
        '''A list of all of the Person stances for the Organization'''

        # Set the Authorization header based on how the instance was built
        self._headers = parent.headers
        self.licenses = self.__get_licenses()

        # Get all of the people if we aren't told not to
        if people:
            self.get_people()
        # Get all of the locations if we aren't asked not to
        if locations:
            self.get_locations()
        if xsi:
            self.get_xsi_endpoints()

    @property
    def __str__(self):
        return f"{self.name},{self.id}"

    def __get_licenses(self):
        """
        Gets all of the licenses for the Organization

        :return:
            list: List of dictionaries containing the license name and ID
        """
        logging.info("__get_licenses() started for org")
        license_list = []
        r = requests.get(_url_base + "v1/licenses", headers=self._headers, params=self._params)
        response = r.json()
        for item in response['items']:
            if "Webex Calling" in item['name']:
                wxc_license = True
            else:
                wxc_license = False
            lic = {"name": item['name'], "id": item['id'], "wxc_license": wxc_license}
            license_list.append(lic)
        return license_list

    def __get_wxc_licenses(self):
        """
        Get only the Webex Calling licenses from the Org.licenses attribute

        Returns:
            list[str]:
        """
        logging.info("__get_wxc_licenses started")
        license_list = []
        for license in self.licenses:
            if license['wxc_license']:
                license_list.append(license['id'])
        return license_list

    def get_person_by_email(self, email):
        """
        Get the Person instance from an email address
        Args:
            email (str): The email of the Person to return
        Returns:
            Person: Person instance object. None in returned when no Person is found
        """
        logging.info("get_person_by_email() started")
        for person in self.people:
            if person.email == email:
                return person
        return None

    def get_xsi_endpoints(self):
        """
        Get the XSI endpoints for the Organization. Also stores them in the Org.xsi attribute.
        Returns:
            dict: Org.xsi attribute dictionary with each endpoint as an entry
        """
        params = {"callingData": "true", **self._params}
        r = requests.get(_url_base + "v1/organizations/" + self.id, headers=self._headers, params=params)
        response = r.json()
        self.xsi['actions_endpoint'] = response['xsiActionsEndpoint']
        self.xsi['events_endpoint'] = response['xsiEventsEndpoint']
        self.xsi['events_channel_endpoint'] = response['xsiEventsChannelEndpoint']

        return self.xsi

    def get_locations(self):
        """
        Get the Locations for the Organization. Also stores them in the Org.locations attribute.
        Returns:
            list[Location]: List of Location instance objects. See the Locations class for attributes.
        """
        logging.info("get_locations() started")
        r = requests.get(_url_base + "v1/locations", headers=self._headers, params=self._params)
        response = r.json()
        # I am aware that this doesn't support pagination, so there will be a limit on number of Locations returned
        for location in response['items']:
            this_location = Location(location['id'], location['name'], address=location['address'])
            self.locations.append(this_location)

        return self.locations

    def get_pickup_groups(self):
        """
        Get all of the Call Pickup Groups for an Organization. Also stores them in the Org.pickup_groups attribute.
        Returns:
            list[PickupGroup]: List of Call Pickup Groups as a list of dictionaries.
                See the PickupGroup class for attributes.
        """
        logging.info("get_pickup_groups() started")
        # First we need to know if we already have locations, because they are needed
        # for the pickup groups call
        if not self.locations:
            self.get_locations()
        # Loop through all of the locations and get their pickup groups
        # We will create a new instance of the PickupGroup class when we find one
        for location in self.locations:
            r = requests.get(_url_base + "v1/telephony/config/locations/" + location.id + "/callPickups",
                             headers=self._headers)
            response = r.json()
            for item in response['callPickups']:
                pg = PickupGroup(self, location.id, item['id'], item['name'])
                self.pickup_groups.append(pg)
        return self.pickup_groups

    def get_call_queues(self):
        """
        Get the Call Queues for an Organization. Also stores them in the Org.call_queues attribute.
        Returns:
            list[CallQueue]: List of CallQueue instances for the Organization
        """
        logging.info("get_call_queues() started")
        if not self.locations:
            self.get_locations()
        r = requests.get(_url_base + "v1/telephony/config/queues", headers=self._headers, params=self._params)
        response = r.json()
        for queue in response['queues']:
            id = queue.get("id")
            name = queue.get("name", None)
            location_id = queue.get("locationId")
            phone_number = queue.get("phoneNumber", None)
            extension = queue.get("extension", None)
            enabled = queue.get("enabled")

            queue = CallQueue(self, id, name, location_id, phone_number, extension, enabled, get_config=True)
            self.call_queues.append(queue)
        return self.call_queues

    def get_hunt_groups(self):
        """
        Get the Hunt Groups for an Organization. Also stores them in the Org.hunt_groups attribute.
        Returns:
            list[HuntGroup]: List of HuntGroup instances for the Organization
        """
        logging.info("get_hunt_groups() started")
        if not self.locations:
            self.get_locations()
        r = requests.get(_url_base + "v1/telephony/config/huntGroups", headers=self._headers, params=self._params)
        response = r.json()
        for hg in response['huntGroups']:
            hunt_group = HuntGroup(self, hg['id'], hg['name'], hg['locationId'], hg['enabled'],
                                   hg.get("phoneNumber", ""), hg.get("extension", ""))
            self.hunt_groups.append(hunt_group)
        return self.hunt_groups

    def get_people(self):
        """
        Get all of the people within the Organization. Also creates a Person instance and stores it in the
            Org.people attributes
        Returns:
            list[Person]: List of Person instances
        """
        logging.info("get_people() started")
        params = {"max": "1000", **self._params}
        r = requests.get(_url_base + "v1/people", headers=self._headers, params=params)
        people_list = r.json()

        if "next" in r.links:
            keep_going = True
            next_url = r.links['next']['url']
            while keep_going:
                r = requests.get(next_url, headers=self._headers)
                new_people = r.json()
                if "items" not in new_people:
                    continue
                people_list['items'].extend(new_people['items'])
                if "next" not in r.links:
                    keep_going = False
                else:
                    next_url = r.links['next']['url']

        wxc_licenses = self.__get_wxc_licenses()
        for person in people_list['items']:
            this_person = Person(person['id'], person['emails'][0], first_name=person['firstName'],
                                 last_name=person['lastName'], display_name=person['displayName'], parent=self)
            this_person.licenses = person['licenses']
            for license in person['licenses']:
                if license in wxc_licenses:
                    this_person.wxc = True
            self.people.append(this_person)
        return self.people

    def get_wxc_people(self):
        """
        Get all of the people within the Organization **who have Webex Calling**
        Returns:
            list[Person]: List of Person instances of people who have a Webex Calling license
        """
        if not self.people:
            self.get_people()
        wxc_people = []
        for person in self.people:
            if person.wxc:
                wxc_people.append(person)
        return wxc_people


class Location:
    def __init__(self, location_id, name, address=None):
        """
        Initialize a Location instance
        Args:
            location_id (str): The Webex ID of the Location
            name (str): The name of the Location
            address (dict): The address information for the Location
        Returns:
             Location (object): The Location instance
        """
        if address is None:
            address = {}
        self.id: str = location_id
        self.name: str = name
        self.address: dict = address

    @property
    def __str__(self):
        return f"{self.name},{self.id}"


class Person:
    # TODO List
    #    Add methods to get and return XSI identifiers

    def __init__(self, user_id,
                 user_email,
                 first_name=None,
                 last_name=None,
                 display_name=None,
                 licenses=None,
                 parent=None,
                 access_token=None,
                 url_base=None):
        # Default values for other attrs
        self.wxc: bool = False
        '''True if this is a Webex Calling User'''
        self.vm_config: dict = {}
        '''Dictionary of the VM config as returned by Webex API'''
        self.recording = None
        self.barge_in = None
        self.call_forwarding: dict = {}
        '''Dictionary of the Call Forwarding config as returned by Webex API'''
        self.caller_id = None
        self.intercept = None
        self.dnd = None
        self.calling_behavior = None
        self.xsi = None
        self._parent = parent

        # Set the Authorization header based on how the instance was built
        if licenses is None:
            licenses = []
        if parent is None:  # Instance wasn't created by another instance
            # TODO Need some code here to throw an error if there is no access_token and url_base
            self._headers = {"Authorization": "Bearer " + access_token}
            self._url_base = url_base
        else:  # Instance was created by a parent
            self._headers = parent._headers

        self._params = {"orgId": parent.id}
        self.id = user_id
        self.email = user_email
        self.first_name = first_name
        self.last_name = last_name
        self.display_name = display_name
        self.licenses = licenses

    def __str__(self):
        return f"{self.email},{self.display_name}"

    # The following is to simplify the API call. Eventually I may open this as a public method to
    # allow arbitrary API calls
    def __get_webex_data(self, endpoint, params=None):
        """

        :param endpoint: The endpoint of the API call (e.g. 'v1/locations')
        :param params: A dict of param values for the API call. Will be passed as URL params
        :return: Returns a dict of the JSON response from the API
        """
        if params is None:
            params = {}
        logging.info(f"__get_webex_data started for using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.get(_url_base + endpoint, headers=self._headers, params=my_params)
        response = r.json()
        return response

    def __push_webex_data(self, endpoint, payload, params=None):
        if params is None:
            params = {}
        logging.info(f"__push_webex_data started using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.put(_url_base + endpoint, headers=self._headers, params=my_params, json=payload)
        response_code = r.status_code
        if response_code == 200 or response_code == 204:
            return True
        else:
            raise PutError(r.text)

    def start_xsi(self):
        self.xsi = XSI(self)

    def get_full_config(self):
        if self.wxc:
            self.get_call_forwarding()
            self.get_vm_config()
            self.get_intercept()
            self.get_call_recording()
            self.get_caller_id()
            self.get_dnd()
            self.get_calling_behavior()
            self.get_barge_in()

    def get_call_forwarding(self):
        logging.info("get_call_forwarding() started")
        self.call_forwarding = self.__get_webex_data(f"v1/people/{self.id}/features/callForwarding")
        return self.call_forwarding

    def get_barge_in(self):
        logging.info("get_barge_in() started")
        self.barge_in = self.__get_webex_data(f"v1/people/{self.id}/features/bargeIn")
        return self.barge_in

    def get_vm_config(self):
        logging.info("get_vm_config() started")
        self.vm_config = self.__get_webex_data(f"v1/people/{self.id}/features/voicemail")
        return self.vm_config

    def push_vm_config(self):
        # In progress
        logging.info(f"Pushing VM Config for {self.email}")
        success = self.__push_webex_data(f"v1/people/{self.id}/features/voicemail", self.vm_config)
        self.get_vm_config()
        return self.vm_config

    def enable_vm_to_email(self, email=None, push=True):
        if not email:
            email = self.email
        self.vm_config['emailCopyOfMessage']['enabled'] = True
        self.vm_config['emailCopyOfMessage']['emailId'] = email
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def disable_vm_to_email(self, push=True):
        self.vm_config['emailCopyOfMessage']['enabled'] = False
        if push:
            return self.push_vm_config()
        else:
            return self.vm_config

    def get_intercept(self):
        logging.info("get_intercept() started")
        self.intercept = self.__get_webex_data(f"v1/people/{self.id}/features/intercept")
        return self.intercept

    def get_call_recording(self):
        logging.info("get_call_recording() started")
        self.recording = self.__get_webex_data(f"v1/people/{self.id}/features/callRecording")
        return self.recording

    def get_caller_id(self):
        logging.info("get_caller_id() started")
        self.caller_id = self.__get_webex_data(f"v1/people/{self.id}/features/callerId")
        return self.caller_id

    def get_dnd(self):
        logging.info("get_dnd() started")
        self.dnd = self.__get_webex_data(f"v1/people/{self.id}/features/doNotDisturb")
        return self.dnd

    def get_calling_behavior(self):
        logging.info("get_calling_behavior() started")
        self.calling_behavior = self.__get_webex_data(f"v1/people/{self.id}/features/callingBehavior")
        return self.calling_behavior


class PickupGroup:
    def __init__(self, parent, location, id, name, users=None):
        self._parent: object = parent
        self.location_id: str = location
        """The Webex ID of the Location associated with this Pickup Group"""
        self.id: str = id
        """The Webex ID of the Pickup Group"""
        self.name: str = name
        """The name of the Pickup Group"""
        self.users: list = []
        """All of the users (agents) assigned to this Pickup Group"""
        # If no agents were passed, we need to go get the configuration of the PickupGroup
        if users is None:
            r = requests.get(_url_base + f"v1/telephony/config/locations/{self.location_id}/callPickups/{self.id}",
                             headers=self._parent._headers
                             )
            response = r.json()
            # TODO It doesn't make sense to create a new Person instance for the below.
            #      Once we have an API and a class for Workspaces, it would make sense to tie
            #      the agents to the Person or Workspace instance
            # For now, we just write the values that we get back and the user can find the people with the
            # Person-specific methods
            for agent in response['agents']:
                self.users.append(agent)

    def get_config(self):
        """Gets the configuration of the Pickup Group from Webex
        Returns:
            dict: The configuration of the Pickup Group
        """
        config = {**self}
        return config


class CallQueue:
    def __init__(self, parent, id, name, location, phone_number, extension, enabled, get_config=True):
        self._parent: Org = parent
        """The parent org of this Call Queue"""
        self.id: str = id
        """The Webex ID of the Call Queue"""
        self.name: str = name
        """The name of the Call Queue"""
        self.location_id: str = location
        """The Webex ID of the Location associated with this Call Queue"""
        self.phone_number: str = phone_number
        """The DID of the Call Queue"""
        self.extension: str = extension
        """The extension of the Call Queue"""
        self.enabled: bool = enabled
        """True if the Call Queue is enabled. False if disabled"""
        self.call_forwarding: dict = {}
        """The Call Forwarding config for the Call Queue"""
        self.config: dict = {}
        """The configuration dictionary for the Call Queue"""

        if get_config:
            self.get_queue_config()
            self.get_queue_forwarding()

    def get_queue_config(self):
        """
        Get the configuration of this Call Queue instance
        Returns:
            CallQueue.config: The config dictionary of this Call Queue
        """
        r = requests.get(_url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id,
                         headers=self._parent._headers)
        response = r.json()
        self.config = response
        return self.config

    def get_queue_forwarding(self):
        """
        Get the Call Forwarding settings for this Call Queue instance

        Returns:
            CallQueue.call_forwarding: The Call Forwarding settings for the Person
        """
        # TODO: The rules within Call Forwarding are weird. The rules come back in this call, but they are
        #       different than the /selectiveRules response. It makes sense to aggregate them, but that probably
        #       requires the object->JSON mapping that we need to do for all classes
        r = requests.get(_url_base + "v1/telephony/config/locations/" + self.location_id +
                         "/queues/" + self.id + "/callForwarding",
                         headers=self._parent._headers)
        response = r.json()
        self.call_forwarding = response
        return self.call_forwarding

    def push(self):
        """
        Push the contents of the CallQueue.config back to Webex
        Returns:
            CallQueue.config: The updated config attribute pulled from Webex after pushing the change
        """
        # TODO: Right now this only pushes .config. It should also push .call_forwarding and .forwarding_rules
        logging.info(f"Pushing Call Queue config to Webex for {self.name}")
        url = _url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id
        print(url)
        r = requests.put(url,
                         headers=self._parent._headers, json=self.config)
        response = r.status_code
        self.get_queue_config()
        return self.config


class XSI:
    def __init__(self, _parent, get_profile=False):
        """
        The XSI class holds all of the relevant XSI data for a Person
        :param _parent: The Person instance that created the XSI
        :param get_profile: Boolean value to force the XSI to get the user profile when initialized
        """
        logging.info(f"Initializing XSI instance for {_parent.email}")
        # First we need to get the XSI User ID for the Webex person we are working with
        logging.info("Getting XSI identifiers")
        user_id_bytes = base64.b64decode(_parent.id + "===")
        user_id_decoded = user_id_bytes.decode("utf-8")
        user_id_bwks = user_id_decoded.split("/")[-1]
        self.id = user_id_bwks

        # Inherited attributes
        self.xsi_endpoints = _parent._parent.xsi

        # API attributes
        self._headers = {"Content-Type": "application/json",
                         "Accept": "application/json",
                         "X-BroadWorks-Protocol-Version": "25.0",
                         **_parent._headers}
        self._params = {"format": "json"}

        # Attribute definitions
        self.profile = {}
        self.registrations = None
        self.fac = None
        self.services = {}

        # Get the profile if we have been asked to
        if get_profile:
            self.get_profile()

    def get_profile(self):
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + "/v2.0/user/" + self.id + "/profile",
                         headers=self._headers, params=self._params)
        response = r.json()
        # The following is a mapping of the raw XSI format to the profile attribute
        self.profile['registrations_url'] = response['Profile']['registrations']['$']
        self.profile['schedule_url'] = response['Profile']['scheduleList']['$']
        self.profile['fac_url'] = response['Profile']['fac']['$']
        self.profile['country_code'] = response['Profile']['countryCode']['$']
        self.profile['user_id'] = response['Profile']['details']['userId']['$']
        self.profile['group_id'] = response['Profile']['details']['groupId']['$']
        self.profile['service_provider'] = response['Profile']['details']['serviceProvider']['$']
        # Not everyone has a number and/or extension, so we need to check to see if there are there
        if "number" in response['Profile']['details']:
            self.profile['number'] = response['Profile']['details']['number']['$']
        if "extension" in response['Profile']['details']:
            self.profile['extension'] = response['Profile']['details']['extension']['$']

        return self.profile

    def get_registrations(self):
        # If we don't have a registrations URL, because we don't have the profile, go get it
        if "registrations_url" not in self.profile:
            self.get_profile()
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + self.profile['registrations_url'],
                         headers=self._headers, params=self._params)
        response = r.json()
        self.registrations = response
        return self.registrations

    def get_fac(self):
        # If we don't have a FAC URL, go get it
        if "fac_url" not in self.profile:
            self.get_profile()
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + self.profile['fac_url'],
                         headers=self._headers, params=self._params)
        response = r.json()
        self.fac = response
        return self.fac

    def get_services(self):
        # TODO There are still some services that we should collect more data for. For example, BroadWorks
        #       Anywhere has Locations that aren't pulled without a separate call.

        r = requests.get(self.xsi_endpoints['actions_endpoint'] + "/v2.0/user/" + self.id + "/services",
                         headers=self._headers, params=self._params)
        response = r.json()
        self.services['list'] = response['Services']['service']
        # Now that we have all of the services, pulling the data is pretty easy since the URL
        # is present in the response. Loop through the services and collect the data
        # Some services have no config so there is no URI and we'll just populate them as True
        for service in self.services['list']:
            if "uri" in service:
                r = requests.get(self.xsi_endpoints['actions_endpoint'] + service['uri']['$'],
                                 headers=self._headers, params=self._params)
                # Getting well-formatted JSON doesn't always work. If we can decode the JSON, use it
                # If not, just store the raw text. At some point, it would make sense to parse the text
                # and build the dict directly
                try:
                    response = r.json()
                except json.decoder.JSONDecodeError:
                    response = r.text
                self.services[service['name']['$']] = response
            else:
                self.services[service['name']['$']] = True
        return self.services


class HuntGroup:
    def __init__(self, parent: object,
                 id: str,
                 name: str,
                 location: str,
                 enabled: bool,
                 phone_number: str = None,
                 extension: str = None,
                 config: bool = True
                 ):
        """
        Initialize a HuntGroup instance
        Args:
            parent (Org): The Org instance to which the Hunt Group belongs
            id (str): The Webex ID for the Hunt Group
            name (str): The name of the Hunt Group
            location (str): The Location ID associated with the Hunt Group
            enabled (bool): Boolean indicating whether the Hunt Group is enabled
            phone_number (str, optional): The DID for the Hunt Group
            extension (str, optional): The extension of the Hunt Group
        Returns:
            HuntGroup: The HuntGroup instance
        """

        # Instance attrs
        self.parent: object = parent
        self.id: str = id
        """The Webex ID of the Hunt Group"""
        self.name: str = name
        """The name of the Hunt Group"""
        self.location: str = location
        """The Location ID associated with the Hunt Group"""
        self.enabled: bool = enabled
        """Whether the Hunt Group is enabled or not"""
        self.phone_number: str = phone_number
        """The DID for the Hunt Group"""
        self.extension: str = extension
        """The extension of the Hunt Group"""
        self.agents: list = []
        """List of agents/users assigned to this Hunt Group"""
        self.distinctive_ring: bool = False
        """Whether or not the Hunt Group has Distinctive Ring enabled"""
        self.alternate_numbers_settings: dict = {}
        """List of alternate numbers for this Hunt Group"""
        self.language: str = ""
        """The language name for the Hunt Group"""
        self.language_code: str = ""
        """The short name for the language of the Hunt Group"""
        self.first_name: str = ""
        """The Caller ID first name for the Hunt Group"""
        self.last_name: str = ""
        """The Caller ID last name for the Hunt Group"""
        self.time_zone: str = ""
        """The time zone for the Hunt Group"""
        self.call_policy: dict = {}
        """The Call Policy for the Hunt Group"""
        self.agents: list = []
        """List of users assigned to this Hunt Group"""
        self.raw_config: dict = {}
        """The raw JSON-to-Python config from Webex"""

        # Get the config unless we are asked not to
        if config:
            logging.info(f"Getting config for Hunt Group {self.id} in Location {self.location}")
            self.get_config()

    def get_config(self):
        """Get the Hunt Group config, including agents"""
        r = requests.get(_url_base + f"v1/telephony/config/locations/{self.location}/huntGroups/{self.id}",
                         headers=self.parent._headers)
        response = r.json()
        self.raw_config = response
        self.agents = response['agents']
        self.distinctive_ring = response.get("distinctiveRing", False)
        self.alternate_numbers_settings = response['alternateNumberSettings']
        self.language = response['language']
        self.language_code = response['languageCode']
        self.first_name = response['firstName']
        self.last_name = response['lastName']
        self.time_zone = response['timeZone']
        self.call_policy = response['callPolicies']

        return self.raw_config









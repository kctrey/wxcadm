import requests
import logging

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


class Webex:
    # TODO List
    #    Add token management
    #    Provide direct access to the children's methods

    def __init__(self, access_token, create_org=True, get_people=True, get_locations=True, get_xsi=False):
        logging.info("Webex instance initialized")
        # The access token is the only thing that we need to get started
        self._access_token = access_token
        # The Authorization header is going to be used by every API call in the package.
        # Might want to make it something global so we don't have to inherit it across all of the children
        self._headers = {"Authorization": "Bearer " + access_token}
        # Get the orgs that this token can manage
        r = requests.get(_url_base + "v1/organizations", headers=self._headers)
        response = r.json()
        # If a token can manage a lot of orgs, you might not want to create them all, because
        # it can take some time to do all of the API calls and get the data back
        if not create_org:
            self.orgs = response['items']
            return
        else:
            logging.info("Collecting orgs")
            self.orgs = []
            for org in response['items']:
                # This builds an Org instance for every Org, so be careful
                # if the user manages multiple orgs
                org = Org(org['displayName'], org['id'],
                          people=get_people, locations=get_locations, xsi=get_xsi, _parent=self)
                self.orgs.append(org)
            # Most users have only one org, so to make that easier for them to work with
            # we are also going to put the orgs[0] instance in the org attr
            # That way both .org and .orgs[0] are the same
            if len(self.orgs) == 1:
                self.org = self.orgs[0]


class Org:
    def __init__(self, name, id, people=True, locations=True, xsi=False, _parent=None):
        # Set the Authorization header based on how the instance was built
        if _parent is None:  # Instance wasn't created by another instance
            # TODO Need some code here to throw an error if there is no access_token and url_base
            pass
        else:
            # Since we need the headers for API calls, might as well just store it in a protected attr
            # Should this be a class attr instead of instance? Probably, but since I hope to allow Org creation
            # without a Webex parent, I am leaving it like this.
            self._headers = _parent._headers

        self.name = name
        self.id = id
        self.actions_uri = None
        self.events_uri = None
        self.events_channel_uri = None
        self._params = {"orgId": self.id}
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
        logging.info("__get_wxc_licenses started")
        license_list = []
        for license in self.licenses:
            if license['wxc_license']:
                license_list.append(license['id'])
        return license_list

    def get_person_by_email(self, email):
        """
        Get the Person instance from an email address
        :param email: The email of the Person to return
        :return: Person instance object. None in returned when no Person is found
        """
        logging.info("get_person_by_email() started")
        for person in self.people:
            if person.email == email:
                return person
        return None

    def get_xsi_endpoints(self):
        """
        Get the XSI endpoints for the Organization. Also stores them in the Org.xsi attribute.
        :return: Org.xsi attribute dictionary with each endpoint as a tuple
        """
        self.xsi = {}
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
        :return: List of Location instance objects. See the Locations class for attributes.
        """
        logging.info("get_locations() started")
        self.locations = []
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
        :return: List of Call Pickup Groups as a list of dictionaries. See the PickupGroup class for attributes.
        """
        logging.info("get_pickup_groups() started")
        self.pickup_groups = []
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
        logging.info("get_call_queues() started")
        self.call_queues = []
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

    def get_people(self):
        logging.info("get_people() started")
        self.people = []
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
                                 last_name=person['lastName'], display_name=person['displayName'], _parent=self)
            this_person.licenses = person['licenses']
            for license in person['licenses']:
                if license in wxc_licenses:
                    this_person.wxc = True
            self.people.append(this_person)
        return self.people

    def get_wxc_people(self):
        if not self.people:
            self.get_people()
        wxc_people = []
        for person in self.people:
            if person.wxc:
                wxc_people.append(person)
        return wxc_people

class Location:
    def __init__(self, location_id, name, address=None, **kwargs):
        if address is None:
            address = {}
        self.id = location_id
        self.name = name
        self.address = address

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
                 _parent=None,
                 access_token=None,
                 url_base=None,
                 **kwargs):
        # Default values for other attrs
        self.wxc = False
        self.vm_config = None
        self.recording = None
        self.barge_in = None
        self.call_forwarding = None
        self.caller_id = None
        self.intercept = None
        self.dnd = None
        self.calling_behavior = None


        # Set the Authorization header based on how the instance was built
        if licenses is None:
            licenses = []
        if _parent is None:  # Instance wasn't created by another instance
            # TODO Need some code here to throw an error if there is no access_token and url_base
            self._headers = {"Authorization": "Bearer " + access_token}
            self._url_base = url_base
        else:  # Instance was created by a parent
            self._headers = _parent._headers

        self._params = {"orgId": _parent.id}
        self.id = user_id
        self.email = user_email
        self.first_name = first_name
        self.last_name = last_name
        self.display_name = display_name
        self.licenses = licenses

    def __str__(self):
        return f"{self.email},{self.display_name}"

    # The following is to simplify the API call. Eventually I may open this as a public method to allow arbitrary API calls
    def __get_webex_data(self, endpoint, params=None):
        """

        :param endpoint: The endpoint of the API call (e.g. 'v1/locations')
        :param params: A dict of param values for the API call. Will be passed as URL params
        :return: Returns a dict of the JSON response from the API
        """
        if params is None:
            params = {}
        logging.info(f"__get_webex_data started for using {endpoint}")
        myparams = {**params, **self._params}
        r = requests.get(_url_base + endpoint, headers=self._headers, params=myparams)
        response = r.json()
        return response

    def __push_webex_data(self, endpoint, payload, params=None):
        if params is None:
            params = {}
        logging.info(f"__push_webex_data started using {endpoint}")
        myparams = {**params, **self._params}
        r = requests.put(_url_base + endpoint, headers=self._headers, params=myparams, json=payload)
        response_code = r.status_code
        if response_code == 200 or response_code == 204:
            return True
        else:
            return False

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
    def __init__(self, _parent, location, id, name, agents=None):
        self.location_id = location
        self.id = id
        self.name = name
        # If no agents were passed, we need to go get the configuration of the PickupGroup
        if agents == None:
            self.agents = []
            r = requests.get(_url_base + f"v1/telephony/config/locations/{self.location_id}/callPickups/{self.id}",
                             headers=_parent._headers
                             )
            response = r.json()
            print(r.text)
            # TODO It doesn't make sense to create a new Person instance for the below.
            #      Once we have an API and a class for Workspaces, it would make sense to tie
            #      the agents to the Person or Workspace instance
            # For now, we just write the values that we get back and the user can find the people with the
            # Person-specific methods
            for agent in response['agents']:
                self.agents.append(agent)


class CallQueue:
    def __init__(self, _parent, id, name, location, phone_number, extension, enabled, get_config=True):
        self._parent = _parent
        self.id = id
        self.name = name
        self.location_id = location
        self.phone_number = phone_number
        self.extension = extension
        self.enabled = enabled
        if get_config:
            self.get_queue_config()

    def get_queue_config(self):
        r = requests.get(_url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id,
                         headers=self._parent._headers)
        response = r.json()
        self.config = response

    def push(self):
        logging.info(f"Pushing Call Queue config to Webex for {self.name}")
        url = _url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id
        print(url)
        r = requests.put(url,
                         headers=self._parent._headers, json=self.config)
        response = r.status_code
        self.get_queue_config()
        return self.config

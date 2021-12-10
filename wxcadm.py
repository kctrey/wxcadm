import requests
import logging

#import globals
#TODO: Eventually I would like to use dataclasses, but it will be a heavy lift

# Set up logging
logging.basicConfig(level=logging.INFO, filename="wxcadm.log", format='%(asctime)s %(module)s:%(levelname)s:%(message)s')

class Webex:
    # TODO List
    #    Add token management
    # Provide direct access to the children's methods

    def __init__(self, access_token, create_org=True, get_people=True, get_locations=True, get_xsi=False):
        logging.info("Webex instance initialized")
        self.access_token = access_token
        self.url_base = "https://webexapis.com/"
        self.headers = {"Authorization": "Bearer " + self.access_token}
        r = requests.get(self.url_base + "v1/organizations", headers=self.headers)
        response = r.json()
        if create_org == False:
            self.orgs = response['items']
            return
        else:
            logging.info("Collecting orgs")
            orgs = []
            for org in response['items']:
                # This builds an Org instance for every Org, so be careful
                # if the user manages multiple orgs
                org = Org(org['displayName'], org['id'], people=get_people, locations=get_locations, xsi=get_xsi, _parent=self)
                orgs.append(org)
            self.orgs = orgs

class Org:
    def __init__(self, name, id, people=True, locations=True, xsi=False, _parent=None, access_token=None, url_base=None):
        # Set the Authorization header based on how the instance was built
        if _parent == None:     # Instance wasn't created by another instance
            #TODO Need some code here to throw an error if there is no access_token and url_base
            self._headers = {"Authorization": "Bearer " + access_token}
            self._url_base = url_base
        else:                   # Instance was created by a parent
            self._headers = _parent.headers
            self._url_base = _parent.url_base

        self.name = name
        self.id = id
        self.actions_uri = None
        self.events_uri = None
        self.events_channel_uri = None
        self._params = {"orgId": self.id}
        self.licenses = self.__get_licenses()
        # Get all of the people if we aren't told not to
        if people == True:
            self.get_people()
        # Get all of the locations if we aren't asked not to
        if locations == True:
            self.get_locations()
        if xsi == True:
            self.get_xsi_endpoints()

    def __str__(self):
        return(f"{self.name},{self.org_id}")

    def __get_licenses(self):
        logging.info("__get_licenses() started for org")
        license_list = []
        r = requests.get(self._url_base + "v1/licenses", headers=self._headers, params=self._params)
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
            if license['wxc_license'] == True:
                license_list.append(license['id'])
        return license_list

    def get_person_by_email(self, email):
        logging.info("get_person_by_email() started")
        for person in self.people:
            if person.email == email:
                return person
        return None

    def get_xsi_endpoints(self):
        self.xsi = {}
        params = {"callingData": "true", **self._params}
        r = requests.get(self._url_base + "v1/organizations/" + self.id, headers=self._headers, params=params)
        response = r.json()
        self.xsi['actions_endpoint'] = response['xsiActionsEndpoint']
        self.xsi['events_endpoint'] = response['xsiEventsEndpoint']
        self.xsi['events_channel_endpoint'] = response['xsiEventsChannelEndpoint']

        return self.xsi

    def get_locations(self):
        logging.info("get_locations() started")
        self.locations = []
        r = requests.get(self._url_base + "v1/locations", headers=self._headers, params=self._params)
        response = r.json()
        # I am aware that this doesn't support pagination, so there will be a limit on number of Locations returned
        for location in response['items']:
            this_location = Location(location['id'], location['name'], address=location['address'])
            self.locations.append(this_location)

        return self.locations

    def get_people(self):
        logging.info("get_people() started")
        self.people = []
        params = {"max": "1000", **self._params}
        r = requests.get(self._url_base + "v1/people", headers=self._headers, params=params)
        people_list = r.json()

        if "next" in r.links:
            keep_going = True
            next_url = r.links['next']['url']
            while keep_going == True:
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
            this_person = Person(person['id'], person['emails'][0], first_name=person['firstName'], last_name=person['lastName'], display_name=person['displayName'], _parent=self)
            this_person.licenses = person['licenses']
            for license in person['licenses']:
                if license in wxc_licenses:
                    this_person.wxc = True
            self.people.append(this_person)
        return self.people

class Location:
    def __init__(self, location_id, name, address={}, **kwargs):
        self.id = location_id
        self.name = name
        self.address = address

    def __str__(self):
        return(f"{self.name},{self.idea}")

class Person:
    # TODO List
    #    Add methods to get and return XSI identifiers

    def __init__(self, user_id,
                user_email,
                first_name=None,
                last_name=None,
                display_name=None,
                licenses=[],
                _parent=None,
                access_token=None,
                url_base=None,
                **kwargs):
        # Set the Authorization header based on how the instance was built
        if _parent == None:     # Instance wasn't created by another instance
            #TODO Need some code here to throw an error if there is no access_token and url_base
            self._headers = {"Authorization": "Bearer " + access_token}
            self._url_base = url_base
        else:                   # Instance was created by a parent
            self._headers = _parent._headers
            self._url_base = _parent._url_base

        self._params = {"orgId": _parent.id}
        self.id = user_id
        self.email = user_email
        self.first_name = first_name
        self.last_name = last_name
        self.display_name = display_name
        self.licenses = licenses

    def __str__(self):
        return(f"{self.email},{self.display_name}")

    # The following is to simplify the API call. Eventually I may open this as a public method to allow arbitrary API calls
    def __get_webex_data(self, endpoint, params={}):
        logging.info(f"__get_webex_data started for using {endpoint}")
        myparams = {**params, **self._params}
        r = requests.get(self._url_base + endpoint, headers=self._headers, params=params)
        response = r.json()
        return response

    def get_full_config(self):
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
    def __init__(_parent, location, 

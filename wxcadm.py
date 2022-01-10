import json.decoder
import time
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


class LicenseError(OrgError):
    def __init__(self, message):
        """Exceptions dealing with License problems within the Org"""
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
    #    Add token refresh, just for completeness. For now, we don't mess with tokens at all.
    """
    The base class for working with wxcadm.
    """
    def __init__(self,
                 access_token: str,
                 create_org: bool = True,
                 get_people: bool = True,
                 get_locations: bool = True,
                 get_xsi: bool = False,
                 get_hunt_groups: bool = False,
                 get_call_queues: bool = False
                 ) -> object:
        """
        Initialize a Webex instance to communicate with Webex and store data
        Args:
            access_token (str): The Webex API Access Token to authenticate the API calls
            create_org (bool, optional): Whether to create an Org instance for all organizations.
            get_people (bool, optional): Whether to get all of the People and created instances for them
            get_locations (bool, optional): Whether to get all Locations and create instances for them
            get_xsi (bool, optional): Whether to get the XSI endpoints for each Org. Defaults to False, since
                not every Org has XSI capability
            get_hunt_groups (bool, optional): Whether to get the Hunt Groups for each Org. Defaults to False.
            get_call_queues (bool, optional): Whether to get the Call Queues for each Org. Defaults to False.
        Returns:
            Webex: The Webex instance
        """
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
                          people=get_people, locations=get_locations, xsi=get_xsi, parent=self,
                          call_queues=get_call_queues, hunt_groups=get_hunt_groups)
                self.orgs.append(org)
            # Most users have only one org, so to make that easier for them to work with
            # we are also going to put the orgs[0] instance in the org attr
            # That way both .org and .orgs[0] are the same
            if len(self.orgs) == 1:
                logging.debug(f"Only one org found. Storing as Webex.org")
                self.org = self.orgs[0]

    @property
    def headers(self):
        """The "universal" HTTP headers with the Authorization header present"""
        return self._headers

    def get_org_by_name(self, name: str):
        """
        Get the Org instance that matches all or part of the name argument.
        Args:
            name (str): Text to match against the Org name
        Returns:
            Org: The Org instance of the matching Org
        Raises:
            KeyError: Raised when no match is made
        """
        for org in self.orgs:
            if name in org.name:
                return org
        raise KeyError("Org not found")

class Org(Webex):
    def __init__(self,
                 name: str,
                 id: str,
                 parent: Webex = None,
                 people: bool = True,
                 locations: bool = True,
                 hunt_groups: bool = False,
                 call_queues: bool = False,
                 xsi: bool = False,
                 ):
        """
        Initialize an Org instance

        Args:
            name (str): The Organization name
            id (str): The Webex ID of the Organization
            parent (Webex, optional): The parent Webex instance that owns this Org.
            people (bool, optional): Whether to get all People for the Org. Default True.
            locations (bool, optional): Whether to get all Locations for the Org. Default True.
            hunt_groups (bool, optional): Whether to get all Hunt Groups for the Org. Default False.
            call_queues (bool, optional): Whether to get all Call Queues for the Org. Default False.
            xsi (bool, optional): Whether to get the XSI Endpoints for the Org. Default False.

        Returns:
            Org: This instance of the Org class
        """

        # Instance attrs
        self.call_queues: list[CallQueue] = None
        """The Call Queues for this Org"""
        self.hunt_groups: list[HuntGroup] = None
        """The Hunt Groups for this Org"""
        self.pickup_groups: list[PickupGroup] = None
        'A list of the PickupGroup instances for this Org'
        self.locations: list[Location] = []
        'A list of the Location instances for this Org'
        self.name: str = name
        'The name of the Organization'
        self.id:  str = id
        '''The Webex ID of the Organization'''
        self.xsi: dict = {}
        """The XSI details for the Organization"""
        self._params: dict = {"orgId": self.id}
        self.licenses: list[dict] = []
        '''A list of all of the licenses for the Organization as a dictionary of names and IDs'''
        self.people: list[Person] = []
        '''A list of all of the Person stances for the Organization'''
        self.workspaces: list[Workspace] = None
        """A list of the Workspace instances for this Org."""
        self.workspace_locations: list[WorkspaceLocation] = None
        """A list of the Workspace Location instanced for this Org."""

        # Set the Authorization header based on how the instance was built
        self._headers = parent.headers
        self.licenses = self.__get_licenses()

        # Get all of the people if we aren't told not to
        if people:
            self.get_people()
        if locations:
            self.get_locations()
        if xsi:
            self.get_xsi_endpoints()
        if call_queues:
            self.get_call_queues()
        if hunt_groups:
            self.get_hunt_groups()

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
                if "Professional" in item['name']:
                    wxc_type = "person"
                elif "Workspace" in item['name']:
                    wxc_type = "workspace"
                else:
                    wxc_type = "unknown"
            else:
                wxc_license = False
                wxc_type = None
            lic = {"name": item['name'],
                   "id": item['id'],
                   "total": item['totalUnits'],
                   "consumed": item['consumedUnits'],
                   "subscription": item.get("subscriptionId", ""),
                   "wxc_license": wxc_license,
                   "wxc_type": wxc_type
                   }
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

    def __get_wxc_person_license(self):
        """
        Get the Webex Calling - Professional license ID
        Returns:
            str: The License ID
        Todo:
            Need to account for multiple subscriptions and calculate usage, throwing an exception when there
                is no license available.
        """
        logging.info("__get_wxc_person_license started to find available license")
        for license in self.licenses:
            if license['wxc_type'] == "person":
                return license['id']
        raise LicenseError("No Webex Calling Professional license found")



    def create_person(self, email: str,
                      location: str,
                      licenses: list = None,
                      calling: bool = True,
                      messaging: bool = True,
                      meetings: bool = True,
                      phone_number: str = None,
                      extension: str = None,
                      first_name: str = None,
                      last_name: str = None,
                      display_name: str = None,
                      ):
        """
        Create a new user in Webex. Also creates a new Person instance for the created user.
        Args:
            email (str): The email address of the user
            location (str): The ID of the Location that the user is assigned to.
            licenses (list, optional): List of license IDs to assign to the user. Use this when the license IDs
                are known. To have the license IDs determined dynamically, use the `calling`, `messaging` and
                `meetings` parameters.
            calling (bool, optional): BETA - Whether to assign Calling licenses to the user. Defaults to True.
            messaging (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            meetings (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            phone_number (str, optional): The phone number to assign to the user.
            extension (str, optional): The extension to assign to the user
            first_name (str, optional): The user's first name. Defaults to empty string.
            last_name (str, optional): The users' last name. Defaults to empty string.
            display_name (str, optional): The full name of the user as displayed in Webex. If first name and last name are passed
                without display_name, the display name will be the concatenation of first and last name.
        Returns:
            Person: The Person instance of the newly-created user.
        """
        if (first_name or last_name) and not display_name:
            display_name = f"{first_name} {last_name}"

        # Find the license IDs for each requested service, unless licenses was passed
        if not licenses:
            if calling:
                licenses.append(self.__get_wxc_person_license())
            if messaging:
                pass
            if meetings:
                pass

        # Build the payload to send to the API
        payload = {"emails": [email],
                   "phoneNumbers": [{"type": "work", "value": phone_number}],
                   "extension": extension,
                   "locationId": location,
                   "displayName": display_name,
                   "firstName": first_name,
                   "lastName": last_name,
                   "orgId": self.id,
                   "licenses": licenses
                   }
        r = requests.post(_url_base + "v1/people", headers=self._headers, params={"callingData": "true"},
                          json=payload)
        response = r.json()
        if r.status_code == 200:
            person = Person(response['id'], self, response)
            self.people.append(person)
            return person
        else:
            return f"{r.status_code} - {r.text}"

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

    def get_workspaces(self):
        """
        Get the Workspaces and Workspace Locations for the Organizations.
            Also stores them in the Org.workspaces and Org.workspace_locations attributes.

        Returns:
            list[Workspace]: List of Workspace instance objects. See the Workspace class for attributes.
        """
        logging.info("Getting Workspaces")
        self.workspaces = []
        r = requests.get(_url_base + "v1/workspaces", headers=self._headers, params=self._params)
        response = r.json()
        for workspace in response['items']:
            this_workspace = Workspace(self, workspace['id'], workspace)
            self.workspaces.append(this_workspace)

        logging.info("Getting Workspace Locations")
        self.workspace_locations = []
        r = requests.get(_url_base + "v1/workspaceLocations", headers=self._headers, params=self._params)
        response = r.json()
        for location in response['items']:
            this_location = WorkspaceLocation(self, location['id'], location)
            self.workspace_locations.append(this_location)

        return self.workspaces

    def get_pickup_groups(self):
        """
        Get all of the Call Pickup Groups for an Organization. Also stores them in the Org.pickup_groups attribute.
        Returns:
            list[PickupGroup]: List of Call Pickup Groups as a list of dictionaries.
                See the PickupGroup class for attributes.
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
        """
        Get the Call Queues for an Organization. Also stores them in the Org.call_queues attribute.
        Returns:
            list[CallQueue]: List of CallQueue instances for the Organization
        """
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

    def get_hunt_groups(self):
        """
        Get the Hunt Groups for an Organization. Also stores them in the Org.hunt_groups attribute.
        Returns:
            list[HuntGroup]: List of HuntGroup instances for the Organization
        """
        logging.info("get_hunt_groups() started")
        self.hunt_groups = []
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
        params = {"max": "1000", "callingData": "true", **self._params}
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

        self.wxc_licenses = self.__get_wxc_licenses()
        for person in people_list['items']:
            this_person = Person(person['id'], parent=self, config=person)
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

    def get_license_name(self, license_id: str):
        """
        Gets the name of a license by its ID
        Args:
            license_id (str): The License ID
        Returns:
            str: The License name. None if not found.
        """
        for license in self.licenses:
            if license['id'] == license_id:
                return license['name']
        return None


class Location:
    def __init__(self, location_id: str, name: str, address: dict = None):
        """
        Initialize a Location instance
        Args:
            location_id (str): The Webex ID of the Location
            name (str): The name of the Location
            address (dict): The address information for the Location
        Returns:
             Location (object): The Location instance
        """
        self.id: str = location_id
        """The Webex ID of the Location"""
        self.name: str = name
        """The name of the Location"""
        self.address: dict = address
        """The address of the Location"""

    @property
    def __str__(self):
        return f"{self.name},{self.id}"


class Person:
    def __init__(self, user_id, parent: object = None, config: dict = None):
        """
        Initialize a new Person instance. If only the `user_id` is provided, the API calls will be made to get
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
        """The roles assigned to this Person in Webex"""
        self.vm_config: dict = {}
        '''Dictionary of the VM config as returned by Webex API'''
        self.recording: dict = {}
        """Dictionary of the Recording config as returned by Webex API"""
        self.barge_in: dict = {}
        """Dictionary of Barge-In config as returned by Webex API"""
        self.call_forwarding: dict = {}
        '''Dictionary of the Call Forwarding config as returned by Webex API'''
        self.caller_id: dict = {}
        """Dictionary of Caller ID config as returned by Webex API"""
        self.intercept: dict = {}
        """Dictionary of Call Intercept config as returned by Webex API"""
        self.dnd: dict = {}
        """Dictionary of DND settings as returned by Webex API"""
        self.calling_behavior: dict = {}
        """Dictionary of Calling Behavior as returned by Webex API"""
        self.xsi = None
        """Holds the XSI instance when created with the `start_xsi()` method."""
        self.numbers: list = []
        """The phone numbers for this person from Webex CI"""
        self.extension: str = None
        """The extension for this person"""
        self._hunt_groups: list = []
        """A list of the Hunt Group instances that this user is an Agent for"""
        self._call_queues: list = []
        """A list of the Call Queue instances that this user is an Agent for"""

        # API-related attributes
        # Set the Authorization header based on how the instance was built
        if parent is None:  # Instance wasn't created by another instance
            # TODO Need some code here to throw an error if there is no access_token and url_base
            self._headers = {"Authorization": "Bearer " + access_token}
            self._url_base = url_base
        else:  # Instance was created by a parent
            self._headers = parent._headers
        self._params = {"orgId": parent.id, "callingData": "true"}

        # If the config was passed, process it. If not, make the API call for the Person ID and then process
        if config:
            self.__process_api_data(config)
        else:
            response = self.__get_webex_data(f"v1/people/{self.id}")
            self.__process_api_data(response)

    def __process_api_data(self, data: dict):
        """
        Takes the API data passed as the `data` argument and parses it to the instance attributes.
        Args:
            data (dict): A dictionary of the raw data returned by the `v1/people` API call
        """
        self.email = data['emails'][0]
        self.extension = data.get("extension", "")
        self.location = data.get("location", "")
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

    # The following is to simplify the API call. Eventually I may open this as a public method to
    # allow arbitrary API calls
    def __get_webex_data(self, endpoint: str, params: dict = None):
        """
        Issue a GET to the Webex API
        Args:
            endpoint (str): The endpoint of the call (i.e. "v1/people" or "/v1/people/{Person.id}")
            params (dict): Any additional params to be passed in the query (i.e. {"callingData":"true"}
        Returns:
            dict: The response from the Webex API
        """
        if params is None:
            params = {}
        logging.info(f"__get_webex_data started for using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.get(_url_base + endpoint, headers=self._headers, params=my_params)
        if r.status_code in [200]:
            response = r.json()
            return response
        else:
            return False

    def __put_webex_data(self, endpoint: str, payload: dict, params: dict = None):
        """
        Issue a PUT to the Webex API
        Args:
            endpoint: The endpoint of the call (i.e. "v1/people" or "/v1/people/{Person.id}")
            payload: A dict to send as the JSON payload of the PUT
            params: Any additional params to be passed in the query (i.e. {"callingData":"true"}
        Returns:
            bool: True if successful, False if not
        """
        if params is None:
            params = {}
        logging.info(f"__put_webex_data started using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.put(_url_base + endpoint, headers=self._headers, params=my_params, json=payload)
        response_code = r.status_code
        if response_code == 200 or response_code == 204:
            logging.info("Push successful")
            return True
        else:
            logging.info("Push failed")
            raise PutError(r.text)

    def start_xsi(self):
        """Starts an XSI session for the Person"""
        self.xsi = XSI(self)

    def get_full_config(self):
        """Fetches all of the Webex Calling settings for the Person. Due to the number of API calls, this
            method is not performed automatically on Person init and should be called for each Person during
            any subsequent processing. If you are only interested in one of the features, calling that method
            directly can significantly improve the time to return data.
        """
        logging.info(f"Getting the full config for {self.email}")
        if self.wxc:
            self.get_call_forwarding()
            self.get_vm_config()
            self.get_intercept()
            self.get_call_recording()
            self.get_caller_id()
            self.get_dnd()
            self.get_calling_behavior()
            self.get_barge_in()
            return self
        else:
            logging.info(f"{self.email} is not a Webex Calling user.")

    @property
    def hunt_groups(self):
        """
        The Hunt Groups that this user is an Agent for.
        Returns:
            list[HuntGroup]: A list of the `HuntGroup` instances the user belongs to
        """
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
        """
        The Call Queues that this user is an Agent for.
        Returns:
            list[CallQueue]: A list of the `CallQueue` instances the user belongs to
        """
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
        """Fetch the Call Forwarding config for the Person from the Webex API"""
        logging.info("get_call_forwarding() started")
        self.call_forwarding = self.__get_webex_data(f"v1/people/{self.id}/features/callForwarding")
        return self.call_forwarding

    def get_barge_in(self):
        """Fetch the Barge-In config for the Person from the Webex API"""
        logging.info("get_barge_in() started")
        self.barge_in = self.__get_webex_data(f"v1/people/{self.id}/features/bargeIn")
        return self.barge_in

    def get_vm_config(self):
        """Fetch the Voicemail config for the Person from the Webex API"""
        logging.info("get_vm_config() started")
        self.vm_config = self.__get_webex_data(f"v1/people/{self.id}/features/voicemail")
        return self.vm_config

    def push_vm_config(self):
        """Pushes the current Person.vm_config attributes back to Webex"""
        logging.info(f"Pushing VM Config for {self.email}")
        success = self.__put_webex_data(f"v1/people/{self.id}/features/voicemail", self.vm_config)
        if success:
            self.get_vm_config()
            return self.vm_config

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
        if email is None:
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
        logging.info(f"Getting DND for {self.email}")
        self.dnd = self.__get_webex_data(f"v1/people/{self.id}/features/doNotDisturb")
        return self.dnd

    def get_calling_behavior(self):
        logging.info(f"Getting Calling Behavior for {self.email}")
        self.calling_behavior = self.__get_webex_data(f"v1/people/{self.id}/features/callingBehavior")
        return self.calling_behavior

    def license_details(self):
        """
        Get the full details for all of the licenses assigned to the Person
        Returns:
            list[dict]: List of the license dictionaries
        """
        license_list = []
        for license in self.licenses:
            for org_lic in self._parent.licenses:
                if license == org_lic['id']:
                    license_list.append(org_lic)
        return license_list

    def refresh_person(self):
        """
        Pull a fresh copy of the Person details from the Webex API and update the instance. Useful when changes
            are made outside of the script or changes have been pushed and need to get updated info.
        Returns:
            bool: True if successful, False if not
        """
        response = self.__get_webex_data(f"v1/people/{self.id}")
        if response:
            self.__process_api_data(response)
            return True
        else:
            return False

    def update_person(self,
                      email = None,
                      numbers = None,
                      extension = None,
                      location = None,
                      display_name = None,
                      first_name = None,
                      last_name = None,
                      roles = None,
                      licenses = None):
        """
        Update the Person in Webex. Pass only the arguments that you want to change. Other attributes will be populated
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
        if not email:
            email = self.email
        payload['emails'] = [email]
        if not numbers:
            numbers = self.numbers
        payload['phoneNumbers'] = numbers
        if not extension:
            if self.extension:
                extension = self.extension
        payload['extension'] = extension
        if not location:
            location = self.location
        payload['location'] = location
        if not display_name:
            display_name = self.display_name
        payload['displayName'] = display_name
        if not first_name:
            first_name = self.first_name
        payload['firstName'] = first_name
        if not last_name:
            last_name = self.last_name
        payload['lastName'] = last_name
        if not roles:
            roles = self.roles
        payload['roles'] = roles
        if not licenses:
            licenses = self.licenses
        payload['licenses'] = licenses

        params = {"callingData": "true"}
        success = self.__put_webex_data(f"v1/people/{self.id}", payload, params)
        if success:
            self.refresh_person()
            return True
        else:
            return False

    def set_calling_only(self):
        """
        Removes the Messaging and Meetings licenses, leaving only the Calling capability. **Note that this does not
            work, and is just here for the future.**
        Returns:
            Person: The instance of this person with the updated values
        """
        # First, iterate the existing licenses and remove the ones we don't want
        # Build a list that contains the values to match on to remove
        remove_matches = ["messaging",
                          "meeting",
                          "free"]
        new_licenses = []
        for license in self.licenses:
            lic_name = self._parent.get_license_name(license)
            if lic_name:
                if lic_name.lower() not in remove_matches:
                    new_licenses.append((license))
                else:
                    continue
            else:
                continue
        success = self.update_person(licenses=new_licenses)
        return self

    def change_phone_number(self, new_number: str, new_extension: str = None):
        """
        Change a person's phone number and extension
        Args:
            new_number (str): The new phone number for the person
            new_extension (str, optional): The new extension, if changing. Omit to leave the same value.
        Returns:
            Person: The instance of this person, with the new values
        """
        if not new_extension:
            if self.extension:
                extension = self.extension
            else:
                extension = None
        else:
            extension = new_extension

        # Call the update_person() method
        success = self.update_person(numbers=[{"type": "work", "value": new_number}], extension=extension)
        return self


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
    def __init__(self, parent, get_profile: bool = False, cache: bool = False ):
        """
        The XSI class holds all of the relevant XSI data for a Person
        Args:
            parent (Person): The Person who this XSI instance belongs to
            get_profile (bool): Whether or not to automatically get the XSI Profile
            cache (bool): Whether to cache the XSI data (True) or pull it "live" every time (**False**)
        """
        logging.info(f"Initializing XSI instance for {parent.email}")
        # First we need to get the XSI User ID for the Webex person we are working with
        logging.info("Getting XSI identifiers")
        user_id_bytes = base64.b64decode(parent.id + "===")
        user_id_decoded = user_id_bytes.decode("utf-8")
        user_id_bwks = user_id_decoded.split("/")[-1]
        self.id = user_id_bwks

        # Inherited attributes
        self.xsi_endpoints = parent._parent.xsi
        self._cache = cache

        # API attributes
        self._headers = {"Content-Type": "application/json",
                         "Accept": "application/json",
                         "X-BroadWorks-Protocol-Version": "25.0",
                         **parent._headers}
        self._params = {"format": "json"}

        # Attribute definitions
        self._calls: list = []
        self._profile: dict = {}
        """The XSI Profile for this Person"""
        self._registrations:dict  = {}
        """The Registrations associated with this Person"""
        self.fac = None
        self.services = {}
        self._alternate_numbers: dict = {}
        """The Alternate Numbers for the Person"""
        self._anonymous_call_rejection: dict = {}
        """The Anonymous Call Rejection settings for this Person"""
        self._single_number_reach: dict = {}
        """The SNR (Office Anywhere) settings for this Person"""
        self._monitoring: dict = {}
        """The BLF/Monitoring settings for this Person"""
        self.conference: object = None

        # Get the profile if we have been asked to
        if get_profile:
            self.get_profile()

    def new_call(self, address: str = None):
        """
        Create a new Call instance
        Args:
            address (str, optional): The address to originate a call to
        Returns:
            Call: The Call instance
        """
        # If we got an address, pass it to the new instance
        if address is not None:
            call = Call(self, address=address)
        else:
            call = Call(self)
        self._calls.append(call)
        return call

    def new_conference(self, calls: list = [], comment:str = ""):
        """
        Crates a new Conference instance. A user can only have one Conference instance, so this will replace any
        previous Conference. At the moment, this **should not be called directly** and will be done dynamically by
        a Call.conference()
        Args:
            calls (list): A list of Call IDs involved in this conference. A conference is always started with only
                two Call IDs. Call IDs after the first two will be ignored.
            comment (str, optional): An optional text comment for the conference
        Returns:
            The instance of the Conference class
        """
        self.conference = Conference(self, calls, comment)
        return self.conference

    @property
    def calls(self):
        """
        Get the list of active calls and creates Call instances. Also destroys any Call instances that are no longer
        valid.
        Returns:
            list[Call]: List of Call instances
        """
        # First wipe out all of the existing instances
        for call in self._calls:
            del call
        self._calls.clear()
        calls_data: list = self.__get_xsi_data(f"/v2.0/user/{self.id}/calls")
        logging.debug(f"Calls Data: {calls_data}")
        if "call" not in calls_data['Calls']:
            self._calls = []
            return self._calls
        if type(calls_data['Calls']['call']) is dict:
            this_call = Call(self, id=calls_data['Calls']['call']['callId']['$'])
            self._calls.append(this_call)
        elif type(calls_data['Calls']['call']) is list:
            for call in calls_data['Calls']['call']:
                this_call = Call(self, id=call['callId']['$'])
                self._calls.append(this_call)
        return self._calls

    def __get_xsi_data(self, url, params: dict = {}):
        params = {**params, **self._params}
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + url, headers=self._headers, params=params)
        if r.status_code == 200:
            try:
                response = r.json()
            except json.decoder.JSONDecodeError:
                response = r.text
            return_data = response
        elif r.status_code == 404:
            return_data = False
        return return_data

    @property
    def monitoring(self):
        """The Monitoring/BLF settings for this person"""
        if not self._monitoring or not self._cache:
            self._monitoring = self.__get_xsi_data(f"/v2.0/user/{self.id}/services/BusyLampField")
        return self._monitoring

    @property
    def single_number_reach(self):
        """The SNR (Office Anywhere) settings for this Person"""
        if not self._single_number_reach or not self._cache:
            self._single_number_reach = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/services/BroadWorksAnywhere")
        return self._single_number_reach

    @property
    def anonymous_call_rejection(self):
        """The Anonymous Call Rejection settings for this Person"""
        if not self._anonymous_call_rejection or not self._cache:
            self._anonymous_call_rejection = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/services/AnonymousCallRejection")
        return self._anonymous_call_rejection

    @property
    def alternate_numbers(self):
        """The Alternate Numbers for this Person"""
        if not self._alternate_numbers or not self._cache:
            self._alternate_numbers = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/services/AlternateNumbers")
        return self._alternate_numbers

    @property
    def profile(self):
        """The XSI Profile for this Person"""
        if not self._profile or not self._cache:
            profile_data: dict = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/profile")
            # The following is a mapping of the raw XSI format to the profile attribute
            self._profile['registrations_url'] = profile_data['Profile']['registrations']['$']
            self._profile['schedule_url'] = profile_data['Profile']['scheduleList']['$']
            self._profile['fac_url'] = profile_data['Profile']['fac']['$']
            self._profile['country_code'] = profile_data['Profile']['countryCode']['$']
            self._profile['user_id'] = profile_data['Profile']['details']['userId']['$']
            self._profile['group_id'] = profile_data['Profile']['details']['groupId']['$']
            self._profile['service_provider'] = profile_data['Profile']['details']['serviceProvider']['$']
            # Not everyone has a number and/or extension, so we need to check to see if there are there
            if "number" in profile_data['Profile']['details']:
                self._profile['number'] = profile_data['Profile']['details']['number']['$']
            if "extension" in profile_data['Profile']['details']:
                self._profile['extension'] = profile_data['Profile']['details']['extension']['$']
        return self._profile

    @property
    def registrations(self):
        """The device registrations asscociated with this Person"""
        if not self._registrations or not self._cache:
            # If we don't have a registrations URL, because we don't have the profile, go get it
            if "registrations_url" not in self._profile:
                self.profile
            self._registrations = self.__get_xsi_data(self._profile['registrations_url'])
        return self._registrations

    def get_fac(self):
        # If we don't have a FAC URL, go get it
        if "fac_url" not in self._profile:
            self.profile()
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + self._profile['fac_url'],
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


class Call:
    """
    The Call class represents a call for a person. Since Webex supports calls in the Webex API as well as XSI API,
    the class supports both styles. When initialized, the parent instance is checked to see if it is a Person
    instance or an XSI instance. At the moment, the Webex API only supports user-scoped call control, so most of the
    development focus right now is the XSI API, which is more feature-rich
    """
    def __init__(self, parent, id: str = "", address: str = ""):
        """
        Inititalize a Call instance for a Person
        Args:
            parent (XSI): The Person or XSI instance that owns this Call
            id (str, optional): The Call ID of a known call. Usually only done during a XSI.calls method
            address (str, optional): The address to originate a call to when the instance is created
        Returns:
            Call: This Call instance
        """
        self._parent: XSI = parent
        """The Person or XSI instance that owns this Call"""
        self._userid: str = self._parent.id
        """The Person or XSI ID inherited from the parent"""
        self._headers = self._parent._headers
        self._params = self._parent._params
        self._url: str = ""
        self.id: str = id
        """The Call ID for this call"""
        self._external_tracking_id: str = ""
        """The externalTrackingId used by XSI"""
        self._status: dict = {}
        """The status of the call"""


        if type(self._parent) is Person:
            # This is where we set things based on whether the parent is a Person
            self._url = _url_base
            pass
        elif type(self._parent) is XSI:
            # The Call parent is XSI
            self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls"
        elif type(self._parent) is Call:
            # Another Call created this Call instance (probably for a transfer or conference
            self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._parent._userid}/calls"

        if address:
            self.originate(address)

    def originate(self, address: str, comment: str = ""):
        """
        Originate a call on behalf of the Person
        Args:
            address (str): The address (usually a phone number) to originate the call to
            comment (str, optional): Text comment to attach to the call
        Returns:
            bool: Whether the command was successful
        """
        logging.info(f"Originating a call to {address} for {self._userid}")
        params = {"address": address, "info": comment}
        r = requests.post(self._url + "/new", headers=self._headers, params=params)
        response = r.json()
        self.id = response['CallStartInfo']['callId']['$']
        self._external_tracking_id = response['CallStartInfo']['externalTrackingId']['$']
        if r.status_code == 201:
            return True
        else:
            return False

    def hangup(self):
        """
        Hang up the call
        Returns:
            bool: Whether the command was successful
        """
        logging.info(f"Hanging up call ID: {self.id}")
        r = requests.delete(self._url + f"/{self.id}",
                            headers=self._headers)
        if r.status_code == 200:
            return True
        else:
            return False

    @property
    def status(self):
        """
        The status of the call
        Returns:
            dict:

                {
                'network_call_id' (str): The unique identifier for the Network side of the call
                'personality'(str): The user's personalty (Originator or Terminator)
                'state' (str): The state of the call
                'remote_party' (dict): {
                    'address' (str): The address of the remote party
                    'call_type' (str): The call type
                    }
                'endpoint' (dict): {
                    'type' (str): The type of endpoint in use
                    'AoR' (str): The Address of Record for the endpoint
                    }
                'appearance' (str): The Call Appearance number
                'start_time' (str): The UNIX timestanp of the start of the call
                'answer_time' (str): The UNIX timestamp when the call was answered
                'status_time' (str): The UNIX timestamp of the status response
                }
        """
        logging.info(f"Getting call status")
        r = requests.get(self._url + f"/{self.id}",
                         headers=self._headers)
        response = r.json()
        logging.debug(f"Call Status response: {response}")
        if r.status_code == 200:
            return_data = {
                "network_call_id": response['Call']['networkCallId']['$'],
                "personality": response['Call']['personality']['$'],
                "state": response['Call']['state']['$'],
                "remote_party": {
                    "address": response['Call']['remoteParty']['address']['$'],
                    "call_type": response['Call']['remoteParty']['callType']['$'],
                },
                "endpoint": {
                    "type": response['Call']['endpoint']['@xsi1:type'],
                    "AoR": response['Call']['endpoint']['addressOfRecord']['$']
                },
                "appearance": response['Call']['appearance']['$'],
                "diversion_inhibited": response['Call']['diversionInhibited'],
                "start_time": response['Call']['startTime']['$'],
                "answer_time": response['Call']['answerTime']['$'],
                "status_time": int(time.time())
            }
            return return_data
        else:
            return False

    def transfer(self, address: str, type: str = "blind"):
        """
        Transfer the call to the selected address. Type of transfer can be controlled with `type` param. VM
        transfers will transfer the call directly to the voice mail of the address, even if the address is the
        user's own address. Attended transfers require a subsequent call to `finish_transfer()` when the actual transfer
        should happen.
        Args:
            address (str): The address (usually a phone number or extension) to transfer the call to
            type (str): ['blind','vm','attended']:
                The type of transfer.
        Returns:
            bool: True if successful. False if unsuccessful
        """
        logging.info(f"Transferring call {self.id} to {address} for {self._userid}")
        # Set the address param to be passed to XSI
        params = {"address": address}
        # Handle an attended transfer first. Anything else is assumed to be blind
        if type.lower() == "attended":
            # Attended transfer requires the first call to be put on hold and the second call to be
            # placed, so those are here. A separate call to finish_transfer will be required when the transfer should
            # happen.
            self.hold()
            self._transfer_call = self._parent.new_call()
            self._transfer_call.originate(address)
            return True
        elif type.lower() == "vm":
            r = requests.put(self._url + f"/{self.id}/VmTransfer", headers=self._headers, params=params)
            if r.status_code in [200, 201, 204]:
                return True
            else:
                return False
        else:
            r = requests.put(self._url + f"/{self.id}/BlindTransfer", headers=self._headers, params=params)
            if r.status_code in [200, 201, 204]:
                return True
            else:
                return False

    def finish_transfer(self):
        """
        Complete an Attended Transfer. This method will only complete if a `transfer(address, type="attended")`
        has been done first.
        Returns:
            bool: Whether or not the transfer completes
        """
        logging.info("Completing transfer...")
        r = requests.put(self._url + f"/{self.id}/ConsultTransfer/{self._transfer_call.id}", headers=self._headers)
        if r.status_code in [200, 201, 204]:
            return True
        else:
            return False, r.text

    def conference(self, address: str = ""):
        """
        Starts a multi-party conference. If the call is already held and an attended transfer is in progress,
        meaning the user is already talking to the transfer-to user, this method will bridge the calls.
        Args:
            address (str, optional): The address (usually a phone number or extension) to conference to. Not needed
                when the call is already part of an Attended Transfer
        Returns:
            bool: True if the conference is successful
        """
        # First, check to see if the call is already part of an attended transfer. If so, just build the conference
        # based on the two call IDs
        if self._transfer_call:
            xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
                  f"<Conference xmlns=\"http://schema.broadsoft.com/xsi\">" \
                  f"<conferenceParticipantList>" \
                  f"<conferenceParticipant>" \
                  f"<callId>{self.id}</callId>" \
                  f"</conferenceParticipant>" \
                  f"<conferenceParticipant>" \
                  f"<callId>{self._transfer_call.id}</callId>" \
                  f"</conferenceParticipant>" \
                  f"</conferenceParticipantList>" \
                  f"</Conference>"
            # Building the XML by hand for right now. Probably going to replace it with something JSON-friendly
            headers = self._headers
            headers['Content-Type'] = "application/xml; charset=UTF-8"
            r = requests.post(self._url + f"/Conference", headers=headers, data=xml)
            if r.status_code in [200, 201, 204]:
                return self._parent.new_conference([self.id, self._transfer_call.id])
            else:
                return False
        else:
            # Still needs work.
            pass

    def send_dtmf(self, dtmf: str):
        """
        Transmit DTMF tones outbound
        Args:
            dtmf (str): The string of dtmf digits to send. Accepted digits 0-9, star, pound. A comma will pause
                between digits (i.e. "23456#,123")
        Returns:
            bool: True if the dtmf was sent successfuly
        """
        params = {"playdtmf": str(dtmf)}
        r = requests.put(self._url + f"/{self.id}/TransmitDTMF", headers=self._headers, params=params)
        if r.status_code in [200, 201, 204]:
            return True
        else:
            return False, r.text


    def hold(self):
        """
        Place the call on hold
        Returns:
            bool: Whether the hold command was successful
        """
        r = requests.put(self._url + f"/{self.id}/Hold", headers=self._headers)
        if r.status_code in [200, 201, 204]:
            return True
        else:
            return False

    def resume(self):
        """Resume a call that was placed on hold
        Returns:
            bool: Whether the command was successful
        """
        r = requests.put(self._url + f"/{self.id}/Talk", headers=self._headers)
        if r.status_code in [200, 201, 204]:
            return True
        else:
            return False

class Conference:
    """The class for Conference Calls started by a Call.conference()"""
    def __init__(self, parent: object, calls: list, comment: str = ""):
        """
        Initialize a Conferece instance for an XSI instance
        Args:
            parent (XSI): The XSI instance that owns this conference
            calls (list): Call IDs associated with the Conference. Always two Call IDs to start a Conference.
                Any additional Call IDs will be added to the conference as it is created.
            comment (str, optional): An optional text comment for the Conference
        Returns:
            Conference: This instance of the Conference class
        """
        self._parent: XSI = parent
        self._calls: list = calls
        self._userid = self._parent.id
        self._headers = self._parent._headers
        self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls/Conference"
        self.comment: str = comment
        """Text comment associated with the Conference"""

    def deaf(self, call: str):
        """
        Stop audio and video from being sent to a participant. Audio and video from that participant are unaffected.
        Args:
            call (str): The Call ID to make deaf
        Returns:
            bool: Whether the command was successful
        """
        pass

class Workspace:
    def __init__(self, parent: Org, id: str, config: dict = None):
        """Initialize a Workspace instance. If only the `id` is provided, the configuration will be fetched from
            the Webex API. To save API calls, the config dict can be passed using the `config` argument
        Args:
            parent (Org): The Organization to which this workspace belongs
            id (str): The Webex ID of the Workspace
            config (dict): The configuration of the Workspace as returned by the Webex API
        """
        self.id: str = id
        """The Webex ID of the Workspace"""
        self._parent: Org = parent
        # Attributes inherited from the Org parent
        self._headers = self._parent._headers
        self._params = self._parent._params
        # Instance attributes
        self.location: str = None
        """The Webex ID of the Workspace Location (note this is a Workspace Location, not a Calling Location."""
        self.floor: str = None
        """The Webex ID of the Floor ID"""
        self.name: str = ""
        """The name of the Workspace"""
        self.capacity: int = None
        """The capacity of the Workspace"""
        self.type: str = None
        """
        The type of Workspace. Valid values are:
        
            "notSet": No value set
            "focus": High concentration
            "huddle": Brainstorm/collaboration
            "meetingRoom": Dedicated meeting space
            "open": Unstructured agile
            "desk": Individual
            "other": Unspecified
        """
        self.sip_address: str = None
        """The SIP Address used to call to the Workspace"""
        self.created: str = None
        """The date and time the workspace was created"""
        self.calling: str = None
        """
        The type of Calling license assigned to the Workspace. Valid values are:
        
            "freeCalling": Free Calling
            "hybridCalling": Hybrid Calling
            "webexCalling": Webex Calling
            "webexEdgeForDevices": Webex Edge for Devices
        """
        self.calendar: dict = None
        """The type of calendar connector assigned to the Workspace"""
        self.notes: str = None
        """Notes associated with the Workspace"""

        if config:
            self.__process_config(config)
        else:
            self.get_config()

    def get_config(self):
        """Get (or refresh) the confiration of the Workspace from the Webex API"""
        logging.info(f"Getting Workspace config for {self.id}")
        r = requests.get(_url_base + f"v1/workspaces/{self.id}", headers=self._headers, params=self._params)
        if r.status_code in [200]:
            response = r.json()
            self.__process_config(response)
        else:
            raise APIError(f"Unable to fetch workspace config for {self.id}")

    def __process_config(self, config: dict):
        """Processes the config dict, whether passed in init or from an API call"""
        self.name = config.get("displayName", "")
        self.location = config.get("workspaceLocationId", "")
        self.floor = config.get("floorId", "")
        self.capacity = config.get("capacity", 0)
        self.type = config['type']
        self.sip_address = config.get("sipAddress", "")
        self.created = config.get("created", "")
        if "calling" in config:
            self.calling = config['calling']['type']
        else:
            self.calling = "None"
        self.calendar = config['calendar']
        self.notes = config.get("notes", "")


class WorkspaceLocation:
    def __init__(self, parent: Org, id: str, config: dict = None):
        """Initialize a WorkspaceLocation instance. If only the `id` is provided, the configuration will be fetched from
            the Webex API. To save API calls, the config dict can be passed using the `config` argument
        Args:
            parent (Org): The Organization to which this WorkspaceLocation belongs
            id (str): The Webex ID of the WorkspaceLocation
            config (dict): The configuration of the WorkspaceLocation as returned by the Webex API
        """
        self.id: str = id
        """The Webex ID of the Workspace"""
        self._parent: Org = parent
        # Attributes inherited from the Org parent
        self._headers = self._parent._headers
        self._params = self._parent._params
        # Instance attributes
        self.name: str = None
        """The name of the WorkspaceLocation"""
        self.address: str = None
        """The address of the WorkspaceLocation"""
        self.country: str = None
        """The country code (ISO 3166-1) for the WorkspaceLocation"""
        self.city: str = None
        """The city name where the WorkspaceLocation is located"""
        self.latitude: float = None
        """The WorkspaceLocation latitude"""
        self.longitude: float = None
        """The WorkspaceLocation longitude"""
        self.notes: str = None
        """Notes associated with the WorkspaceLocation"""
        self.floors: list[WorkspaceLocationFloor] = None

        if config:
            self.__process_config(config)
        else:
            self.get_config()
        self.get_floors()

    def get_config(self):
        """Get (or refresh) the configuration of the WorkspaceLocations from the Webex API"""
        logging.info(f"Getting Workspace config for {self.id}")
        r = requests.get(_url_base + f"v1/workspaceLocations/{self.id}", headers=self._headers, params=self._params)
        if r.status_code in [200]:
            response = r.json()
            self.__process_config(response)
        else:
            raise APIError(f"Unable to fetch workspace config for {self.id}")

    def get_floors(self):
        """Get (or refresh) the WorkspaceLocationFloor instances for this WorkspaceLocation"""
        logging.info(f"Getting Location Floors for {self.name}")
        self.floors = []
        r = requests.get(_url_base + f"v1/workspaceLocations/{self.id}/floors",
                         headers=self._headers, params=self._params)
        response = r.json()
        for floor in response['items']:
            this_floor = WorkspaceLocationFloor(floor)
            self.floors.append(this_floor)

    def __process_config(self, config: dict):
        """Processes the config dict, whether passed in init or from an API call"""
        self.name = config.get("displayName", "")
        self.address = config.get("address", "")
        self.country = config.get("countryCode", "")
        self.city = config.get("cityName", "")
        self.latitude = config.get("latitude", "")
        self.longitude = config.get("longitude", "")
        self.notes = config.get("notes", "")

class WorkspaceLocationFloor(WorkspaceLocation):
    def __init__(self, config: dict):
        self.name = config.get("displayName")
        self.id = config.get("id")
        self.floor = config.get("floorNumber")


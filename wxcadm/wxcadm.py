import json.decoder
import time
import uuid
import re

import requests
import logging
import base64
from threading import Thread, Event

import xmltodict
import srvlookup

from .exceptions import *

# TODO: There is a package-wide problem where we have Webex-native data and instance attributes that we write
#       to make the instances easier to work with. I have kept the native data because it is easier to push back
#       to Webex and safer in case the API changes. Ideally, we should store all attributes in ways that a user
#       would want them and pack them back into JSON as needed. In the meantime, like in the CallQueues object
#       I end up with the same values in multiple attributes, which is a bad idea.

# Some functions available to all classes and instances (optionally)
_url_base = "https://webexapis.com/"

def webex_api_call(method: str, url: str, headers: dict, params: dict = None, payload: dict = None):
    """ Generic handler for all Webex API requests

    This function performs the Webex API call as a Session and handles processing the response. It has the ability
    to recognize paginated responses from the API and make subsequent requests to get all of the data, regardless of
    how many pages (calls) are needed.

    Args:
        method (str): The HTTP method to use. **get**, **post** and **put** are supported.
        url (str): The endpoint part of the URL (after https://webexapis.com/)
        headers (dict): HTTP headers to use with the request
        params (dict): Any paramaters to be passed as part of an API call
        payload: (dict): Payload that will be sent in a POST or PUT. Will be converted to JSON during the API call

    Returns:
        The return value will vary based on the API response. If a list of items are returned, a list will be returned.
            If the details for a single entry are returned by the API, a dict will be returned.

    Raises:
        wxcadm.exceptions.APIError: Raised when the API call fails to retrieve at least one response.

    """
    logging.debug("Webex API Call:")
    logging.debug(f"\tMethod: {method}")
    logging.debug(f"\tURL: {url}")

    start = time.time()     # Tracking API execution time
    session = requests.Session()
    session.headers.update(headers)

    if method.lower() == "get":
        r = session.get(_url_base + url, params=params)
        if r.ok:
            response = r.json()
            # With an 'items' array, we know we are getting multiple values. Without it, we are getting a singe entity
            if "items" in response:
                logging.debug(f"Webex returned {len(response['items'])} items")
            else:
                return response
        else:
            logging.debug("Webex API returned an error")
            raise APIError(f"The Webex API returned an error: {r.text}")

        # Now we look for pagination and get any additional pages as part of the same Session
        if "next" in r.links:
            keep_going = True
            next_url = r.links['next']['url']
            while keep_going:
                logging.debug(f"Getting more items from {next_url}")
                r = session.get(next_url)
                if r.ok:
                    new_items = r.json()
                    if "items" not in new_items:
                        continue        # This is here just to handle a weird case where the API responded with no data
                    logging.debug(f"Webex returned {len(new_items['items'])} more items")
                    response['items'].extend(new_items['items'])
                    if "next" not in r.links:
                        keep_going = False
                    else:
                        next_url = r.links['next']['url']
                else:
                    keep_going = False

        session.close()
        end = time.time()
        logging.debug(f"__webex_api_call() completed in {end - start} seconds")
        return response['items']
    else:
        return False


class Webex:
    """The base class for working with wxcadm"""
    def __init__(self,
                 access_token: str,
                 create_org: bool = True,
                 get_people: bool = True,
                 get_locations: bool = True,
                 get_xsi: bool = False,
                 get_hunt_groups: bool = False,
                 get_call_queues: bool = False,
                 fast_mode: bool = False,
                 people_list: list = None
                 ) -> None:
        """Initialize a Webex instance to communicate with Webex and store data

        Args:
            access_token (str): The Webex API Access Token to authenticate the API calls
            create_org (bool, optional): Whether to create an Org instance for all organizations.
            get_people (bool, optional): Whether to get all of the People and created instances for them
            get_locations (bool, optional): Whether to get all Locations and create instances for them
            get_xsi (bool, optional): Whether to get the XSI endpoints for each Org. Defaults to False, since
                not every Org has XSI capability
            get_hunt_groups (bool, optional): Whether to get the Hunt Groups for each Org. Defaults to False.
            get_call_queues (bool, optional): Whether to get the Call Queues for each Org. Defaults to False.
            fast_mode (bool, optional): When possible, optimize the API calls to Webex to work more quickly,
                sometimes at the expense of not getting as much data. Use this option only if you have a script that
                runs very slowly, especially during the Webex initialization when collecting people.
            people_list (list, optional): A list of people, by ID or email, to get instead of getting all People.
                **Note** that this ovverrides the ``get_people`` argument, only fetching the people in ``people_list``

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

        # Fast Mode flag when needed
        self._fast_mode = fast_mode

        # Instance attrs
        self.orgs: list[Org] = []
        '''A list of the Org instances that this Webex instance can manage'''
        # Get the orgs that this token can manage
        logging.debug(f"Making API call to v1/organizations")
        r = requests.get(_url_base + "v1/organizations", headers=self._headers)
        # Handle an invalid access token
        if r.status_code != 200:
            logging.critical("The Access Token was not accepted by Webex")
            raise TokenError("The Access Token was not accepted by Webex")
        response = r.json()
        # Handle when no Orgs are returned. This is pretty rare
        if len(response['items']) == 0:
            logging.warning("No Orgs were retuend by the Webex API")
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
                # If we were given a list of people, don't have the Org get all people
                if people_list is not None:
                    get_people = False
                org = Org(org['displayName'], org['id'],
                          people=get_people, locations=get_locations, xsi=get_xsi, parent=self,
                          call_queues=get_call_queues, hunt_groups=get_hunt_groups, people_list=people_list)
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
        """Get the Org instance that matches all or part of the name argument.

        Args:
            name (str): Text to match against the Org name

        Returns:
            Org: The Org instance of the matching Org

        Raises:
            wxcadm.exceptions.KeyError: Raised when no match is made

        """
        for org in self.orgs:
            if name in org.name:
                return org
        raise KeyError("Org not found")

    def get_person_by_email(self, email: str):
        """ Get the person instance  of a user with the given email address

        Unlike the :class:`Org` method of the same name, this method searches across all the Orgs that the token
        has access to, so it can find a user in any :class:`Org`

        Args:
            email (str): The email address to search for

        Returns:
            :class:`Person`: The Person instance. None is returned if no match is found

        """
        for org in self.orgs:
            person = org.get_person_by_email(email)
            if person is not None:
                return person
        return None


class Org:
    def __init__(self,
                 name: str,
                 id: str,
                 parent: Webex = None,
                 people: bool = True,
                 locations: bool = True,
                 hunt_groups: bool = False,
                 call_queues: bool = False,
                 xsi: bool = False,
                 people_list: list = None
                 ):
        """Initialize an Org instance

        Args:
            name (str): The Organization name
            id (str): The Webex ID of the Organization
            parent (Webex, optional): The parent Webex instance that owns this Org.
            people (bool, optional): Whether to get all People for the Org. Default True.
            locations (bool, optional): Whether to get all Locations for the Org. Default True.
            hunt_groups (bool, optional): Whether to get all Hunt Groups for the Org. Default False.
            call_queues (bool, optional): Whether to get all Call Queues for the Org. Default False.
            xsi (bool, optional): Whether to get the XSI Endpoints for the Org. Default False.
            people_list (list, optional): List of people, by ID or email to get instances for.

        Returns:
            Org: This instance of the Org class

        """

        # Instance attrs
        self._parent = parent
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
        self.id: str = id
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
        self._devices: list[Device] = None
        """A list of the Devce instances for this Org"""

        # Set the Authorization header based on how the instance was built
        self._headers = parent.headers
        self.licenses = self.__get_licenses()

        # Create a CPAPI instance for CPAPI work
        self._cpapi = CPAPI(self, self._parent._access_token)

        # Create a CSDM instance for CSDM work
        self._csdm = CSDM(self, self._parent._access_token)

        # Get all of the people if we aren't told not to
        if locations:
            self.get_locations()
        if xsi:
            self.get_xsi_endpoints()
        if call_queues:
            self.get_call_queues()
        if hunt_groups:
            self.get_hunt_groups()
        if people:
            self.get_people()
        if people_list:
            for person in people_list:
                self._get_person(person)

    @property
    def spark_id(self):
        org_id_bytes = base64.b64decode(self.id + "===")
        spark_id = org_id_bytes.decode("utf-8")
        return spark_id

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def __get_licenses(self):
        """Gets all of the licenses for the Organization

        Returns:
            list: List of dictionaries containing the license name and ID

        """
        logging.info("__get_licenses() started for org")
        license_list = []
        api_resp = webex_api_call("get", "v1/licenses", headers=self._headers, params=self._params)
        for item in api_resp:
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

    @property
    def numbers(self):
        """All of the Numbers for the Org

        Returns:
            list[dict]: List of dict containing information about each number

        """
        my_numbers = self._cpapi.get_numbers()
        for num in my_numbers:
            if "owner" in num:
                if "id" in num['owner']:
                    person = self.get_person_by_id(num['owner']['id'])
                    if person is not None:
                        num['owner'] = person
            if "location" in num:
                location = self.get_location_by_name(num['location']['name'])
                if location is not None:
                    num['location'] = location
        return my_numbers

    @property
    def devices(self):
        """All of the Device instances for the Org

        Returns:
            list[Device]: List of all Device instances
        """
        self._devices = self._csdm.get_devices()
        return self._devices

    def get_location_by_name(self, name: str):
        """Get the Location instance associated with a given Location ID

        Args:
            name (str): The full name of the Location to look for. (Case sensitive)

        Returns:
            Location: The Location instance. If no match is found, None is returned

        """
        for location in self.locations:
            if location.name == name:
                return location
        return None

    def get_person_by_id(self, id: str):
        """Get the Person instance associated with a given ID

        Args:
            id (str): The Webex ID of the Person to look for.

        Returns:
            Person: The Person instance. If no match is found, None is returned

        """
        for person in self.people:
            if person.id == id:
                return person
        return None

    def __get_wxc_licenses(self):
        """Get only the Webex Calling licenses from the Org.licenses attribute

        Returns:
            list[str]:

        """
        logging.info("__get_wxc_licenses started")
        license_list = []
        for license in self.licenses:
            if license['wxc_license']:
                license_list.append(license['id'])
        return license_list

    def get_wxc_person_license(self):
        """Get the Webex Calling - Professional license ID

        Returns:
            str: The License ID

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
        """Create a new user in Webex.

        Also creates a new Person instance for the created user.

        Args:
            email (str): The email address of the user
            location (str): The ID of the Location that the user is assigned to.
            licenses (list, optional): List of license IDs to assign to the user. Use this when the license IDs
            are known. To have the license IDs determined dynamically, use the `calling`, `messaging` and
            meetings` parameters.

            calling (bool, optional): BETA - Whether to assign Calling licenses to the user. Defaults to True.
            messaging (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            meetings (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            phone_number (str, optional): The phone number to assign to the user.
            extension (str, optional): The extension to assign to the user
            first_name (str, optional): The user's first name. Defaults to empty string.
            last_name (str, optional): The users' last name. Defaults to empty string.
            display_name (str, optional): The full name of the user as displayed in Webex. If first name and last name
                are passed without display_name, the display name will be the concatenation of first and last name.

        Returns:
            Person: The Person instance of the newly-created user.

        """
        logging.info(f"Creating new user: {email}")
        if (first_name or last_name) and display_name is None:
            logging.debug("No display_name provided. Setting default.")
            display_name = f"{first_name} {last_name}"

        # Find the license IDs for each requested service, unless licenses was passed
        if not licenses:
            logging.debug("No licenses specified. Finding licenses.")
            licenses = []
            if calling:
                logging.debug("Calling requested. Finding Calling licenses.")
                logging.debug(f"Licenses: {self.get_wxc_person_license()}")
                licenses.append(self.get_wxc_person_license())
            if messaging:
                pass
            if meetings:
                pass

        # Build the payload to send to the API
        logging.debug("Building payload.")
        payload = {"emails": [email], "locationId": location, "orgId": self.id, "licenses": licenses}
        if phone_number is not None:
            payload["phoneNumbers"] = [{"type": "work", "value": phone_number}]
        if extension is not None:
            payload["extension"] = extension
        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if display_name is not None:
            payload["displayName"] = display_name
        logging.debug(f"Payload: {payload}")
        r = requests.post(_url_base + "v1/people", headers=self._headers, params={"callingData": "true"},
                          json=payload)
        response = r.json()
        if r.status_code == 200:
            person = Person(response['id'], self, response)
            self.people.append(person)
            return person
        else:
            raise PutError(response['message'])

    def get_person_by_email(self, email):
        """Get the Person instance from an email address

        Args:
            email (str): The email of the Person to return

        Returns:
            Person: Person instance object. None in returned when no Person is found

        """
        logging.info("get_person_by_email() started")
        for person in self.people:
            if person.email.lower() == email.lower():
                return person
        return None

    def get_xsi_endpoints(self):
        """Get the XSI endpoints for the Organization.

        Also stores them in the Org.xsi attribute.

        Returns:
            dict: Org.xsi attribute dictionary with each endpoint as an entry.

        """
        params = {"callingData": "true", **self._params}
        response = webex_api_call("get", "v1/organizations/" + self.id, headers=self._headers, params=params)
        if "xsiActionsEndpoint" in response:
            self.xsi['xsi_domain'] = response['xsiDomain']
            self.xsi['actions_endpoint'] = response['xsiActionsEndpoint']
            self.xsi['events_endpoint'] = response['xsiEventsEndpoint']
            self.xsi['events_channel_endpoint'] = response['xsiEventsChannelEndpoint']
        else:
            raise XSIError("XSI requested but not present in Org. Contact Cisco TAC to enable XSI.")
        return self.xsi

    def get_locations(self):
        """Get the Locations for the Organization.

        Also stores them in the Org.locations attribute.

        Returns:
            list[Location]: List of Location instance objects. See the Locations class for attributes.

        """
        logging.info("get_locations() started")
        api_resp = webex_api_call("get", "v1/locations", headers=self._headers, params=self._params)
        for location in api_resp:
            this_location = Location(self, location['id'], location['name'], address=location['address'])
            self.locations.append(this_location)
        return self.locations

    def get_workspaces(self):
        """Get the Workspaces and Workspace Locations for the Organizations.

        Also stores them in the Org.workspaces and Org.workspace_locations attributes.

        Returns:
            list[Workspace]: List of Workspace instance objects. See the Workspace class for attributes.

        """
        logging.info("Getting Workspaces")
        self.workspaces = []
        api_resp = webex_api_call("get", "v1/workspaces", headers=self._headers, params=self._params)
        for workspace in api_resp:
            this_workspace = Workspace(self, workspace['id'], workspace)
            self.workspaces.append(this_workspace)

        logging.info("Getting Workspace Locations")
        self.workspace_locations = []
        api_resp = webex_api_call("get", "v1/workspaceLocations", headers=self._headers, params=self._params)
        for location in api_resp:
            this_location = WorkspaceLocation(self, location['id'], location)
            self.workspace_locations.append(this_location)

        return self.workspaces

    def get_pickup_groups(self):
        """Get all of the Call Pickup Groups for an Organization.

        Also stores them in the Org.pickup_groups attribute.

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
            api_resp = webex_api_call("get", "v1/telephony/config/locations/" + location.id + "/callPickups",
                                      headers=self._headers)
            for item in api_resp['callPickups']:
                pg = PickupGroup(self, location.id, item['id'], item['name'])
                self.pickup_groups.append(pg)
        return self.pickup_groups

    def get_call_queues(self):
        """Get the Call Queues for an Organization.

        Also stores them in the Org.call_queues attribute.

        Returns:
            list[CallQueue]: List of CallQueue instances for the Organization

        """
        logging.info("get_call_queues() started")
        self.call_queues = []
        if not self.locations:
            self.get_locations()
        api_resp = webex_api_call("get", "v1/telephony/config/queues", headers=self._headers, params=self._params)
        for queue in api_resp['queues']:
            id = queue.get("id")
            name = queue.get("name", None)
            location_id = queue.get("locationId")
            phone_number = queue.get("phoneNumber", None)
            extension = queue.get("extension", None)
            enabled = queue.get("enabled")

            queue = CallQueue(self, id, name, location_id, phone_number, extension, enabled, get_config=True)
            self.call_queues.append(queue)
        return self.call_queues

    def get_call_queue_by_id(self, id: str):
        """ Get the :class:`CallQueue` instance with the requested ID
        Args:
            id (str): The CallQueue ID

        Returns:
            HuntGroup: The :class:`CallQueue` instance

        """
        for cq in self.call_queues:
            if cq.id == id:
                return cq
        return None

    def get_hunt_group_by_id(self, id: str):
        """ Get the :class:`HuntGroup` instance with the requested ID
        Args:
            id (str): The HuntGroup ID

        Returns:
            HuntGroup: The :class:`HuntGroup` instance

        """
        for hg in self.hunt_groups:
            if hg.id == id:
                return hg
        return None

    def get_hunt_groups(self):
        """Get the Hunt Groups for an Organization.

        Also stores them in the Org.hunt_groups attribute.

        Returns:
            list[HuntGroup]: List of HuntGroup instances for the Organization

        """
        logging.info("get_hunt_groups() started")
        self.hunt_groups = []
        if not self.locations:
            self.get_locations()

        api_resp = webex_api_call("get", "v1/telephony/config/huntGroups", headers=self._headers, params=self._params)
        for hg in api_resp['huntGroups']:
            hunt_group = HuntGroup(self, hg['id'], hg['name'], hg['locationId'], hg['enabled'],
                                   hg.get("phoneNumber", ""), hg.get("extension", ""))
            self.hunt_groups.append(hunt_group)
        return self.hunt_groups

    def get_people(self):
        """Get all of the people within the Organization.

        Also creates a Person instance and stores it in the Org.people attributes

        Returns:
            list[Person]: List of Person instances

        """
        logging.info("get_people() started")
        params = {"max": "1000", "callingData": "true", **self._params}
        # Fast Mode - callingData: false is much faster
        if self._parent._fast_mode is True:
            params['callingData'] = "false"
        people = webex_api_call("get", "v1/people", headers=self._headers, params=params)
        logging.info(f"Found {len(people)} people.")

        self.wxc_licenses = self.__get_wxc_licenses()

        for person in people:
            this_person = Person(person['id'], parent=self, config=person)
            self.people.append(this_person)
        return self.people

    def _get_person(self, match):
        logging.info(f"Getting person: {match}")
        self.wxc_licenses = self.__get_wxc_licenses()
        if "@" in match:
            params = {"max": "1000", "callingData": "true", "email": match, **self._params}
            url = "v1/people"
            response = webex_api_call("get", url, headers=self._headers, params=params)
            this_person = Person(response[0]['id'], parent=self, config=response[0])
        else:
            params = {"callingData": "true"}
            url = f"v1/people/{match}"
            response = webex_api_call("get", url, headers=self._headers, params=params)
            this_person = Person(response['id'], parent=self, config=response)
        self.people.append(this_person)
        return this_person


    def get_wxc_people(self):
        """Get all of the people within the Organization **who have Webex Calling**

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
        """Gets the name of a license by its ID

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
    def __init__(self, parent: Org, location_id: str, name: str, address: dict = None):
        """Initialize a Location instance

        Args:
            location_id (str): The Webex ID of the Location
            name (str): The name of the Location
            address (dict): The address information for the Location

        Returns:
             Location (object): The Location instance

        """
        self._parent = parent
        self.id: str = location_id
        """The Webex ID of the Location"""
        self.name: str = name
        """The name of the Location"""
        self.address: dict = address
        """The address of the Location"""

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def spark_id(self):
        """The ID used by all of the underlying services."""
        bytes = base64.b64decode(self.id + "===")
        spark_id = bytes.decode("utf-8")
        return spark_id

    @property
    def hunt_groups(self):
        """List of HuntGroup instances for this Location"""
        my_hunt_groups = []
        for hg in self._parent.hunt_groups:
            if hg.location == self.id:
                my_hunt_groups.append(hg)
        return my_hunt_groups

    @property
    def call_queues(self):
        """List of CallQueue instances for this Location"""
        my_call_queues = []
        for cq in self._parent.call_queues:
            if cq.location_id == self.id:
                my_call_queues.append(cq)
        return my_call_queues

    @property
    def available_numbers(self):
        """Returns all of the available numbers for the Location.

        Only returns active numbers, so numbers that have not been activated yet will not be returned.

        Returns:
            list[dict]: A list of available numbers, in dict form

        """
        available_numbers = []
        for number in self._parent.numbers:
            if number['location'].name == self.name and number.get('state', "") == "ACTIVE":
                available_numbers.append(number)
        return available_numbers

    @property
    def main_number(self):
        """Returns the Main Number for this Location, if defined

        Returns:
            str: The main number for the Location. None is returned if a main number cannot be found.

        """
        for number in self._parent.numbers:
            if number['location'].name == self.name and number['mainNumber'] is True:
                return number['number']
        return None


class Person:
    def __init__(self, user_id, parent: Org = None, config: dict = None):
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
        logging.info(f"__get_webex_data started for using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.get(_url_base + endpoint, headers=self._headers, params=my_params)
        if r.status_code in [200]:
            response = r.json()
            return response
        else:
            return False

    def __put_webex_data(self, endpoint: str, payload: dict, params: dict = None):
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
        logging.info(f"__put_webex_data started using {endpoint}")
        my_params = {**params, **self._params}
        r = requests.put(_url_base + endpoint, headers=self._headers, params=my_params, json=payload)
        response_code = r.status_code
        if response_code == 200 or response_code == 204:
            logging.info("Push successful")
            return True
        else:
            logging.info("Push failed")
            return False

    @property
    def spark_id(self):
        user_id_bytes = base64.b64decode(self.id + "===")
        spark_id = user_id_bytes.decode("utf-8")
        return spark_id

    def assign_wxc(self, location: Location, phone_number: str = None, extension: str = None):
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

    def start_xsi(self):
        """Starts an XSI session for the Person"""
        self.xsi = XSI(self)
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

        """
        self._parent._cpapi.reset_vm_pin(self, pin=pin)

    def get_full_config(self):
        """
        Fetches all of the Webex Calling settings for the Person. Due to the number of API calls, this
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
        """The Hunt Groups that this user is an Agent for.

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
        """The Call Queues that this user is an Agent for.

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

    def push_vm_config(self, vm_config: dict = None):
        """ Push the Voicemail config back to Webex

        If the vm_config dict is provided, it will be sent as the payload to Webex. If it is omitted, the current
        Person.call_forwarding attributes will be sent.

        Args:
            vm_config (dict, optional: The vm_config dictionary to push to Webex

        Returns:
            dict: The new config that was sent back by Webex. False is returned if the API call fails.

        """
        logging.info(f"Pushing VM Config for {self.email}")
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

    def push_cf_config(self, cf_config: dict = None):
        """ Pushes the Call Forwarding config back to Webex

        If the cf_config dict is provided, it will be sent as the PUT payload. If it is omitted, the current
        Person.call_forwarding attributes will be sent

        Args:
            cf_config (dict, optional): The cf_config dictionary to push to Webex

        Returns:
            dict: The new config that was sent back by Webex

        """
        logging.info(f"Pushing CF Config for {self.email}")
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
        if not self.vm_config:
            self.get_vm_config()
        self.vm_config['emailCopyOfMessage']['enabled'] = False
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

        r = requests.put(_url_base + f"v1/people/{self.id}/features/callerId",
                           headers=self._headers, json=payload)
        if r.ok:
            return True
        else:
            raise APIError(f"CPAPI failed to update Caller ID for Person: {r.text}")

    def get_dnd(self):
        logging.info(f"Getting DND for {self.email}")
        self.dnd = self.__get_webex_data(f"v1/people/{self.id}/features/doNotDisturb")
        return self.dnd

    def get_calling_behavior(self):
        logging.info(f"Getting Calling Behavior for {self.email}")
        self.calling_behavior = self.__get_webex_data(f"v1/people/{self.id}/features/callingBehavior")
        return self.calling_behavior

    def license_details(self):
        """Get the full details for all of the licenses assigned to the Person

        Returns:
            list[dict]: List of the license dictionaries

        """
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

    def set_calling_only(self):
        """
        Removes the Messaging and Meetings licenses, leaving only the Calling capability.

        Returns:
            Person: The instance of this person with the updated values

        """
        logging.info(f"Setting {self.email} to Calling-Only")
        # First, iterate the existing licenses and remove the ones we don't want
        # Build a list that contains the values to match on to remove
        remove_matches = ["messaging",
                          "meeting",
                          "free"]
        new_licenses = []
        for license in self.licenses:
            logging.debug(f"Checking license: {license}")
            lic_name = self._parent.get_license_name(license)
            logging.debug(f"License Name: {lic_name}")
            if any(match in lic_name.lower() for match in remove_matches):
                if "screen share" in lic_name.lower():
                    logging.debug(f"{lic_name} matches but is needed")
                    new_licenses.append(license)
                else:
                    logging.debug(f"License should be removed")
                    continue
            else:
                logging.debug(f"Keeping license")
                new_licenses.append(license)

        success = self.update_person(licenses=new_licenses)
        return self

    def change_phone_number(self, new_number: str, new_extension: str = None):
        """"Change a person's phone number and extension

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

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

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

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def get_queue_config(self):
        """Get the configuration of this Call Queue instance

        Returns:
            CallQueue.config: The config dictionary of this Call Queue

        """
        r = requests.get(_url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id,
                         headers=self._parent._headers)
        response = r.json()
        self.config = response
        return self.config

    def get_queue_forwarding(self):
        """Get the Call Forwarding settings for this Call Queue instance

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
        """Push the contents of the CallQueue.config back to Webex

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

class XSICallQueue:
    def __init__(self, call_queue_id: str, org: Org):
        """ Initialize an instance to control calls within a Webex Calling Call Queue.

        This class is used primarily when monitoring XSI Events where there is a need to control calls that come
        into a Call Queue. Since Call Queues are "virtual" users within the call control, there are special methods
        required to deal with those calls.

        Args:
            call_queue_id (str): The ID of the Call Queue as shown in the ``xsi:targetId`` of an XSI Event
            org (Org): The instance of the wxcadm.Org class (i.e. "webex.org"). This is needed to provide the right
                authentication and URLs for the XSI service.
        """
        logging.info(f"Starting XSICallCenter for {call_queue_id}")
        self.id = call_queue_id
        self.org = org
        self._calls = []
        self._headers = org._headers
        self._params = org._params

    def attach_call(self, call_id: str):
        """ Attach an active call to the XSICallQueue instance

        Attaching a call provides a :class:`wxcadm.Call` instance that can be used to control the call. Note that not
        all call controls are available to a Call Queue call, but the basic ones, including Transfer, are available.

        Args:
            call_id (str): The callId from the XSI Events message

        Returns:
            Call: The :class:`wxcadm.Call` instance that was attached

        """
        call = Call(self, id = call_id)
        self._calls.append(call)
        return call


class XSI:
    def __init__(self, parent, get_profile: bool = False, cache: bool = False):
        """The XSI class holds all of the relevant XSI data for a Person

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
        self._registrations: dict = {}
        """The Registrations associated with this Person"""
        self.fac = None
        self.services = {}
        self._alternate_numbers: dict = {}
        """The Alternate Numbers for the Person"""
        self._anonymous_call_rejection: dict = {}
        """The Anonymous Call Rejection settings for this Person"""
        self._executive_assistant: dict = {}
        """The Executive Assistant settings for this Person"""
        self._executive: dict = {}
        """The Executive settings for this Person"""
        self._single_number_reach: dict = {}
        """The SNR (Office Anywhere) settings for this Person"""
        self._monitoring: dict = {}
        """The BLF/Monitoring settings for this Person"""
        self.conference: object = None

        # Get the profile if we have been asked to
        if get_profile:
            self.get_profile()

    def new_call(self, address: str = None):
        """Create a new Call instance

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

    def new_conference(self, calls: list = [], comment: str = ""):
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

    def answer_call(self, call_id: str = None):
        """ Answer an incoming call

        If the call_id is not provided, the method will try and answer the latest/only call for the user.

        Args:
            call_id (str, optional): The call_id to answer

        Returns:
            Call: The :class:`Call` instance of the answered call. None is returned if no calls can be found.

        """
        call = self.calls[-1]
        if call is not None:
            call.resume()
            return call
        else:
            return None


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

    def attach_call(self, call_id: str):
        """ Attach an active call to the XSICallQueue instance

        Attaching a call provides a :class:`wxcadm.Call` instance that can be used to control the call. Note that not
        all call controls are available to a Call Queue call, but the basic ones, including Transfer, are available.

        Args:
            call_id (str): The callId from the XSI Events message

        Returns:
            Call: The :class:`wxcadm.Call` instance that was attached

        """
        call = Call(self, id = call_id)
        self._calls.append(call)
        return call

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
        else:
            return_data = False
        return return_data

    @property
    def executive(self):
        """The Executive Assistant settings for this Person"""
        if not self._executive or not self._cache:
            self._executive = self.__get_xsi_data(f"/v2.0/user/{self.id}/services/Executive")
        return self._executive

    @property
    def executive_assistant(self):
        """The Executive Assistant settings for this Person"""
        if not self._executive_assistant or not self._cache:
            self._executive_assistant = self.__get_xsi_data(f"/v2.0/user/{self.id}/services/ExecutiveAssistant")
        return self._executive_assistant

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
        """The device registrations associated with this Person"""
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

class XSIEvents:
    def __init__(self, parent: Org):
        """ Initialize an XSIEvents instance to provide access to XSI-Events

        Args:
            parent (Org): The Webex.Org instance that these Events are associated with. Currently, only Org-level
                events can be monitored. User-level subscriptions will be added later.
        """
        self._parent = parent
        self._headers = parent._headers
        self.events_endpoint = parent.xsi['events_endpoint']
        self.channel_endpoint = parent.xsi['events_channel_endpoint']
        self.xsi_domain = parent.xsi['xsi_domain']
        self.application_id = uuid.uuid4()
        self.enterprise = self._parent.spark_id.split("/")[-1]
        self.channel_sets = []
        self.queue = None

    def open_channel(self, queue):
        """ Open an XSI Events channel and start pushing Events into the queue.

        For now, this only accepts a Queue instance as the queue argument.

        Args:
            queue (Queue): The Queue instance to place events into

        Returns:
            XSIEventsChannelSet: The :class:`XSIEventsChannelSet` instance that was opened

        """
        self.queue = queue
        logging.debug("Initializing Channel Set")
        channel_set = XSIEventsChannelSet(self)
        self.channel_sets.append(channel_set)
        return channel_set


class XSIEventsChannelSet:
    def __init__(self, parent: XSIEvents):
        """ Inititalize an XSIEventsChannelSet instance to manage channels and subscriptions.

        Calling this method, which is normally done with the :meth:`XSIEvents.open_channel()` method, automatically
        creates the channels to each XSP in the region and begins send heartbeat messages on them.

        Args:
            parent (XSIEvents): The XSIEvents instance to which this ChanelSet belongs.
        """
        self.parent = parent
        self._headers = self.parent._headers
        self.id = uuid.uuid4()
        logging.debug(f"Channel Set ID: {self.id}")
        self.channels = []
        self.subscriptions = []
        self.queue = self.parent.queue

        # Now init the channels. Get the SRV records to ensure they get opended with each XSP
        srv_records = srvlookup.lookup("xsi-client", "TCP", self.parent.xsi_domain)
        for record in srv_records:
            my_endpoint = re.sub(self.parent.xsi_domain, record.host, self.parent.channel_endpoint)
            my_events_endpoint = re.sub(self.parent.xsi_domain, record.host, self.parent.events_endpoint)
            logging.debug(f"Establishing channel with endpoint: {record.host}")
            channel = XSIEventsChannel(self, my_endpoint, my_events_endpoint)
            self.channels.append(channel)

        # Now that we have the channels build, start the daemons (threads) for each
        for channel in self.channels:
            channel_thread = Thread(target=channel.channel_daemon, daemon=True)
            channel_thread.start()
            # Wait a few seconds to start the heartbeats
            time.sleep(2)
            heartbeat_thread = Thread(target=channel.heartbeat_daemon, daemon=True)
            heartbeat_thread.start()

    def subscribe(self, event_package):
        """ Subscribe to an Event Package over the channel opened with :meth:`XSIEvents.open_channel()`

        Args:
            event_package (str): The name of the Event Package to subscribe to.

        Returns:
            XSIEventsSubscription: The Subscription instance. False is returned if the subscription fails.

        """
        subscription = XSIEventsSubscription(self, event_package)
        if subscription:
            self.subscriptions.append(subscription)
            return subscription
        else:
            return False

class XSIEventsSubscription:
    def __init__(self, parent: XSIEventsChannelSet, event_package: str):
        """ Initialize an XSIEventsSubscription

        Initializing the subscription also sends the subscription to the XSI API over the events_endpoint.

        Args:
            parent (XSIEventsChannelSet): The XSIEventsChannelSet instance to issue the subscription for.
            event_package (str): The XSI Event Package to subscribe to.
        """
        self.id = ""
        self.parent = parent
        self.events_endpoint = self.parent.parent.events_endpoint
        self._headers = self.parent._headers
        self.last_refresh = time.time()
        self.event_package = event_package
        logging.info(f"Subscribing to: {self.event_package}")
        payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
                  '<Subscription xmlns=\"http://schema.broadsoft.com/xsi\">' \
                  f'<event>{self.event_package}</event>' \
                  f'<expires>7200</expires><channelSetId>{self.parent.id}</channelSetId>' \
                  f'<applicationId>{self.parent.parent.application_id}</applicationId></Subscription>'
        r = requests.post(self.events_endpoint + f"/v2.0/serviceprovider/{self.parent.parent.enterprise}",
                          headers=self._headers, data=payload)
        if r.ok:
            response_dict = xmltodict.parse(r.text)
            self.id = response_dict['Subscription']['subscriptionId']
            logging.debug(f"Subscription ID: {self.id}")

    def _refresh_subscription(self):
        payload = "<Subscription xmlns=\"http://schema.broadsoft.com/xsi\"><expires>7200</expires></Subscription>"
        r = requests.put(self.events_endpoint + f"/v2.0/subscription/{self.id}",
                         headers=self._headers, data=payload)
        if r.ok:
            logging.debug("Subscription refresh succeeded")
            return True
        else:
            logging.debug(f"Subscription refresh failed: {r.text}")
            return False


class XSIEventsChannel:
    def __init__(self, parent: XSIEventsChannelSet, endpoint: str, events_endpoint: str):
        self.parent = parent
        self._headers = self.parent.parent._headers
        self.id = ""
        self.endpoint = endpoint
        self.events_endpoint = events_endpoint
        self.queue = self.parent.queue
        self.active = True
        self.last_refresh = ""

    def channel_daemon(self):
        payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
                  '<Channel xmlns=\"http://schema.broadsoft.com/xsi\">' \
                  f'<channelSetId>{self.parent.id}</channelSetId>' \
                  '<priority>1</priority>' \
                  '<weight>50</weight>' \
                  '<expires>7200</expires>' \
                  f'<applicationId>{self.parent.parent.application_id}</applicationId>' \
                  '</Channel>'

        logging.debug("Sending Channel Start Request (Streaming)")
        r = requests.post(
            f"{self.endpoint}/v2.0/channel",
            headers=self._headers, data=payload, stream=True)
        # Get the real IP of the remote server so we can send subsequent messages to that
        ip, port = r.raw._connection.sock.getpeername()
        logging.debug(f"Received response from {ip}.")
        self.xsp_ip = str(ip)
        chars = ""
        self.last_refresh = time.time()
        for char in r.iter_content():
            decoded_char = char.decode('utf-8')
            chars += decoded_char
            # logging.info(chars)
            if "</Channel>" in chars:
                m = re.search("<channelId>(.+)<\/channelId>", chars)
                self.id = m.group(1)
                chars = ""
            if "<ChannelHeartBeat xmlns=\"http://schema.broadsoft.com/xsi\"/>" in chars:
                logging.debug("Heartbeat received on channel")
                # Check how long since a channel refresh and refresh if needed
                time_now = time.time()
                if time_now - self.last_refresh >= 3600:
                    logging.debug(f"Refreshing channel: {self.id}")
                    self._refresh_channel()
                    self.last_refresh = time.time()
                # Check any subscriptions and refresh them while we are at it
                for subscription in self.parent.subscriptions:
                    if time_now - subscription.last_refresh >= 3600:
                        logging.debug(f"Refreshing subscription: {subscription.id}")
                        subscription._refresh_subscription()
                        subscription.last_refresh = time.time()
                chars = ""
            if "</xsi:Event>" in chars:
                event = chars
                logging.debug(f"Full Event: {event}")
                message_dict = xmltodict.parse(event)
                self.parent.queue.put(message_dict)
                # Reset ready for new message
                chars = ""
                self._ack_event(message_dict['xsi:Event']['xsi:eventID'], r.cookies)
            if decoded_char == "\n":
                # Discard this for now
                # logging.debug(f"Discard Line: {chars}")
                chars = ""
        logging.debug("Channel loop ended")

    def heartbeat_daemon(self):
        session = requests.Session()
        while self.active:
            logging.debug(f"Sending heartbeat for channel: {self.id}")
            r = session.put(self.events_endpoint + f"/v2.0/channel/{self.id}/heartbeat",
                            headers=self._headers, stream=True)
            ip, port = r.raw._connection.sock.getpeername()
            if r.ok:
                logging.debug(f"{ip} - Heartbeat successful")
            else:
                logging.debug(f"{ip} - Heartbeat failed: {r.text} [{r.status_code}]")
            # Send a heartbeat every 15 seconds
            time.sleep(15)
        return True

    def _ack_event(self, event_id, cookies):
        payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
                  '<EventResponse xmlns=\"http://schema.broadsoft.com/xsi\">' \
                  f'<eventID>{event_id}</eventID>' \
                  '<statusCode>200</statusCode>' \
                  '<reason>OK</reason>' \
                  '</EventResponse>'
        logging.debug(f"Acking event: {event_id}")
        r = requests.post(self.events_endpoint + "/v2.0/channel/eventresponse",
                          headers=self._headers, data=payload, cookies=cookies)
        return True

    def _refresh_channel(self):
        payload = "<Channel xmlns=\"http://schema.broadsoft.com/xsi\"><expires>7200</expires></Channel>"
        r = requests.put(self.events_endpoint + f"/v2.0/channel/{self.id}",
                         headers=self._headers, data=payload)
        if r.ok:
            logging.debug("Channel refresh succeeded")
            return True
        else:
            logging.debug(f"Channel refresh failed: {r.text}")
            return False


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
        """Initialize a HuntGroup instance

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
        self.location_id: str = location
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
            logging.info(f"Getting config for Hunt Group {self.id} in Location {self.location_id}")
            self.get_config()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def get_config(self):
        """Get the Hunt Group config, including agents"""
        r = requests.get(_url_base + f"v1/telephony/config/locations/{self.location_id}/huntGroups/{self.id}",
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
        """Inititalize a Call instance for a Person

        Args:
            parent (XSI): The Person or XSI instance that owns this Call
            id (str, optional): The Call ID of a known call. Usually only done during a XSI.calls method
            address (str, optional): The address to originate a call to when the instance is created

        Returns:
            Call: This Call instance

        """
        self._parent = parent
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
            self.type = "Person"
            pass
        elif type(self._parent) is XSICallQueue:
            self._url = self._parent.org.xsi['actions_endpoint'] + f"/v2.0/callcenter/{self._userid}/calls"
            self.type = "CallQueue"
        elif type(self._parent) is XSI:
            # The Call parent is XSI
            self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls"
            self.type = "XSI"
        elif type(self._parent) is Call:
            # Another Call created this Call instance (probably for a transfer or conference
            self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._parent._userid}/calls"
            self.type = "Call"

        if address:
            self.originate(address)

    def originate(self, address: str, comment: str = "", executive: str = None):
        """Originate a call on behalf of the Person

        The optional ``executive`` argument takes an extension or phone number and allows the call to be placed
        on behalf of an executive to which the Person is assigned as an executive assistant. If the Exectuve call is
        not allowed by the system, an :exc:`NotAllowed` is raised.

        Args:
            address (str): The address (usually a phone number) to originate the call to
            comment (str, optional): Text comment to attach to the call
            executive (str, optional): The phone number or extension of the Executive to place the call on behalf of

        Returns:
            bool: True when the call was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the Person is not able to place the call for an Executive

        """
        if executive is not None:
            logging.info(f"Originating a call to {address} for {self._userid} on behalf of Exec {executive}")
            # TODO: The API call will fail if the Assistant can't place the call for the Exec, but we should
            #   really check that first and not waste the API call (although those take API calls, too)
            params = {"address": address, "executiveAddress": executive}
            r = requests.post(self._url + "/ExecutiveAssistantInitiateCall", headers=self._headers, params=params)
            if r.status_code == 201:
                response = r.json()
                self.id = response['CallStartInfo']['callId']['$']
                self._external_tracking_id = response['CallStartInfo']['externalTrackingId']['$']
                return True
            else:
                raise NotAllowed("Person is not allowed to place calls on behalf of this executive")
        else:
            logging.info(f"Originating a call to {address} for {self._userid}")
            params = {"address": address, "info": comment}
            r = requests.post(self._url + "/new", headers=self._headers, params=params)
            if r.status_code == 201:
                response = r.json()
                self.id = response['CallStartInfo']['callId']['$']
                self._external_tracking_id = response['CallStartInfo']['externalTrackingId']['$']
                return True
            else:
                return False

    def exec_push(self):
        """Pushes the active Executive Assistant call to the Executive

        This method will only complete if the following conditions are met:
        * The user is an Assistant
        * The call must be active and answered

        Returns:
            bool: True if the push was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the call does not meet the conditions to be pushed

        """
        r = requests.put(self._url + f"/{self.id}/ExecutiveAssistantCallPush", headers=self._headers)
        if r.status_code == 200:
            return True
        else:
            raise NotAllowed("The call cannot be pushed")

    def hangup(self):
        """Hang up the call

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
        """The status of the call

        Returns:
            dict::

                {
                'network_call_id' (str): The unique identifier for the Network side of the call
                'personality'(str): The user personalty (Originator or Terminator)
                'state' (str): The state of the call
                'remote_party' (dict): {
                    'address' (str): The address of the remote party
                    'call_type' (str): The call type
                    }
                'endpoint' (dict): {
                    'type' (str): The type of endpoint being used
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
        """Transfer the call to the selected address.

        Type of transfer can be controlled with `type` param. VM transfers will transfer the call directly to the voice
        mail of the address, even if the address is the user's own address. Attended transfers require a subsequent call
        to `finish_transfer()` when the actual transfer should happen.

        Args:
            address (str): The address (usually a phone number or extension) to transfer the call to
            type (str): ['blind','vm','attended']:
                The type of transfer.

        Returns:
            bool: True if successful. False if unsuccessful

        """
        logging.info(f"Transferring call {self.id} to {address} for {self._userid}")
        # Set the address param to be passed to XSI
        if self.type == "CallQueue":
            params = {"phoneno": address}
        else:
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
                logging.debug(f"Transfer request {r.request.url}")
                raise APIError(f"The Transfer call failed: {r.text}")

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
        """Transmit DTMF tones outbound

        Args:
            dtmf (str): The string of dtmf digits to send. Accepted digits 0-9, star, pound. A comma will pause
                between digits (i.e. "23456#,123")

        Returns:
            bool: True if the dtmf was sent successfully
        """
        params = {"playdtmf": str(dtmf)}
        r = requests.put(self._url + f"/{self.id}/TransmitDTMF", headers=self._headers, params=params)
        if r.status_code in [200, 201, 204]:
            return True
        else:
            return False, r.text

    def hold(self):
        """Place the call on hold

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

    def park(self, extension: str = None):
        """Park the call

        When called with the ``extension`` argument, the call will be parked using the Call Park Extension feature at
        the chosen extension. When called without ``extension``, the call will be parked with the Group Call Park
        feature, which assigns an extension automatically. Note that Group Call Park requires the Person to be part
        of the Park Group. If a Group Call Park is attemped for a user that isn't park of a Park Group, a
        :exc:`NotAllowed` exception will be raised.

        Args:
            extension (str, optional): The extension to park the call against

        Returns:
            str: The extension that the call is parked against

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the user is not part of a Park Group or the extension is already busy

        """
        if extension is None:
            r = requests.put(self._url + f"/{self.id}/GroupCallPark", headers=self._headers)
            if r.status_code == 200:
                self._park_location = r.headers['Content-Location']
                self._park_address = self._park_location.split("?")[-1]
                self._park_extension = self._park_address.split(":")[-1]
                return self._park_extension
            else:
                raise NotAllowed("The call cannot be parked")
        else:
            params = {"address": extension}
            r = requests.put(self._url + f"/{self.id}/Park", headers=self._headers, params=params)
            if r.status_code == 200:
                self._park_location = r.headers['Content-Location']
                self._park_address = self._park_location.split("?")[-1]
                self._park_extension = self._park_address.split(":")[-1]
                return self._park_extension
            else:
                raise NotAllowed("The call cannot be parked")

    def reconnect(self):
        """Retrieves the call from hold **and releases all other calls**"""
        r = requests.put(self._url + f"{self.id}/Reconnect", headers=self._headers)
        if r.ok:
            return True
        else:
            return NotAllowed("The reconnect failed")

    def recording(self, action: str):
        """Control the recording of the call

        For the recording() method to work, the user must have Call Recording enabled. Any unsuccessful attempt to
        record a call for a user who is not enabled for Call Recording will raise a NotAllowed exception.

        Args:
            action (str): The action to perform.

                'start': Starts recording, if it isn't in process already

                'stop': Stops the recording. Only applies to On Demand call recording.

                'pause': Pauses the recording

                'resume': Resume a paused recording

        Returns:
            bool: True if the recording command was accepted by the server

        Raises:
            wxcadm.exceptions.NotAllowed: The action is not allowed. Normally it indicates that the user does not have
                the Call Recording service assigned.
            ValueError: Raised when the action is not recognized.

        """

        if action.lower() == "start":
            r = requests.put(self._url + f"{self.id}/Record", headers=self._headers)
        elif action.lower() == "resume":
            r = requests.put(self._url + f"{self.id}/ResumeRecording", headers=self._headers)
        elif action.lower() == "stop":
            r = requests.put(self._url + f"{self.id}/StopRecording", headers=self._headers)
        elif action.lower() == "resume":
            r = requests.put(self._url + f"{self.id}/PauseRecording", headers=self._headers)
        else:
            raise ValueError(f"{action} is not a valid action")

        if r.ok:
            return True
        else:
            raise NotAllowed(f"The {action} action was not successful: {r.text}")


class Conference:
    """The class for Conference Calls started by a Call.conference()"""

    def __init__(self, parent: object, calls: list, comment: str = ""):
        """Initialize a Conference instance for an XSI instance

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
        self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls/Conference/"
        self.comment: str = comment
        """Text comment associated with the Conference"""

    def deaf(self, call: str):
        """Stop audio and video from being sent to a participant. Audio and video from that participant are unaffected.

        Args:
            call (str): The Call ID to make deaf. The Call ID must be part of the Conference.

        Returns:
            bool: True if the command was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the server rejects the command

        """
        r = requests.put(self._url + f"{call}/Deaf", headers=self._headers)
        if r.ok:
            return True
        else:
            raise NotAllowed(f"The deaf command was rejected by the server: {r.text}")

    def mute(self, call: str):
        """Mute a conference participant. Audio and video sent to the participant are unaffected.

        Args:
            call (str): The Call ID to mute. The Call ID must be part of the Conference

        Returns:
            bool: True if the command was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the server rejects the command

        """
        r = requests.put(self._url + f"{call}/Mute", headers=self._headers)
        if r.ok:
            return True
        else:
            raise NotAllowed(f"The mute command was rejected by the server: {r.text}")


class Workspace:
    def __init__(self, parent: Org, id: str, config: dict = None):
        """Initialize a Workspace instance

        If only the `id` is provided, the configuration will be fetched from
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
        
            'freeCalling': Free Calling
            'hybridCalling': Hybrid Calling
            'webexCalling': Webex Calling
            'webexEdgeForDevices': Webex Edge for Devices
        """
        self.calendar: dict = None
        """The type of calendar connector assigned to the Workspace"""
        self.notes: str = None
        """Notes associated with the Workspace"""

        if config:
            self.__process_config(config)
        else:
            self.get_config()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def spark_id(self):
        bytes = base64.b64decode(self.id + "===")
        spark_id = bytes.decode("utf-8")
        return spark_id

    def get_config(self):
        """Get (or refresh) the confirmation of the Workspace from the Webex API"""
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
        """Initialize a WorkspaceLocation instance.

        If only the `id` is provided, the configuration will be fetched from
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
        """Initialize a new WorkspaceLocationFloor

        Args:
            config (dict): The config as returned by the Webex API

        """
        self.name = config.get("displayName")
        self.id = config.get("id")
        self.floor = config.get("floorNumber")


class CPAPI:
    """The CPAPI class handles API calls using the CP-API, which is the native API used by Webex Control Hub."""

    def __init__(self, org: Org, access_token: str):
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the "customer" ID from the Org ID
        org_id_bytes = base64.b64decode(org.id + "===")
        org_id_decoded = org_id_bytes.decode("utf-8")
        self._customer = org_id_decoded.split("/")[-1]

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
        logging.info("Setting Org-wide default VM PIN")
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
        logging.info("Clearing Org-wide default VM PIN")
        payload = {
            "defaultVoicemailPinEnabled": False,
        }
        r = requests.patch(self._url_base + f"features/voicemail/rules",
                           headers=self._headers, json=payload)
        return r.text

    def reset_vm_pin(self, person: Person, pin: str = None):
        logging.info(f"Resetting VM PIN for {person.email}")
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
        logging.info("CPAPI - Getting Calling Location")
        r = requests.get(self._url_base + f"places/{workspace_id}", headers=self._headers)
        if r.status_code == 200:
            response = r.json()
            location = self._parent.get_location_by_name(response['location']['name'])
        elif r.status_code == 403:
            raise TokenError("Your API Access Token doesn't have permission to use this API call")
        else:
            raise APIError("Something went wrong getting the Workspace Calling Location")
        return location


class Terminus:
    """The Terminus class handles API calls using the Terminus API."""

    def __init__(self, org: Org, access_token: str):
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the "customer" ID from the Org ID
        org_id_bytes = base64.b64decode(org.id + "===")
        org_id_decoded = org_id_bytes.decode("utf-8")
        self._customer = org_id_decoded.split("/")[-1]

        self._url_base = f"https://terminus.huron-dev.com/api/v2/customers/{self._customer}/"
        self._server = "https://terminus.huron-dev.com"

    def get_locations(self):
        logging.info("Getting locations from Terminus")
        r = requests.get(self._url_base + "locations", headers=self._headers)
        if r.ok:
            locations = r.json()
            for location in locations:
                webex_location = self._parent.get_location_by_name(location['name'])
                webex_location.terminus_config = location
            return locations
        else:
            raise APIError("Your API Access Token does not have permission to get the locations from Terminus.")


class Bifrost:
    """The Bifrost class handles API calls using the Bifrost API."""

    def __init__(self, org: Org, access_token: str):
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the "customer" ID from the Org ID
        org_id_bytes = base64.b64decode(org.id + "===")
        org_id_decoded = org_id_bytes.decode("utf-8")
        self._customer = org_id_decoded.split("/")[-1]

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
                webex_location = self._parent.get_location_by_name(location['name'])
                webex_location.bifrost_config = location
        return locations



class CSDM:
    """The base class for dealing with devices"""
    def __init__(self, org: Org, access_token: str):
        """ Initialize a CSDM instance for an :class:`Org`

        Args:
            org (Org): The Org instance which is the parent of this CSDM instance
            access_token (str): The API Access Token that is used to access the CSDM API. Usually the same access
                token that is used by the Org
        """

        logging.info("Initializing CSDM instance")
        self._parent = org
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

        # Calculate the CSDM "organization" ID from the Org ID
        org_id_bytes = base64.b64decode(org.id + "===")
        org_id_decoded = org_id_bytes.decode("utf-8")
        self._organization = org_id_decoded.split("/")[-1]

        self._url_base = f"https://csdm-a.wbx2.com/csdm/api/v1/organization/{self._organization}/devices/"
        self._server = "https://csdm-a.wbx2.com"

        self._devices: list[Device] = []

    def get_devices(self, with_location: bool = False):
        """ Get a list of all the Device instances from CSDM

        Args:
            with_location (bool, optional): Whether to populate the .location attribute with the Webex Calling
                :class:`Location` instance. The API calls to do this take some time, so it defaults to **False**.

        Returns:
            list[Device]: A list of all the :class:`Device` instances

        """
        logging.info("Getting devices from CSDM")
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
            logging.debug(f"Received {len(response['hits']['hits'])} devices out of {response['hits']['total']}")
            devices_from_csdm.extend(response['hits']['hits'])
            # If the total number of devices is greater than what we received, we need to make the call again
            keep_going = True
            while keep_going:
                if len(devices_from_csdm) < response['hits']['total']:
                    logging.debug("Getting more devices")
                    payload['from'] = len(devices_from_csdm)
                    r = requests.post(self._url_base + "_search", headers=self._headers, json=payload)
                    if r.ok:
                        response = r.json()
                        logging.debug(f"Received {len(response['hits']['hits'])} more devices")
                        devices_from_csdm.extend(response['hits']['hits'])
                    else:
                        logging.error("Failed getting more devices")
                        raise CSDMError("Error getting more devices")
                else:
                    keep_going = False
        else:
            logging.error(("Failed getting devices"))
            raise CSDMError("Error getting devices")

        self._devices = []
        logging.debug("Creating Device instances")
        for device in devices_from_csdm:
            this_device = Device(self, device)
            if with_location is True:
                # Get the device location with another search via CPAPI
                logging.debug(f"Getting Device Location via CPAPI: {this_device.display_name}")
                if "ownerId" in device:
                    device_location: Location = self._parent._cpapi.get_workspace_calling_location(device['ownerId'])
                    logging.debug(f"\tLocation: {device_location.name}")
                    this_device.calling_location = device_location
            self._devices.append(this_device)

        return self._devices


class Device:
    """The Device class holds device information, currently only available with CSDM."""
    def __init__(self, parent: CSDM, config: dict):
        self._parent = parent
        self.display_name: str = config.get("displayName", "")
        """The display name associated with the device"""
        self.uuid: str = config.get("cisUuid", "")
        """The Cisco UUID associated with the device"""
        self.account_type: str = config.get("accountType", "UNKNOWN")
        """The type of account the device is associated with"""
        self.url: str = config.get("url", "")
        """The URL to access the CSDM API for the device"""
        self.created: str = config.get("createTime", "")
        """The timestamp when the device was added"""
        self.serial: str = config.get("serial", "")
        """The serial number of the device"""
        self.product: str = config.get("product", "")
        """The product name"""
        self.type: str = config.get("type", "")
        """The type of device"""
        self.last_seen: str = config.get("lastKnownOnline", "UNKNOWN")
        """The last time the device was seen online"""
        self.owner_id: str = config.get("ownerId", "UNKNOWN")
        """The Spark ID of the device owner"""
        self.owner_name: str = config.get("ownerDisplayName", "UNKNOWN")
        """The display name of the device owner"""
        self.calling_type: str = config.get("callingType", "UNKNOWN")
        """The type of Calling the device is licensed for"""
        self.usage_mode: str = config.get("usageMode", "UNKNOWN")
        """The usage mode the device is operating in"""
        self.status: str = config.get("connectionStatus", "UNKNONW")
        """Real-time status information"""
        self.category: str = config.get("category", "UNKNOWN")
        """The device category"""
        self.product_family: str = config.get("productFamily", "UNKNOWN")
        """The product family to which the device belongs"""
        self.mac: str = config.get("mac", "UNKNOWN")
        """The MAC address of the device"""
        self._calling_location: Location = ""
        """The Webex Calling :class:`Location`"""
        self._image: str = config.get("imageFilename", None)

    def __str__(self):
        return f"{self.product},{self.display_name}"

    @property
    def calling_location(self):
        """ The :class:`Location` instance that the device is assigned to"""
        if not self._calling_location:
            location = self._parent._parent._cpapi.get_workspace_calling_location(self.owner_id)
            self._calling_location = location
        return self._calling_location

    @calling_location.setter
    def calling_location(self, location: Location):
        if isinstance(location, Location):
            self._calling_location = location

    def refresh(self):
        """Refresh the information about this device (including status) from CSDM"""
        r = requests.get(self.url, headers=self._parent._headers)
        if r.ok:
            response = r.json()
            return response
        else:
            raise CSDMError("Unable to refresh device status")

    def change_workspace_caller_id(self, name: str, number: str):
        """ Change the Caller ID for a Workspace

        For most cases, the ``name`` and ``number`` arguments will be special keywords to specify either the DID
        (Direct Line) or the Location Number as the Caller ID.

        Args:
            name (str): Acceptable values are 'DIRECT_LINE' and 'LOCATION'
            number (str): Acceptable values are 'DIRECT_LINE' and 'LOCATION_NUMBER'

        Returns:
            bool: True if successful. False otherwise

        """
        cpapi = self._parent._parent._cpapi
        if cpapi.change_workspace_caller_id(self.owner_id, name=name, number=number):
            return True
        else:
            return CSDMError("Not able to set Caller ID for Workspace")


class RedSky:
    def __init__(self, username: str, password: str):
        """ Initialize a connection to RedSky and obtain basic account info

        Args:
            username (str): The Horizon admin username
            password (str): The Horizon admin password

        """
        # Log into Horizon and get access token info
        payload = {"username": username, "password": password}
        r = requests.post("https://api.wxc.e911cloud.com/auth-service/login", json=payload)
        if r.ok:
            response = r.json()
        else:
            raise APIError("Cannot log into RedSky Horizon")
        self._access_token = response['accessToken']
        self.org_id = response['userProfileTO']['company']['id']
        self._refresh_token = response['refreshTokenInfo']['id']
        self._full_config = response
        self._buildings = []

    @property
    def _headers(self):
        headers = {"Authorization": "Bearer " + self._access_token}
        return headers

    def _token_refresh(self):
        """A method to refresh the access_toke using the stored refresh_token"""
        r = requests.post("https://api.wxc.e911cloud.com/auth-service/token/refresh",
                          headers=self._headers,
                          json=self._refresh_token)
        if r.status_code == 200:
            response = r.json()
            self._access_token = response['accessToken']
            self._refresh_token = response['refreshTokenInfo']['id']
        else:
            raise APIError("There was an error refreshing the RedSky token")

    @property
    def buildings(self):
        """A list of all of the RedSkyBuilding instances within this RedSky account

        Returns:
            list[RedSkyBuilding]: The RedSkyBuilding instances

        """
        params = {"page": 1,
                  "pageSize": 100,
                  "searchTerm": None,
                  "origin": "default"}
        self._buildings = []

        r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/buildings/parent/{self.org_id}",
                         params=params, headers=self._headers)
        if r.status_code == 401:
            if r.status_code == 401:
                self._token_refresh()
                r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/buildings/parent/{self.org_id}",
                                 headers=self._headers, params=params)
        if r.status_code == 200:
            response = r.json()
            for item in response:
                building = RedSkyBuilding(self, item)
                self._buildings.append(building)
        else:
            raise APIError("Something went wrong getting the list of buildings")

        return self._buildings

    def get_building_by_name(self, name: str):
        """Get the RedSkyBuilding instance for a given name

        Args:
            name (str): The name of the Building to return. Not case sensitive.

        Returns:
            RedSkyBuilding: The instance of the RedSkyBuilding class. None is returned if no match is found.

        """
        for building in self.buildings:
            if building.name.lower() == name.lower():
                return building

        return None

    def get_building_by_webex_location(self, location: Location):
        """Get the RedSkyBuilding instance for a given Location instance.

        This method will first try to match on the Location ID in Webex, which will work if the Building was created
        by ***wxcadm**. If no match is found, it will attempt to match on the Location Name. The Webex Location name and
        the RedSky Building name must match exactly, although case is ignored.

        Args:
            location (Location): The Location instance to search against.

        Returns:
            RedSkyBuilding: The instance of the RedSkyBuilding class. None is returned if no match is found.

        """
        buildings = self.buildings
        for building in buildings:
            if building.supplemental_data == location.id[-20:]:
                return building
        for building in buildings:
            if building.name.lower() == location.name.lower():
                return building
        return None

    def add_building(self, webex_location: Location, create_location: bool = True):
        """ Add a new Building to RedSky

        The ``create_location`` arg defaults to True, which will automatically create a RedSkyLocation called "Default".
        If you want to prevent a Location from being created, pass ``create_location=False``.

        Args:
            webex_location (Location): The Webex Location instance to create the building for
            create_location (bool. optional: Whether to create a RedSkyLocation called "Default" in the RedSkyBuilding

        Returns:
            RedSkyBuilding: The RedSkyBulding instance that was created

        Raises:
            ValueError: Raised when trying to create a RedSkyBuilding for a Location that is not in the U.S.
            wxcadm.exceptions.APIError: Raised on all API failures

        """
        if webex_location.address['country'] != "US":
            raise ValueError("Cannot create Building for non-US location")

        a1 = webex_location.address['address1']
        a2 = webex_location.address.get("address2", "")
        city = webex_location.address['city']
        state = webex_location.address['state']
        zip = webex_location.address['postalCode']
        full_address = f"{a1} {a2}, {city}, {state} {zip}"

        payload = {"name": webex_location.name,
                   "supplementalData": webex_location.id[-20:],
                   "parentOrganizationUnitId": self.org_id,
                   "fullAddress": full_address,
                   "origin": "default"
                   }
        print(payload)
        r = requests.post("https://api.wxc.e911cloud.com/geography-service/buildings",
                          headers=self._headers, json=payload)
        if r.ok:
            building = self.get_building_by_webex_location(webex_location)
            if create_location is True:
                building = self.get_building_by_webex_location(webex_location)
                if building is not None:
                    building.add_location("Default", ecbn=webex_location.main_number.replace("+1", ""))
                else:
                    raise APIError("The created Building cannot be located. Location not created.")
            return building
        else:
            raise APIError(f"Something went wrong adding Building: {r.text}")

    @property
    def held_devices(self):
        """All of the HELD devices known to RedSky"""
        params = {"page": 1,
                  "pageSize": 100,
                  "searchTerm": None,
                  "type": None}
        r = requests.get(f"https://api.wxc.e911cloud.com/admin-service/held/org/{self.org_id}",
                         headers=self._headers, params=params)
        if r.status_code == 401:
            self._token_refresh()
            r = requests.get(f"https://api.wxc.e911cloud.com/admin-service/held/org/{self.org_id}",
                             headers=self._headers, params=params)
        if r.status_code == 200:
            self._held_devices = []
            response = r.json()
            print(response)
            for device in response:
                self._held_devices.append(device)
        else:
            raise APIError(f"Something went wrong getting the HELD devices {r.text}")

        return self._held_devices

    def phones_without_location(self):
        """Get a list of phone (HELD) devices that don't have a RedSkyLocation associated

        Returns:
            list[dist]: A list of the device properties from RedSky

        """
        devices = []
        for device in self.held_devices:
            if device['erl'] is None and device['deviceType'] == "HELD":
                devices.append(device)
        return devices

    def clients_without_location(self):
        """Get a list of soft client (HELD+) devices that don't have a RedSkyLocation associated

        Returns:
            list[dict]: A list of the device properties from RedSky

        """
        devices = []
        for device in self.held_devices:
            if device['erl'] is None and device['deviceType'] == "HELD_PLUS":
                devices.append(device)
        return devices

    def get_mac_discovery(self):
        """ Get the current MAC address mapping defined in RedSky Horizon

        Returns:
            list[dict]: A list of all the MAC address mappings

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/macAddress/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting MAC mapping: {r.text}")
        return mappings

    def add_mac_discovery(self, mac: str, location: "RedSkyLocation", description: str = ""):
        """ Add a new MAC address mapping to RedSky Horizon

        Args:
            mac (str): The MAC address to add. RedSky isn't picky about formatting or case, so any MAC format should work
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        payload = {"macAddress": mac,
                   "locationId": location.id,
                   "orgId": self.org_id,
                   "description": description}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/macAddress",
                          headers=self._headers, json=payload)
        if r.ok:
            added_mapping = r.json()
        else:
            raise APIError(f"There was a problem adding the mapping: {r.text}")
        return added_mapping

    def get_lldp_discovery(self):
        """ Get the current LLDP chassis and port mappings defined in RedSky Horizon

        Returns:
            list[dict]: A list of all the LLDP mappings

        Raises:
            APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/networkSwitch/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                item['ports'] = []
                r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/networkSwitchPort/networkSwitch/{item['id']}",
                                 headers=self._headers)
                if r.ok:
                    ports = r.json()
                    for port in ports:
                        item['ports'].append(port)
                else:
                    raise APIError(f"There was a problem getting Chassis Ports: {r.text}")
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting Chassis mapping: {r.text}")
        return mappings

    def add_lldp_discovery(self, chassis: str, location: "RedSkyLocation", ports: list = None, description: str = ""):
        """ Add a new LLDP mapping to RedSky Horizon

        If only a chassis identifier is provided, the chassis will be added. If a list of ports are provided, the method
        will determine if the chassis already exists. If it does, the ports will be added and the chassis mapping will
        not be changed. If the chassis does not exist, it will be added and mapped to the provided RedSkyLocation, and
        the list of ports will be added, mapped to the same RedSkyLocation.

        Args:
            chassis (str): The chassis identifier
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            ports (list, optional): A list of ports (i.e. ['1','2','3'] or ['B000B4BB1BF4:P1'] to add mapping for
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        if ports is not None:
            # Determine if the chassis already exists
            chassis_exists = False
            chassis_id = ""
            current_lldp = self.get_lldp_discovery()
            for entry in current_lldp:
                if entry['chassisId'].lower() == chassis.lower():
                    chassis_id = entry['id']
                    chassis_exists = True
            if chassis_exists is False:
                new_chassis = self._add_chassis_discovery(chassis, location, description)
                chassis_id = new_chassis['id']
            for port in ports:
                self._add_port_discovery(chassis_id, port, location, description)

            # Now that we added everything, let's get the details of the new chassis and its ports
            current_lldp = self.get_lldp_discovery()
            for entry in current_lldp:
                if entry['chassisId'].lower == chassis.lower():
                    return entry
            raise APIError("Something went wrong addind the LLDP mapping")
        else:
            new_chassis = self._add_chassis_discovery(chassis, location, description)
            return new_chassis

    def _add_chassis_discovery(self, chassis, location, description=""):
        payload = {"chassisId": chassis,
                   "companyId": self.org_id,
                   "locationId": location.id,
                   "description": description}
        r = requests.post("https://api.wxc.e911cloud.com/networking-service/networkSwitch",
                          headers=self._headers, json=payload)
        if r.ok:
            response = r.json()
        else:
            raise APIError(f"There was a problem adding the chassis: {r.text}")
        return response

    def _add_port_discovery(self, chassis_id, port, location, description=""):
        payload = {"erlId": location.id,
                   "portId": port,
                   "description": description,
                   "networkSwitchId": chassis_id}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/networkSwitchPort",
                          headers=self._headers, json=payload)
        if r.ok:
            respose = r.json()
        else:
            raise APIError(f"There was a problem adding the port to the chassis: {r.text}")
        return respose


    def get_bssid_discovery(self):
        """ Get the current BSSID mappings defined in RedSky Horizon

        Returns:
            list[dict]: A list of all the BSSID mappings

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/bssid/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting BSSID mapping: {r.text}")
        return mappings

    def add_bssid_discovery(self, bssid:str, location:"RedSkyLocation", description:str = ""):
        """ Add a new BSSID mapping to RedSky Horizon

        Args:
            bssid (str): The BSSID to add. RedSky isn't picky about formatting or case, so any MAC format should work
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        payload = {"bssid": bssid,
                   "locationId": location.id,
                   "orgId": self.org_id,
                   "description": description}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/bssid",
                          headers=self._headers, json=payload)
        if r.ok:
            added_mapping = r.json()
        else:
            raise APIError(f"There was a problem adding the mapping: {r.text}")
        return added_mapping

    def get_ip_range_discovery(self):
        """ Get the current IP Range mappings defined inRedSky Horizon

        Returns:
            list[dict]: A list of all the IP Range mappings

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        mappings = []
        r = requests.get(f"https://api.wxc.e911cloud.com/networking-service/ipRange/company/{self.org_id}",
                         headers=self._headers)
        if r.ok:
            response = r.json()
            for item in response:
                mappings.append(item)
        else:
            raise APIError(f"There was a problem getting IP Range mapping: {r.text}")
        return mappings

    def add_ip_range_discovery(self, ip_start:str, ip_end:str, location:"RedSkyLocation", description:str = ""):
        """ Add a new IP Range mapping to RedSky Horizon

        Args:
            ip_start (str): The first IP in the range to add
            ip_end (str): The last IP in the range to add
            location (RedSkyLocation): The RedSkyLocation instance to add the mapping to
            description (str, optional): A description of the device or any other information to store

        Returns:
            dict: The configuration of the mapping after processing by RedSky

        Raises:
            wxcadm.exceptions.APIError: Raised on any error from the RedSKy API

        """
        payload = {"ipAddressLow": ip_start,
                   "ipAddressHigh": ip_end,
                   "locationId": location.id,
                   "orgId": self.org_id,
                   "description": description}
        r = requests.post(f"https://api.wxc.e911cloud.com/networking-service/ipRange",
                          headers=self._headers, json=payload)
        if r.ok:
            added_mapping = r.json()
        else:
            raise APIError(f"There was a problem adding the mapping: {r.text}")
        return added_mapping



class RedSkyBuilding:
    """A RedSky Horizon Building"""
    def __init__(self, parent: RedSky, config: dict):
        """Initialize a RedSkyBuilding instance.

        Args:
            parent (RedSky): The RedSky instance that this Building belongs to
            config: (dict): The dict returned by the RedSky API containing the Building information

        """
        self._parent:RedSky = parent
        self._raw_config:dict = config
        self.id:str = config.get("id")
        """The ID of the Building"""
        self.name:str = config.get("name")
        """The name of the Building"""
        self.supplemental_data:str = config.get("supplementalData", None)
        """Supplemental data for the Building"""
        self.type:str = config.get("type", "unknown")
        """The type of Building"""
        self.address:dict = config.get("address")
        """The physical address of the building"""
        self._locations: list = None

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def locations(self):
        """A list of RedSkyLocation instances associated with this Building

        Returns:
            list[RedSkyLocation]: List of RedSkyLocation instances

        """
        self._locations = []
        r = requests.get(f"https://api.wxc.e911cloud.com/geography-service/locations/parent/{self.id}",
                         headers=self._parent._headers)
        if r.status_code == 200:
            response = r.json()
            for item in response:
                location = RedSkyLocation(self, item)
                self._locations.append(location)
        else:
            raise APIError(f"There was a problem getting the Locations for Building {self.name}")
        return self._locations

    def get_location_by_name(self, name: str):
        """ Return the RedSkyLocation instance that matches the name provided.

        Args:
            name (str): The name of the location to search for. Not case-sensitive

        Returns:
            RedSkyLocation: The instance of the RedSkyLocation class. None is returned if no match can be found

        """
        for location in self.locations:
            if location.name.lower() == name.lower():
                return location
        return None


    def add_location(self, location_name:str, ecbn:str = "", location_info: str = ""):
        payload = {"name": location_name,
                   "elin": ecbn,
                   "info": location_info,
                   "organizationUnitId": self.id}
        r = requests.post("https://api.wxc.e911cloud.com/geography-service/locations",
                          headers=self._parent._headers, json=payload)
        if r.ok:
            return True
        else:
            raise APIError("Something went wrong adding the Location: {r.text}")


class RedSkyLocation:
    """A RedSky Horizon Location"""
    def __init__(self, parent: RedSkyBuilding, config: dict):
        """Initialize a RedSkyLocation instance

        Args:
            parent (RedSkyBuilding): The RedSkyBuilding instance that this Location belongs to
            config (dict): The dict returned by the RedSky API containing the Location information

        """
        self._parent = parent
        self._raw_config = config
        self.id = config.get("id")
        self.name = config.get("name")
        self.address = config.get("address")
        self.type = config.get("type", "unknown")
        self.suppplemental_data = config.get("supplementalData", None)
        self.org_name_override = config.get("orgNameOverride")
        self.info = config.get("info")
        self.address_entity_name:str = config.get("addressEntityName")
        self.elin:dict = config.get("elin", None)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

from __future__ import annotations

from wxcadm import log, Org
from .common import *
from .location import Location


class Wholesale:
    def __init__(self,
                 access_token: str):
        log.info("Wholesale instance initialized")
        # The access token is the only thing that we need to get started
        self._access_token: str = access_token
        # The Authorization header is going to be used by every API call in the package.
        self._headers: dict = {"Authorization": "Bearer " + access_token}
        log.debug(f"Setting Org._headers to {self._headers}")
        log.debug(f"Setting Global _webex_headers")
        global _webex_headers
        _webex_headers['Authorization'] = "Bearer " + access_token
        self._orgs = None

    @property
    def headers(self):
        """The "universal" HTTP headers with the Authorization header present"""
        return self._headers

    @property
    def customers(self):
        response = webex_api_call('get', '/v1/wholesale/customers')
        customer_list = []
        for customer in response:
            this_customer = WholesaleCustomer(self, customer)
            customer_list.append(this_customer)
        return customer_list

    @property
    def orgs(self):
        if self._orgs is None:
            orgs = []
            for customer in self.customers:
                orgs.append(Org(name=customer.external_id, id=customer.id, parent=self))
            self._orgs = orgs
        return self._orgs

    def get_customer(self, id: str = None, name: str = None, spark_id: str = None):
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        if id is not None:
            for customer in self.customers:
                if customer.id == id:
                    return customer
        if name is not None:
            for customer in self.customers:
                if customer.external_id == name:
                    return customer
        if spark_id is not None:
            for customer in self.customers:
                if customer.spark_id == spark_id:
                    return customer
        return None


class WholesaleCustomer:
    # Eventually, this should probably be a subclass of Org, since they have the same behaviors and attributes
    def __init__(self, partner, customer_data: dict):
        self.id = customer_data.get('id')
        self.org_id = customer_data.get('orgId')
        self.external_id = customer_data.get('externalId')
        self.address = customer_data.get('address')
        self.status = customer_data.get('status')
        self.packages = customer_data.get('packages')
        self.resource_details = customer_data.get('resourceDetails')

        # Set the Authorization header based on how the instance was built
        self._headers = partner.headers

    @property
    def spark_id(self):
        """ The decoded "Spark ID" of the Org ID"""
        return decode_spark_id(self.id)


    @property
    def locations(self):
        locations = []
        params = {"orgId": self.org_id}
        response = webex_api_call('get', '/v1/locations', params=params)
        for location in response:
            this_location = Location(self, location.get('id'), location.get('name'), time_zone=location.get('timeZone'),
                                     preferred_language=location.get('preferredLanguage'),
                                     announcement_language=location.get('announcementLanguage', None))
            locations.append(this_location)
        return locations

    def get_location(self, id: str = None, name: str = None, spark_id: str = None):
        """ Get the Location instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Locations will be
        searched in order by ID, Name, and finally Spark ID. If no arguments are provided, the method will raise an
        Exception.

        Args:
            id (str, optional): The Location ID to find
            name (str, optional): The Location Name to find
            spark_id (str, optional): The Spark ID to find

        Returns:
            Location: The Location instance correlating to the given search argument.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None:
            raise ValueError("A search argument must be provided")
        if id is not None:
            for location in self.locations:
                if location.id == id:
                    return location
        if name is not None:
            for location in self.locations:
                if location.name == name:
                    return location
        if spark_id is not None:
            for location in self.locations:
                if location.spark_id == spark_id:
                    return location
        return None

    def add_subscriber(self,
                      email: str,
                      package: str,
                      first_name: str,
                      last_name: str,
                      phone_number: str,
                      extension: str,
                      location: Location):
        payload = {
            'customerId': self.id,
            'email': email,
            'package': package,
            'provisioningParameters': {
                'firstName': first_name,
                'lastName': last_name,
                'primaryPhoneNumber': phone_number,
                'extension': extension,
                'locationId': location.id
            }
        }
        response = webex_api_call('post', '/v1/wholesale/subscribers', payload=payload)
        return response


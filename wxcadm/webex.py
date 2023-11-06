from __future__ import annotations

import requests
from typing import Optional, Type

import wxcadm.person
from wxcadm import log
from .common import *
from .exceptions import *
from .org import Org
from .person import Me, Person


class Webex:
    """The base class for working with wxcadm"""
    def __init__(self,
                 access_token: str,
                 get_locations: bool = True,
                 get_xsi: bool = False,
                 get_hunt_groups: bool = False,
                 get_call_queues: bool = False,
                 fast_mode: bool = False,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 refresh_token: Optional[str] = None,
                 org_id: Optional[str] = None
                 ) -> None:
        """Initialize a Webex instance to communicate with Webex and store data

        Args:
            access_token (str): The Webex API Access Token to authenticate the API calls
            get_locations (bool, optional): Whether to get all Locations and create instances for them. Defaults to
                True when there is only one Org. When more than one Org is present, setting this value to True has
                no effect and the Org-level method must be used.
            get_xsi (bool, optional): Whether to get the XSI endpoints for each Org. Defaults to False, since
                not every Org has XSI capability
            get_hunt_groups (bool, optional): Whether to get the Hunt Groups for each Org. Defaults to False. Setting
                this value to True only applies when one Org is present. If more than one Org is present, this arg
                is ignored and the Org-level method must be used.
            get_call_queues (bool, optional): Whether to get the Call Queues for each Org. Defaults to False. Setting
                this value to True only applies when one Org is present. If more than one Org is present, this arg
                is ignored and the Org-level method must be used.
            fast_mode (bool, optional): When possible, optimize the API calls to Webex to work more quickly,
                sometimes at the expense of not getting as much data. Use this option only if you have a script that
                runs very slowly, especially during the Webex initialization when collecting people. **Note that this
                option should not be used when it is necessary to know the phone numbers of each Person, because
                it skips the API call to the Call Control back-end on initialization.**
            client_id (str, optional): The Client ID or Application ID to associate with the token. This value is only
                useful if you are planning to call the :py:meth:`refresh_token()` method to refresh the token.
            client_secret (str, optional): The Client Secret for the Integration or Service Application. This value is
                only useful if you are planning to call the :py:math:`refresh_token()` method to refresh the token.
            refresh_token (str, optional): The Refresh Token associated with the Access Token. This argument is needed
                if you are planning to call the :py:meth:`refresh_token()` method to refresh the Access Token.
            org_id (str, optional): The Org ID to use as the default Org for the session. Other Orgs are still available
                in the :attr:`Webex.orgs` list.

        Returns:
            Webex: The Webex instance

        """
        log.info("Webex instance initialized")
        # The access token is the only thing that we need to get started
        self._access_token: str = access_token
        # The Authorization header is going to be used by every API call in the package.
        # Might want to make it something global, so we don't have to inherit it across all the children
        self._headers: dict = {"Authorization": "Bearer " + access_token}
        log.debug(f"Setting Org._headers to {self._headers}")
        log.debug(f"Setting Global _webex_headers")
        global _webex_headers
        _webex_headers['Authorization'] = "Bearer " + access_token

        # Fast Mode flag when needed
        self._fast_mode = fast_mode

        # Instance attrs
        self.client_id = client_id
        """ The Client ID or Application ID """
        self.client_secret = client_secret
        """ The Client Secret value for the Integration or Service Application """
        self.refresh_token = refresh_token
        """ The Refresh Token associated with the Access Token """

        self.orgs: list = []
        '''A list of the Org instances that this Webex instance can manage'''
        self.org: Optional[Org] = None
        """
        If there is only one Org in :py:attr:`Webex.orgs` or if the ``org_id`` param was passed, this attribute will be
        the first or selected Org.
        """
        self._me: Optional[Type[Me]] = None
        # Get the orgs that this token can manage
        log.debug(f"Making API call to v1/organizations")
        r = requests.get(_url_base + "v1/organizations", headers=self._headers)
        # Handle invalid access token
        if r.status_code != 200:
            log.critical("The Access Token was not accepted by Webex")
            log.debug(f"Response: {r.text}")
            raise TokenError("The Access Token was not accepted by Webex")
        response = r.json()
        # Handle when no Orgs are returned. This is pretty rare
        if len(response['items']) == 0:
            log.warning("No Orgs were returned by the Webex API")
            raise OrgError

        orgs = response['items']
        for org in orgs:
            log.debug(f"Processing org: {org['displayName']}")
            this_org = Org(name=org['displayName'], id=org['id'], parent=self,
                           locations=False, xsi=False, hunt_groups=False, call_queues=False)
            self.orgs.append(this_org)
        if org_id is not None:
            log.info(f"Setting Org ID {org_id} as default Org")
            self.org = self.get_org_by_id(org_id)
            if self.org is None:
                log.warning("Org not found")
                raise OrgError
        else:
            self.org = self.orgs[0]


    @property
    def headers(self):
        """The "universal" HTTP headers with the Authorization header present"""
        return self._headers

    def get_new_token(self, client_id: Optional[str] = None,
                      client_secret: Optional[str] = None,
                      refresh_token: Optional[str] = None):
        """ Refresh the Access Token

        To perform a refresh, you must know the client_id and client_secret, and refresh_token value. If you have not
        already set the attributes on the :py:class:`Webex` instance, you can provide them as arguments to this method.
        Passing those arguments will set the instance attributes, so they don't have to be passed on every call to this
        method, meaning any existing value will be overwritten.

        When the Access Token is refreshed, the :py:class:`Webex` instance will be updated to use the new token.

        Args:
            client_id (str): The Client ID or Application ID of your Integration or Service Application
            client_secret (str): The Client Secret of your Integration or Service Application
            refresh_token (str): The Refresh Token associated with the given Access Token

        Returns:
            dict: The new token information

        """
        if client_id is None:
            if self.client_id is None:
                raise ValueError
        else:
            self.client_id = client_id
        if client_secret is None:
            if self.client_secret is None:
                raise ValueError
        else:
            self.client_secret = client_secret
        if refresh_token is None:
            if self.refresh_token is None:
                raise ValueError
        else:
            self.refresh_token = refresh_token

        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }

        response = webex_api_call('post', '/v1/access_token', payload=payload)
        if 'access_token' in response:
            log.info(f"Changing Access Token to {response['access_token']}")
            self._access_token = response['access_token']
            self._headers: dict = {"Authorization": "Bearer " + self._access_token}

            log.debug(f"Setting Org._headers to {self._headers}")
            log.debug(f"Setting Global _webex_headers")
            global _webex_headers
            _webex_headers['Authorization'] = "Bearer " + self._access_token
            return response
        else:
            return False

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
            if name.lower() in org.name.lower():
                return org
        raise KeyError("Org not found")

    def get_org_by_id(self, id: str):
        """Get the Org instance by Org ID.

        Args:
            id (str): The ID of the Org to find

        Returns:
            Org: The Org instance of the matching Org

        Raises:
            wxcadm.exceptions.KeyError: Raised when no match is made

        """
        for org in self.orgs:
            if org.id == id or org.spark_id.split("/")[-1] == id:
                return org
        raise KeyError("Org not found")

    def get_person_by_email(self, email: str) -> Optional[wxcadm.person.Person]:
        """ Get the person instance  of a user with the given email address

        Unlike the :class:`Org` method of the same name, this method searches across all the Orgs that the token
        has access to, so it can find a user in any :class:`Org`

        Args:
            email (str): The email address to search for

        Returns:
            :class:`Person`: The Person instance. None is returned if no match is found

        """
        log.info(f"Getting Person record for email: {email}")
        response = webex_api_call("get", "v1/people", params={"email": email})
        if len(response) > 1:
            log.warn(f"Webex returned more than one record for email: {email}")
            raise APIError("Webex returned more than one Person with the specified email")
        elif len(response) == 1:
            log.debug(f"User data: {response[0]}")
            org = self.get_org_by_id(response[0]['orgId'])
            log.debug(f"User in Org: {org.name}")
            person = Person(response[0]['id'], parent=org, config=response[0])
            return person
        else:
            return None

    def get_person_by_id(self, id: str):
        """ Get the Person instance for a user with the given ID

        Unlike the :class:`Org` method of the same name, this method searches across all Orgs that the token has
        access to, so it can find a user in any :class:`Org`

        Args:
            id (str): The ID to search for

        Returns:
            Person: The Person instance. None is returned if no match is found

        """
        log.info(f"Getting Person record for ID: {id}")
        response = webex_api_call("get", "v1/people", params={"id": id})
        if len(response) > 1:
            log.warn(f"Webex returned more than one record for id: {id}")
            raise APIError("Webex returned more than one Person with the specified ID")
        elif len(response) == 1:
            log.debug(f"User data: {response[0]}")
            org = self.get_org_by_id(response[0]['orgId'])
            log.debug(f"User in Org: {org.name}")
            person = Person(response[0]['id'], parent=org, config=response[0])
            return person
        else:
            return None

    @property
    def me(self):
        """ An instance of the :py:class:`Me` class representing the token owner """
        if self._me is None:
            my_info = webex_api_call("get", "v1/people/me", headers=self.headers)
            me = Me(my_info['id'], parent=self.get_org_by_id(my_info['orgId']), config=my_info)
            self._me = me
        return self._me

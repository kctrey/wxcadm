from __future__ import annotations

import requests
from typing import Optional, Type
from datetime import datetime, timedelta

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
                 fast_mode: bool = False,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 refresh_token: Optional[str] = None,
                 org_id: Optional[str] = None,
                 auto_refresh_token: bool = False,
                 read_only: bool = False,
                 ) -> None:
        """Initialize a Webex instance to communicate with Webex and store data

        Args:
            access_token (str): The Webex API Access Token to authenticate the API calls
            fast_mode (bool, optional): When possible, optimize the API calls to Webex to work more quickly,
                sometimes at the expense of not getting as much data. Use this option only if you have a script that
                runs very slowly, especially during the Webex initialization when collecting people. **Note that this
                option should not be used when it is necessary to know the phone numbers of each Person, because
                it skips the API call to the Call Control back-end on initialization.**
            client_id (str, optional): The Client ID or Application ID to associate with the token. This value is only
                useful if you are planning to call the :py:meth:`refresh_token()` method to refresh the token.
            client_secret (str, optional): The Client Secret for the Integration or Service Application. This value is
                only useful if you are planning to call the :py:meth:`refresh_token()` method to refresh the token.
            refresh_token (str, optional): The Refresh Token associated with the Access Token. This argument is needed
                if you are planning to call the :py:meth:`refresh_token()` method to refresh the Access Token.
            org_id (str, optional): The Org ID to use as the default Org for the session. Other Orgs are still available
                in the :attr:`Webex.orgs` list.
            auto_refresh_token (bool, optional): When True, any API call will first check the access token expiration
                and automatically refresh the token if the expiration is within the next 30 minutes. Note that this
                requires the ``client_id``, ``client_secret`` and ``refresh_token`` to be provided when the
                :class:`Webex` instance is created, as those values are needed by the refresh process. **This feature
                is still in development and should not be used until this warning is removed**
            read_only (bool, optional): Set to True if the token has only read access. Defaults to False.

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

        ### Added in 4.6.0 - Create a WebexApi instance for API calls
        self.api = WebexApi(self._access_token)

        # Fast Mode flag when needed
        self._fast_mode = fast_mode

        # Set Read Only mode
        self._read_only = read_only

        # Instance attrs
        self.client_id = client_id
        """ The Client ID or Application ID """
        self.client_secret = client_secret
        """ The Client Secret value for the Integration or Service Application """
        self.refresh_token = refresh_token
        """ The Refresh Token associated with the Access Token """
        self.access_token_expires = None
        """ The datetime when the access token expires """
        self.refresh_token_expires = None
        """ The datetime when the refresh token expires """
        self.auto_refresh_token: bool = auto_refresh_token

        self.orgs: list = []
        '''A list of the Org instances that this Webex instance can manage'''
        self.org: Optional[Org] = None
        """
        If there is only one Org in :py:attr:`Webex.orgs` or if the ``org_id`` param was passed, this attribute will be
        the first or selected Org.
        """
        self._me: Optional[Type[Me]] = None
        if self._read_only is True:
            # We can't call /v1/organizations on a read-only token, so we have to get it from somewhere else
            log.info("Using token Org as Org ID")
            response = self.api.get('v1/people/me')
            log.debug(response)
            org_id = response['orgId']
            this_org = Org(name="My Organization", id=org_id, parent=self, xsi=False, api_connection=self.api)
            self.orgs.append(this_org)
        else:
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
                this_org = Org(api_connection=self.api, name=org['displayName'], id=org['id'], parent=self, xsi=False)
                self.orgs.append(this_org)

        if org_id is not None:
            log.info(f"Setting Org ID {org_id} as default Org")
            #self.org = self.get_org_by_id(org_id)
            if len(org_id) == 36:
                # We were given a UUID and need to go find the right value
                response = self.api.get(f"v1/organizations/{org_id}")
                org_id = response['id']
            self.org = Org(api_connection=self.api, name=org_id, id=org_id, parent=self, xsi=False)
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

        response = self.api.post('/v1/access_token', payload=payload)
        if 'access_token' in response:
            log.info(f"Changing Access Token to {response['access_token']}")
            self._access_token = response['access_token']
            self._headers: dict = {"Authorization": "Bearer " + self._access_token}

            log.debug(f"Setting Org._headers to {self._headers}")
            log.debug(f"Setting Global _webex_headers")
            global _webex_headers
            _webex_headers['Authorization'] = "Bearer " + self._access_token

            log.debug("Setting token expiry for Org instance")
            self.access_token_expires = datetime.now() + timedelta(seconds=response['expires_in'])
            self.refresh_token_expires = datetime.now() + timedelta(seconds=response['refresh_token_expires_in'])
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
        response = self.api.get("v1/people", params={"email": email, "callingData": True})
        if len(response) > 1:
            log.warn(f"Webex returned more than one record for email: {email}")
            raise APIError("Webex returned more than one Person with the specified email")
        elif len(response) == 1:
            log.debug(f"User data: {response[0]}")
            org = self.get_org_by_id(response[0]['orgId'])
            log.debug(f"User in Org: {org.name}")
            person = Person(response[0]['id'], org=org, config=response[0])
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
        response = self.api.get("v1/people", params={"id": id, "callingData": True})
        if len(response) > 1:
            log.warn(f"Webex returned more than one record for id: {id}")
            raise APIError("Webex returned more than one Person with the specified ID")
        elif len(response) == 1:
            log.debug(f"User data: {response[0]}")
            org = self.get_org_by_id(response[0]['orgId'])
            log.debug(f"User in Org: {org.name}")
            person = Person(response[0]['id'], org=org, config=response[0])
            return person
        else:
            return None

    @property
    def me(self):
        """ An instance of the :py:class:`Me` class representing the token owner """
        if self._me is None:
            my_info = self.api.get("v1/people/me")
            me = Me(my_info['id'], parent=self.get_org_by_id(my_info['orgId']), config=my_info)
            self._me = me
        return self._me

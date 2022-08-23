from __future__ import annotations

import requests
from typing import Optional, Type
from wxcadm import log
from .common import *
from .exceptions import *
from .org import Org
from .person import Me


class Webex:
    """The base class for working with wxcadm"""
    def __init__(self,
                 access_token: str,
                 get_org_data: bool = True,
                 get_people: bool = True,
                 get_locations: bool = True,
                 get_xsi: bool = False,
                 get_hunt_groups: bool = False,
                 get_call_queues: bool = False,
                 fast_mode: bool = False,
                 people_list: Optional[list] = None,
                 ) -> None:
        """Initialize a Webex instance to communicate with Webex and store data

        Args:
            access_token (str): The Webex API Access Token to authenticate the API calls
            get_org_data (bool, optional): Whether to automatically fetch the data for all Orgs. Setting this to
                False allows you to get a list of Orgs without collecting all the people and data for each. This
                reduces processing time and API calls. Once the desired Org is identified, you can collect the
                data directly from the :py:class:`Org` instance
            get_people (bool, optional): Whether to get all the People and created instances for them. Defaults to
                True when there is only one Org. When more than one Org is present, setting this value to True has
                no effect and the Org-level method must be used.
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
            people_list (list, optional): A list of people, by ID or email, to get instead of getting all People.
                **Note** that this overrides the ``get_people`` argument, only fetching the people in ``people_list``
                and will only be used if one Org is present. If multiple Orgs are present, this arg will have no effect.

        Returns:
            Webex: The Webex instance

        """
        log.info("Webex instance initialized")
        # The access token is the only thing that we need to get started
        self._access_token: str = access_token
        # The Authorization header is going to be used by every API call in the package.
        # Might want to make it something global so we don't have to inherit it across all of the children
        self._headers: dict = {"Authorization": "Bearer " + access_token}
        log.debug(f"Setting Org._headers to {self._headers}")
        log.debug(f"Setting Global _webex_headers")
        global _webex_headers
        _webex_headers['Authorization'] = "Bearer " + access_token

        # Fast Mode flag when needed
        self._fast_mode = fast_mode

        # Instance attrs
        self.orgs: list = []
        '''A list of the Org instances that this Webex instance can manage'''
        self.org: Optional[Org] = None
        """
        If there is only one Org in :py:attr:`Webex.orgs`, this attribute is an alias for Webex.orgs[0]. This attribute
        will be None if there are more than one Org accessible by the token, to prevent accidental changes to the
        incorrect Org.
        """
        self._me: Optional[Type[Me]] = None
        # Get the orgs that this token can manage
        log.debug(f"Making API call to v1/organizations")
        r = requests.get(_url_base + "v1/organizations", headers=self._headers)
        # Handle invalid access token
        if r.status_code != 200:
            log.critical("The Access Token was not accepted by Webex")
            raise TokenError("The Access Token was not accepted by Webex")
        response = r.json()
        # Handle when no Orgs are returned. This is pretty rare
        if len(response['items']) == 0:
            log.warning("No Orgs were retuend by the Webex API")
            raise OrgError
        # If a token can manage a lot of orgs, you might not want to create them all, because
        # it can take some time to do all the API calls and get the data back
        if get_org_data is False:
            log.info("Org data collection not requested. Storing orgs.")
            for org in response['items']:
                log.debug(f"Creating Org instance: {org['displayName']}")
                this_org = Org(name=org['displayName'], id=org['id'], parent=self,
                               people=False, locations=False, xsi=False, hunt_groups=False, call_queues=False)
                self.orgs.append(this_org)
            return
        else:
            log.info("Org initialization requested. Collecting orgs")
            if len(response['items']) == 1:
                for org in response['items']:
                    log.debug(f"Processing org: {org['displayName']}")
                    # If we were given a list of people, don't have the Org get all people
                    if people_list is not None:
                        get_people = False
                    org = Org(org['displayName'], org['id'],
                              people=get_people, locations=get_locations, xsi=get_xsi, parent=self,
                              call_queues=get_call_queues, hunt_groups=get_hunt_groups, people_list=people_list)
                    self.orgs.append(org)
                # Most users have only one org, so to make that easier for them to work with
                # we are also going to put the orgs[0] instance in the org attr
                # That way both .org and .orgs[0] are the same if they only have one Org
                log.debug(f"Only one org found. Storing as Webex.org")
                self.org = self.orgs[0]
            elif len(response['items']) > 1:
                log.debug("Multiple Orgs present. Skipping data collection during Org init")
                for org in response['items']:
                    log.debug(f"Processing org: {org['displayName']}")
                    this_org = Org(name=org['displayName'], id=org['id'], parent=self,
                                   people=False, locations=False, xsi=False, hunt_groups=False, call_queues=False)
                    self.orgs.append(this_org)

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
            if org.id == id:
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

    def get_person_by_id(self, id: str):
        """ Get the Person instance for a user with the given ID

        Unlike the :class:`Org` method of the same name, this method searches across all Orgs that the token has
        access to, so it can find a user in any :class:`Org`

        Args:
            id (str): The ID to search for

        Returns:
            Person: The Person instance. None is returned if no match is found

        """
        for org in self.orgs:
            person = org.get_person_by_id(id)
            if person is not None:
                return person
        return None

    @property
    def me(self):
        """ An instance of the :py:class:`Me` class representing the token owner """
        if self._me is None:
            my_info = webex_api_call("get", "v1/people/me", headers=self.headers)
            me = Me(my_info['id'], parent=self.get_org_by_id(my_info['orgId']), config=my_info)
            self._me = me
        return self._me

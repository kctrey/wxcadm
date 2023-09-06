from __future__ import annotations

from typing import Union
from dataclasses import dataclass, field
from collections import UserList

import wxcadm.org
from wxcadm import log
from .common import *


class WebexApplications(UserList):
    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing WebexApps instance")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_applications()

    def _get_applications(self):
        app_list = []
        apps = webex_api_call("get", "v1/applications", params={"orgId": self.parent.id})
        for app in apps:
            this_app = WebexApplication(parent=self.parent, **app)
            app_list.append(this_app)
        return app_list

    @property
    def org_apps(self):
        """ List of :py:class:`WebexApplication` instances for apps owned by this Org """
        org_apps = []
        for app in self.data:
            if app.orgId == self.parent.id:
                org_apps.append(app)
        return org_apps

    def get_app_by_name(self, name: str) -> Union[WebexApplication, list]:
        """ Get a :py:class:`WebexApplication` instance by application name

        .. note::
            It isn't "against the rules" for two apps to have the same name. If only one app is found, just the
            :py:class:`WebexApplication` instance is returned. If more than one app is found, a list of instances will
            be returned

        Args:
             name (str): The name of the :py:class:`WebexApplication` to search for

        Returns:
            WebexApplication: The application instance

        """
        found_apps = []
        for app in self.data:
            if app.name == name:
                found_apps.append(app)
        if len(found_apps) == 0:
            return None
        elif len(found_apps) == 1:
            return found_apps[0]
        else:
            return found_apps

    def get_app_by_id(self, id: str) -> WebexApplication:
        """ Get a :py:class:`WebexApplication` instance by application ID

        Args:
            id (str): The ID of the :py:class:`WebexApplication` to get

        Returns:
            WebexApplication: The application instance. None is returned if no match is found.

        """
        # First check the known apps to see if we already have it
        for app in self.data:
            if app.id == id:
                return app
        # If it wasn't found, call the API to get the app and build an instance for it
        app = webex_api_call('get', f'/v1/applications/{id}')
        this_app = WebexApplication(parent=self.parent, **app)
        self.data.append(this_app)
        return this_app

    def add_service_application(self, name: str,
                                contact_email: str,
                                scopes: list,
                                logo: str = "https://pngimg.com/uploads/hacker/hacker_PNG6.png"):
        """ Add a Service App to the Org

        .. note::

            Ensure you record the client_secret that comes back. It will not be visible later.

        .. warning::

            The Service App capability is in Early Field Trial and may not be available for you Org.

        Args:
            name (str): The name of the application
            contact_email (str): The Contact Email to attach to the application
            scopes (list): A list of Webex scopes to assign to the application
            logo (str, optional): A URL to a logo image. If not specified, a generic phone icon is used.

        """
        payload = {'type': 'authorizedAppIssuer',
                   'name': name,
                   'contactEmail': contact_email,
                   'logo': logo,
                   'scopes': scopes}
        response = webex_api_call("post", "v1/applications", payload=payload)
        return response


@dataclass
class WebexApplication:
    parent: wxcadm.Org = field(repr=False)
    isNative: bool = field(repr=False)
    id: str
    friendlyId: str
    type: str
    name: str
    orgId: str = field(repr=False)
    isFeatured: bool = field(repr=False)
    submissionStatus: str = field(repr=False)
    createdBy: str = field(repr=False)
    created: str = field(repr=False)
    description: str = field(default='', repr=False)
    modified: str = field(default='', repr=False)
    redirectUrls: list = field(default=None, repr=False)
    scopes: list = field(default=None, repr=False)
    clientId: str = field(default='', repr=False)
    logo: str = field(default='', repr=False)
    tagLine: str = field(default='', repr=False)
    shortTagLine: str = field(default='', repr=False)
    categories: list = field(default=None, repr=False)
    videoUrl: str = field(default='', repr=False)
    contactEmail: str = field(default='', repr=False)
    contactName: str = field(default='', repr=False)
    companyName: str = field(default='', repr=False)
    companyUrl: str = field(default='', repr=False)
    supportUrl: str = field(default='', repr=False)
    privacyUrl: str = field(default='', repr=False)
    productUrl: str = field(default='', repr=False)
    applicationUrls: list = field(default=None, repr=False)
    botEmail: str = field(default='', repr=False)
    botPersonId: str = field(default='', repr=False)
    submissionDate: str = field(default='', repr=False)
    orgSubmissionStatus: str = field(default='', repr=False)
    appContext: str = field(default='', repr=False)
    tags: list = field(default=None, repr=False)
    screenshot1: str = field(default='', repr=False)
    screenshot2: str = field(default='', repr=False)
    screenshot3: str = field(default='', repr=False)
    validDomains: list = field(default=None, repr=False)
    groupId: str = field(default='', repr=False)
    version: str = field(default='', repr=False)
    meetingLayoutPreference: str = field(default='', repr=False)
    entitlements: str = field(default='', repr=False)

    def authorize(self):
        """ Authorize the application for the Organization

        Returns:
            bool: True on success, False otherwise

        """
        payload = {'orgId': self.parent.id}
        response = webex_api_call('post', f'/v1/applications/{self.id}/authorize', payload=payload)
        return response

    def delete(self):
        """ Delete the application

        Returns:

        """
        response = webex_api_call('delete', f'/v1/applications/{self.id}')
        return response

    def get_token(self, client_secret: str, target_org: wxcadm.Org | str):
        """ Get the access and refresh tokens to utilize the application in the target Org

        Args:
            client_secret (str): The Client Secret value stored when the Application was created
            target_org (str): The Base64 Org ID to obtain a token for

        Returns:
            dict: A dict of the token info, including access_token and refresh_token

        """
        if isinstance(target_org, wxcadm.org.Org):
            org_id = target_org.id
        else:
            org_id = target_org
            #TODO - Eventually we should take the Org ID in both Base64 (current) and the UUID format

        payload = {
            'clientId': self.clientId,
            'clientSecret': client_secret,
            'targetOrgId': org_id
        }
        response = webex_api_call('post', f'/v1/applications/{self.id}/token', payload=payload)
        return response

    def get_token_refresh(self, client_secret: str, refresh_token: str):
        """ Use the provided Refresh Token to obtain a new Access Token

        Args:
            client_secret (str): The Client Secret value stored when the Application was created
            refresh_token (str): The Refresh Token stored when the initial token was obtained with :py:meth:get_token()

        Returns:
            dict: A dict of the token info, including access_token and refresh_token

        """
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.clientId,
            'client_secret': client_secret,
            'refresh_token': refresh_token
        }
        response = webex_api_call('post', '/v1/access_token', payload=payload)
        return response

    def regenerate_client_secret(self):
        """ Obtain a new Client Secret if the initial value was lost or compromised

        Returns:
            str: The new Client Secret value
        """
        response = webex_api_call('delete', f'/v1/applications/{self.id}/clientSecret')
        if 'clientSecret' in response:
            return response['clientSecret']
        else:
            return False

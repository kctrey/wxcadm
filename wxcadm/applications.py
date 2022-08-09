from __future__ import annotations

from typing import Union
from dataclasses import dataclass, field
from collections import UserList
from wxcadm import log
from .common import *


class WebexApplications(UserList):
    def __init__(self, parent: Org):
        super().__init__()
        log.debug("Initializing WebexApps instance")
        self.parent: Org = parent
        self.data: list = self._get_applications()

    def _get_applications(self):
        app_list = []
        apps = webex_api_call("get", "v1/applications")
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
        if len(found_apps) == 1:
            return found_apps[0]
        else:
            return found_apps

    def add_authorized_application(self, name: str,
                                   contact_email: str,
                                   scopes: list,
                                   logo: str = "https://pngimg.com/uploads/phone/phone_PNG48927.png"):
        """ Add an Authorized App to the Org

        .. warning::

            The Authorized App capability is in Early Field Trial and may not be available for you Org.

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
    parent: Org = field(repr=False)
    isNative: bool = field(repr=False)
    id: str
    friendlyId: str
    type: str
    name: str
    description: str = field(repr=False)
    orgId: str = field(repr=False)
    isFeatured: bool = field(repr=False)
    submissionStatus: str = field(repr=False)
    createdBy: str = field(repr=False)
    created: str = field(repr=False)
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

from __future__ import annotations

import logging
from collections import UserList
from dataclasses import dataclass, field

from wxcadm import log


class Webhooks(UserList):
    def __init__(self):
        log.info("Initializing Webhooks instance")
        super().__init__()
        self.data = []
        items = webex_api_call("get", "v1/webhooks")
        log.debug(f"Webex returned {len(items)} webhooks")
        for item in items:
            webhook = Webhook(**item)
            self.data.append(webhook)

    @property
    def active(self):
        """ Return only the active Webhook instances """
        active = []
        for webhook in self.data:
            if webhook.status.lower() == "active":
                active.append(webhook)
        return active

    @property
    def inactive(self):
        """ Return only the inactive Webhook instances """
        inactive = []
        for webhook in self.data:
            if webhook.status.lower() == "inactive":
                inactive.append(webhook)
        return inactive

    def add(self, name: str,
            url: str,
            resource: str,
            event: str,
            filter: str = None,
            secret: str = None,
            owner: str = None):
        """ Add a new Webhook

        Possible values for arguments can be found at `<https://developer.webex.com/docs/webhooks>`_

        Args:
            name (str): The name of the Webhook
            url (str): The URL to which the Webbook mesages should be sent
            resource (str): The resource type of the Webhook
            event (str): The event type to trigger the Webhook
            filter (str, optional): A valid filter for the Webhook, if needed
            secret (str, optional): The secret value used to generate the Webhook signature
            owner (str, optional): The Webhook owner is creating an org-wide Webhook

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Creating Webhook with name: {name}")
        payload = {"name": name,
                   "targetUrl": url,
                   "resource": resource,
                   "event": event,
                   "filter": filter,
                   "secret": secret,
                   "ownedBy": owner}
        new_webhook = webex_api_call("post", "v1/webhooks", payload=payload)
        if new_webhook:
            log.debug(f"New Webhook ID: {new_webhook['id']}")
            self.data.append(Webhook(**new_webhook))
            return True
        else:
            log.warning("The Webhook creation failed")
            return False


@dataclass
class Webhook:
    """ The Webhook class contains information about each Webhook """
    orgId: str = field(repr=False)
    appId: str
    """ The ID of the application """
    id: str
    """ The unique ID of the Webhook """
    name: str
    """ The user-defined name of the Webhook """
    targetUrl: str
    """ The URL to which messages will be sent """
    resource: str
    """ The resource type for the Webhook """
    event: str
    """ The event type (e.g. created, updated, etc...) for the Webhook """
    status: str
    """ The status of the Webhook, either active or inactive """
    created: str
    """ The date and time the Webhook was created """
    createdBy: str
    """ The ID of the user who created the Webhook """
    ownedBy: str
    """ The owner of the Webhook. Specified when creating an org-level Webhook """
    filter: Optional[str] = None
    """ Any filter that is applied to the Webhook """
    secret: Optional[str] = None
    """ The secret used to generate the payload signature """

    def delete(self) -> bool:
        """ Delete the Webhook

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Deleting Webhook: {self.name}")
        success = webex_api_call("delete", f"v1/webhooks/{self.id}")
        if success:
            return True
        else:
            log.warning("The Webhook delete failed")
            return False

    def change_url(self, url: str) -> bool:
        """ Change the URL to which the Webhook will be sent

        Args:
            url (str): The new URL for the Webhook

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Changing Webhook URL for {self.name} to {url}")
        payload = {"name": self.name,
                   "targetUrl": url,
                   "secret": self.secret,
                   "ownedBy": self.ownedBy,
                   "status": self.status}
        success = webex_api_call("put", f"v1/webhooks/{self.id}", payload=payload)
        if success:
            self.targetUrl = url
            return True
        else:
            log.warning("The Webhook change failed")
            return False

    def change_name(self, name: str) -> bool:
        """ Change the name of the Webhook

        Args:
            name (str): The new name for the Webhook

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Changing Webhook name for {self.name} to {name}")
        payload = {"name": name,
                   "targetUrl": self.targetUrl,
                   "secret": self.secret,
                   "ownedBy": self.ownedBy,
                   "status": self.status}
        success = webex_api_call("put", f"v1/webhooks/{self.id}", payload=payload)
        if success:
            self.name = name
            return True
        else:
            log.warning("The Webhook change failed")
            return False

    def change_secret(self, secret: str) -> bool:
        """ Change the secret value used to generate the Webhook signature

        Args:
            secret (str): The new secret value

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Changing Webhook secret for {self.name} to {secret}")
        payload = {"name": self.name,
                   "targetUrl": self.targetUrl,
                   "secret": secret,
                   "ownedBy": self.ownedBy,
                   "status": self.status}
        success = webex_api_call("put", f"v1/webhooks/{self.id}", payload=payload)
        if success:
            self.secret = secret
            return True
        else:
            log.warning("The Webhook change failed")
            return False

    def change_owner(self, owner: str) -> bool:
        """ Change the owner of the Webhook

        Args:
            owner (str): The new owner value

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Changing Webhook owner for {self.name} to {owner}")
        payload = {"name": self.name,
                   "targetUrl": self.targetUrl,
                   "secret": self.secret,
                   "ownedBy": owner,
                   "status": self.status}
        success = webex_api_call("put", f"v1/webhooks/{self.id}", payload=payload)
        if success:
            self.ownedBy = owner
            return True
        else:
            log.warning("The Webhook change failed")
            return False

    def deactivate(self) -> bool:
        """ Change the status of the Webhook to inactive

        Returns:
            bool: True on success, False otherwise. True will be returned if the Webhook is already inactive.

        """
        log.info(f"Deactivating Webhook: {self.name}")
        payload = {"name": self.name,
                   "targetUrl": self.targetUrl,
                   "secret": self.secret,
                   "ownedBy": self.ownedBy,
                   "status": "inactive"}
        success = webex_api_call("put", f"v1/webhooks/{self.id}", payload=payload)
        if success:
            self.status = "inactive"
            return True
        else:
            log.warning("The Webhook change failed")
            return False

    def activate(self) -> bool:
        """ Change the status of the Webhook to active

        Returns:
            bool: True on success, False otherwise. True will be returned if the Webhook is already active.

        """
        log.info(f"Activating Webhook: {self.name}")
        payload = {"name": self.name,
                   "targetUrl": self.targetUrl,
                   "secret": self.secret,
                   "ownedBy": self.ownedBy,
                   "status": "active"}
        success = webex_api_call("put", f"v1/webhooks/{self.id}", payload=payload)
        if success:
            self.status = "active"
            return True
        else:
            log.warning("The Webhook change failed")
            return False

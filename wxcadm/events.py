from __future__ import annotations
from typing import Optional
from datetime import datetime, timedelta
from collections import UserList
import requests

from .common import *
import wxcadm
from wxcadm import log


class AuditEvent:
    def __init__(self, config: dict):
        self.id: str = config.get('id', '')
        """ The ID of the Admin Event """
        self.actor_id: str = config.get('actorId', '')
        """ The ID of the actor making the change """
        self.actor_name: str = config['data'].get('actorName', '')
        """ The name of the actor making the change """
        self.actor_email: str = config['data'].get('actorEmail', '')
        """ The email address of the actor making the change """
        self.actor_org_name: str = config['data'].get('actorOrgName', '')
        """ The Org name of the actor making the change """
        self.actor_org_id: str = config.get('actorOrgId', '')
        """ The Org ID of the actor making the change """
        self.actor_user_agent: str = config['data'].get('actorUserAgent', '')
        """ The User Agent type of the actor making the change """
        self.admin_roles: list[str] = config['data'].get('adminRoles', [])
        """ The admin roles of the actor making the change """
        self.actor_ip: str = config['data'].get('actorIp', '')
        """ The IP address of the actor making the change """
        self.target_type: str = config['data'].get('targetType', '')
        """ The type of target being changed """
        self.target_id: str = config['data'].get('targetId', '')
        """ The identified of the target being changed """
        self.target_name: str = config['data'].get('targetName', '')
        """ The name of the target being changed """
        self.target_org_name: str = config['data'].get('targetOrgName', '')
        """ The Org name of the target being changed """
        self.target_org_id: str = config['data'].get('targetOrgId', '')
        """ The Org ID of the target being changed """
        self.description: str = config['data'].get('eventDescription', '')
        """ The description of the change """
        self.tracking_id: str = config['data'].get('trackingId', '')
        """ A unique tracking ID for the change """
        self.category: str = config['data'].get('eventCategory', '')
        """ The category of the change """
        self.text: str = config['data'].get('actionText', '')
        """ The full text of the change details """
        self.timestamp: str = config.get('created', '')
        """ The timestamp when the change was made """


class AuditEventList(UserList):
    def __init__(self, parent: wxcadm.Org, start: str, end: str):
        log.info("AuditEventList instance created")
        super().__init__()
        self.parent = parent
        self.start = start
        """ The start date of the audit events """
        self.end = end
        """ The end date of the audit events """
        self.data = self._get_data()

    def _get_data(self):
        data = []
        response = webex_api_call(
            "get",
            f"v1/adminAudit/events",
            params={'orgId': self.parent.org_id, 'from': self.start, 'to': self.end}
        )
        for entry in response:
            data.append(AuditEvent(entry))
        return data


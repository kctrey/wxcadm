from __future__ import annotations

from collections import UserList
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from typing import Optional, Union, List

import wxcadm
import wxcadm.location
import wxcadm.person
from wxcadm import log
from .common import *

@dataclass_json
@dataclass
class MonitoringList:
    parent: Union[wxcadm.Person, wxcadm.Workspace]
    org: wxcadm.Org
    call_park_notification: bool = field(metadata=config(field_name="callParkNotificationEnabled"))
    """ Whether to notify the user about calls parked on monitored lines """
    monitored_elements: list = field(metadata=config(field_name="monitoredElements"))
    """ List of monitored elements, which may be Person, Workspace, CallParkExtension or VirtualLine """
    _url: str = field(init=False, repr=False)

    def __post_init__(self):
        # Set the _url based on whether this is for a Person or a Workspace
        if isinstance(self.parent, wxcadm.Workspace):
            self._url = f"v1/workspaces/{self.parent.id}/features/monitoring"
        else:
            self._url = f"v1/people/{self.parent.id}/features/monitoring"
        log.debug("Resolving monitored elements")
        new_monitoring_list = []
        for monitored_element in self.monitored_elements:
            element_type, element_info = list(monitored_element.items())[0]
            if element_type == 'callparkextension':
                park_extensions = self.org.locations.get(id=element_info['locationId']).park_extensions
                for park_extension in park_extensions:
                    if park_extension.id == element_info['id']:
                        this_element = park_extension
                        break
            elif element_type == 'member':
                if element_info['type'] == 'PEOPLE':
                    this_element = self.org.people.get(id=element_info['id'])
                elif element_info['type'] == 'PLACE':
                    this_element = self.org.workspaces.get(id=element_info['id'])
                elif element_info['type'] == 'VIRTUAL_LINE':
                    this_element = self.org.virtual_lines.get(id=element_info['id'])
                else:
                    log.warning("Unknown element info type: {}".format(element_info['type']))
                    log.debug(f"Details: {element_info}")
                    continue
            else:
                log.warning("Unknown element type: {}".format(element_type))
                continue
            new_monitoring_list.append(this_element)
        self.monitored_elements = new_monitoring_list

    def add(self, monitor: Union[wxcadm.Person, wxcadm.VirtualLine, wxcadm.Workspace, wxcadm.CallParkExtension]):
        """ Add a new monitoring

        Args:
            monitor (Person, VirtualLine, Workspace, CallParkExtension): The new element to monitor

        Returns:
            bool: True on success, False otherwise

        """
        payload = {
            "enableCallParkNotification": self.call_park_notification,
            "monitoredElements": [],
        }
        for element in self.monitored_elements:
            payload["monitoredElements"].append(element.id)
        payload["monitoredElements"].append(monitor.id)
        webex_api_call("put", url=self._url, payload=payload,
                       params={"orgId": self.org.id})
        self.monitored_elements.append(monitor)
        return True

    def remove(self, monitor: Union[wxcadm.Person, wxcadm.VirtualLine, wxcadm.Workspace, wxcadm.CallParkExtension]):
        """ Remove a monitoring

        Args:
            monitor: (Person, VirtualLine, Workspace, CallParkExtension): The new element to monitor

        Returns:
            bool: True on success, False otherwise

        """
        payload = {
            "enableCallParkNotification": self.call_park_notification,
            "monitoredElements": [],
        }
        new_monitoring_list = []
        for element in self.monitored_elements:
            if element.id != monitor.id:
                payload["monitoredElements"].append(element.id)
                new_monitoring_list.append(element)
        webex_api_call("put", url=self._url, payload=payload,
                       params={"orgId": self.org.id})
        self.monitored_elements = new_monitoring_list
        return True

    def replace(self, monitoring_list: MonitoringList):
        """ Replace the monitoring config and monitored elements with a new :class:`~.monitoring.MonitoringList`

        Args:
            monitoring_list (MonitoringList): The new monitoring list

        Returns:
            bool: True on success, False otherwise

        """
        payload = {
            "enableCallParkNotification": monitoring_list.call_park_notification,
            "monitoredElements": [],
        }
        for element in monitoring_list.monitored_elements:
            # Remove the current User/Workspace if it is in the list
            if element.id != self.parent.id:
                payload["monitoredElements"].append(element.id)
        webex_api_call("put", url=self._url, payload=payload,
                       params={"orgId": self.org.id})
        self.monitored_elements = monitoring_list.monitored_elements
        self.call_park_notification = monitoring_list.call_park_notification
        return True

    def copy_to(self, target: Union[wxcadm.Person, wxcadm.Workspace]):
        """ Copy the monitoring config to another Person or Workspace

        Args:
            target (Person, Workspace): Person or Workspace to copy to

        Returns:
            bool: True on success, False otherwise

        """
        target.monitoring.replace(self)
        return True

    def copy_from(self, source: Union[wxcadm.Person, wxcadm.Workspace]):
        """ Copy the monitoring config from another Person or Workspace

        Args:
            source (Person, Workspace): Person or Workspace to copy from

        Returns:
            bool: True on success, False otherwise

        """
        self.replace(source.monitoring)
        return True

    def clear(self):
        """ Clear the list of monitored elements. This removes all monitoring.

        Returns:
            bool: True on success, False otherwise

        """
        log.debug(f"Clearing monitoring list for {self.parent.id}")
        payload = {
            "enableCallParkNotification": False,
            "monitoredElements": [],
        }
        webex_api_call("put", url=self._url, payload=payload, params={"orgId": self.org.id})
        self.monitored_elements = []
        self.call_park_notification = False
        return True


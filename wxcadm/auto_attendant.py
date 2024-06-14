from __future__ import annotations

from typing import Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from wxcadm import Org, Location
from dataclasses import dataclass
from collections import UserList

import wxcadm.location
from wxcadm import log
from .common import *


class AutoAttendantList(UserList):
    def __init__(self, parent: Union[Org, Location]):
        super().__init__()
        log.debug("Initializing AutoAttendantLisa instance")
        self.parent: Union["Org", "Location"] = parent
        self.data: list = self._get_items()

    def _get_items(self):
        if isinstance(self.parent, wxcadm.Org):
            log.debug("Using Org ID as data filter")
            params = {'orgId': self.parent.id}
        elif isinstance(self.parent, wxcadm.Location):
            log.debug("Using Location as data filter")
            params = {'locationId': self.parent.id}
        else:
            raise ValueError("Unsupported parent class")

        log.debug("Getting Auto Attendant list")
        response = webex_api_call('get', f'v1/telephony/config/autoAttendants', params=params)
        log.debug(f"Received {len(response['autoAttendants'])} entries")
        items = []
        for entry in response['autoAttendants']:
            items.append(AutoAttendant(parent=self.parent, id=entry['id'], data=entry))
        return items

    def refresh(self):
        """ Refresh the list of Auto Attendants from Webex

        Returns:
            bool: True on success, False otherwise.

        """
        self.data = self._get_items()
        return True

    def get(self, id: str = None, name: str = None, spark_id: str = None, uuid: str = None):
        """ Get the AutoAttendant instance associated with a given ID, Name, or Spark ID

        Only one parameter should be supplied in normal cases. If multiple arguments are provided, the Auto
        Attendants will be searched in order by ID, Name, UUID and Spark ID. If no arguments are provided, the method
        will raise an Exception.

        Args:
            id (str, optional): The AutoAttendant ID to find
            name (str, optional): The AutoAttendant Name to find
            spark_id (str, optional): The Spark ID to find
            uuid (str, optional): The UUID to find

        Returns:
            AutoAttendant: The AutoAttendant instance correlating to the given search argument.
                None is returned if no AutoAttendant is found.

        Raises:
            ValueError: Raised when the method is called with no arguments

        """
        if id is None and name is None and spark_id is None and uuid is None:
            raise ValueError("A search argument must be provided")
        if id is not None:
            for aa in self.data:
                if aa.id == id:
                    return aa
        if name is not None:
            for aa in self.data:
                if aa.name == name:
                    return aa
        if uuid is not None:
            for aa in self.data:
                if aa.spark_id.split('/')[-1].upper() == uuid.upper():
                    return aa
        if spark_id is not None:
            for aa in self.data:
                if aa.spark_id == spark_id:
                    return aa
        return None

    def create(self,
               name: str,
               first_name: str,
               last_name: str,
               phone_number: Optional[str],
               extension: Optional[str],
               business_hours_schedule: str,
               holiday_schedule: Optional[str],
               business_hours_menu: Optional[dict] = None,
               after_hours_menu: Optional[dict] = None,
               extension_dialing_scope: str = "GROUP",
               name_dialing_scope: str = "GROUP",
               language: Optional[str] = None,
               time_zone: Optional[str] = None,
               location: Optional[wxcadm.Location] = None
               ):
        """ Create a new Auto Attendant

        Args:
            name (str): The name of the Auto Attendant
            first_name (str): The first name of the Auto Attendant in the directory
            last_name (str): The last name of the Auto Attendant in the directory
            phone_number (str, optional): The phone number of the Auto Attendant
            extension (str, optional): The extension of the Auto Attendant
            business_hours_schedule (str): The name of the Business Hours Schedule to appy to the Auto Attendant
            holiday_schedule (str, optional): The name of the Holiday Schedule to apply to the Auto Attendant
            business_hours_menu (dict, optional): The Business Hours menu configuration. See the Webex Developer docs
                for details. Defaults to a menu with a zero (0) to exit the menu.
            after_hours_menu (dict, optional): The After Hours menu configuration. See the Webex Developer docs for
                details. Defaults to a menu with 1 zero (0) to exit the menu.
            extension_dialing_scope (str, optional): Whether extension dialing matches at the `'GROUP'` (i.e. Location)
                or `'ENTERPRISE'`. Defaults to `'GROUP'`
            name_dialing_scope (str, optional): Whether name dialing matches at the `'GROUP'` (i.e. Location) or
                `'ENTERPRISE'`. Defaults to `'GROUP'`
            language (str, optional): The language code for the Auto Attendant. Defaults to the Location language
            time_zone (str, optional): The time zone for the Auto Attendant. Defaults to the Location time zone
            location (Location, optional): The Location to build the Auto Attendant at. If the
                :class:`AutoAttendantList` is at the Location level, this parameter is optional. If it is at the
                Org level, it is required.

        Returns:
            AutoAttendant: The :class:`AutoAttendant` that is created.

        """
        if location is None and isinstance(self.parent, wxcadm.Org):
            raise ValueError("location is required for Org-level AutoAttendantList")
        elif location is None and isinstance(self.parent, wxcadm.Location):
            location = self.parent
        log.info(f"Creating Auto Attendant at Location {location.name} with name: {name}")
        if location.calling_enabled is False:
            log.debug("Not a Webex Calling Location")
            return None
        # Get some values if they weren't passed
        if phone_number is None and extension is None:
            raise ValueError("phone_number and/or extension are required")
        if time_zone is None:
            log.debug(f"Using Location time_zone {location.time_zone}")
            time_zone = location.time_zone
        if language is None:
            log.debug(f"Using Location announcement_language {location.announcement_language}")
            language = location.announcement_language
        if business_hours_menu is None or after_hours_menu is None:
            default_menu = {
                'greeting': 'DEFAULT',
                'extensionEnabled': True,
                'keyConfigurations': [
                    {'key': '0', 'action': 'EXIT'}
                ]
            }
            if business_hours_menu is None:
                log.debug('Using default menu for Business Hours')
                business_hours_menu = default_menu
            if after_hours_menu is None:
                log.debug('Using default menu for After Hours')
                after_hours_menu = default_menu

        payload = {
            "name": name,
            "firstName": first_name,
            "lastName": last_name,
            "extension": extension,
            "phoneNumber": phone_number,
            "timeZone": time_zone,
            "languageCode": language,
            "businessSchedule": business_hours_schedule,
            "holidaySchedule": holiday_schedule,
            "extensionDialing": extension_dialing_scope,
            "nameDialing": name_dialing_scope,
            "businessHoursMenu": business_hours_menu,
            "afterHoursMenu": after_hours_menu
        }
        response = webex_api_call("post", f"v1/telephony/config/locations/{location.id}/autoAttendants",
                                  payload=payload)
        new_aa_id = response['id']
        self.refresh()
        return self.get(id=new_aa_id)


@dataclass
class AutoAttendant:
    parent: Union[wxcadm.Org, wxcadm.Location]
    """ The Org instance that ows this AutoAttendant """
    id: str
    """ The Webex ID of the AutoAttendant """
    data: dict

    def __post_init__(self):
        self.name = self.data.get('name', '')
        self.location_id = self.data.get('locationId', '')

    @property
    def spark_id(self) -> str:
        return decode_spark_id(self.id)

    @property
    def config(self) -> dict:
        """ The config of the AutoAttendant """
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.location_id}/autoAttendants/{self.id}")
        return response

    @property
    def call_forwarding(self) -> dict:
        """ The Call Forwarding settings for the AutoAttendant """
        response = webex_api_call("get", f"v1/telephony/config/locations/{self.location_id}/autoAttendants/{self.id}"
                                         f"/callForwarding")
        return response

    def copy_menu_from_template(self, source: AutoAttendant, menu_type: str = "both"):
        """ Copy the Business Hours, After Hours, or both menus from another :class:`AutoAttendant` instance.

        Note that this copy functionality will not work (yet) if the source Auto Attendant uses a CUSTOM announcement,
        which, unfortunately, is most of them. The Webex API should support this soon, but, until them, the method's
        usefulness is limited.

        Args:
            source (AutoAttendant): The source :class:`AutoAttendant` instance to copy from
            menu_type (str, optional): The menu to copy. 'business_hours', 'after_hours' or 'both' are valid. Defaults
                to 'both'.

        Returns:
            bool: True on success. False otherwise.

        Raises:
            ValueError: Raised when the menu_type value is not one of the accepted values.

        """
        if menu_type.lower() == "both":
            self.config['businessHoursMenu'] = source.config['businessHoursMenu']
            self.config['afterHoursMenu'] = source.config['afterHoursMenu']
        elif menu_type.lower() == "business_hours":
            self.config['businessHoursMenu'] = source.config['businessHoursMenu']
        elif menu_type.lower() == "after_hours":
            self.config['afterHoursMenu'] = source.config['afterHoursMenu']
        else:
            raise ValueError(f"{menu_type} must be 'business_hours', 'after_hours' or 'both'")

        resp = webex_api_call("put", f"v1/telephony/config/locations/{self.location_id}/autoAttendants/{self.id}",
                              payload=self.config)
        if resp:
            return True
        else:
            return False

from __future__ import annotations

from typing import Union, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, Undefined
from collections import UserList

import wxcadm
from wxcadm import log
from .common import *


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Number:
    phone_number: Optional[str] = None
    """ The phone number """
    extension: Optional[str] = None
    """ The extension """
    routing_prefix: Optional[str] = None
    """ The Location routing prefix """
    esn: Optional[str] = None
    """ The Enterprise Number """
    state: Optional[str] = None
    """ The state of the number """
    phone_number_type: Optional[str] = None
    """ The type of phone number """
    included_telephony_types: Optional[str] = None
    """ The type of telephony that is included with this number """
    main_number: Optional[bool] = None
    """ Whether this is a Main Number for a Location """
    toll_free_number: Optional[bool] = None
    """ Whether the number is a toll-free number """
    _location: Optional[Union[dict, wxcadm.Location]] = None
    _owner: Optional[Union[dict, wxcadm.Person, wxcadm.VirtualLine, wxcadm.Workspace]] = None
    org: Optional[wxcadm.Org] = field(init=False, repr=False)

    @property
    def location(self) -> Optional[Union[wxcadm.Location, dict]]:
        if self._location:
            found_location = self.org.locations.get(id=self._location['id'])
            if found_location is not None:
                return found_location
            else:
                return self._location
        else:
            return None

    @property
    def owner(self):
        if self._owner:
            owner_id = self._owner.get('id', None)
            if owner_id is not None:
                owner_type = self._owner['type']
                if owner_type == 'PEOPLE':
                    owner = self.org.people.get(id=owner_id)
                    if owner is not None:
                        return owner
                    else:
                        return self._owner
                elif owner_type == 'PLACE':
                    owner = self.org.workspaces.get(id=owner_id)
                    if owner is not None:
                        return owner
                    else:
                        return self._owner
                elif owner_type == 'VIRTUAL_LINE':
                    owner = self.org.virtual_lines.get(id=owner_id)
                    if owner is not None:
                        return owner
                    else:
                        return self._owner
                elif owner_type == 'CALL_QUEUE':
                    owner = self.org.call_queues.get(id=owner_id)
                    if owner is not None:
                        return owner
                    else:
                        return self._owner
                elif owner_type == 'HUNT_GROUP':
                    owner = self.org.hunt_groups.get(id=owner_id)
                    if owner is not None:
                        return owner
                    else:
                        return self._owner
                elif owner_type == 'AUTO_ATTENDANT':
                    owner = self.org.auto_attendants.get(id=owner_id)
                    if owner is not None:
                        return owner
                    else:
                        return self._owner
                elif owner_type == 'PAGING_GROUP':
                    for group in self.org.paging_groups:
                        if group.id == owner_id:
                            return group
                    return self._owner
                elif owner_type == 'VOICEMAIL_GROUP':
                    for group in self.org.voicemail_groups:
                        if group.id == owner_id:
                            return group
                    return self._owner
                else:
                    log.warning(f'Unknown owner type "{owner_type}"')
                    return self._owner
            else:
                if self._owner['type'] == 'VOICE_MESSAGING':
                    return self.location.voice_portal
                else:
                    return "Unknown"
        else:
            return None

    def activate(self):
        """ Activate the phone number

        Returns:
            Number: The updated :class:`Number` with the new state

        """
        self.org.api.put(
            f'v1/telephony/config/locations/{self.location.id}/numbers',
            payload={'phoneNumbers': [self.phone_number]}
        )
        return True


class NumberList(UserList):
    def __init__(self, org: wxcadm.Org, location: Optional[wxcadm.Location] = None):
        super().__init__()
        self.org = org
        self.location = location
        self.data: list = self._get_data(location=location)

    def _get_data(self, location: Optional[wxcadm.Location] = None) -> list:
        data = []
        if location is not None:
            params = {'locationId': location.id}
        else:
            params = None
        response = self.org.api.get('v1/telephony/config/numbers', params=params, items_key='phoneNumbers')
        for number in response:
            this_number: Number = Number.from_dict(number)
            this_number.org = self.org
            data.append(this_number)
        return data

    def refresh(self):
        """ Refresh the list from Webex """
        self.data = self._get_data(location=self.location)
        return self

    def get(self,
            phone_number: Optional[str] = None,
            extension: Optional[str] = None,
            esn: Optional[str] = None,
            state: Optional[str] = None,
            location: Optional[wxcadm.Location] = None
            ) -> Optional[Union[Number, list]]:
        """ Find a Number or list of Number entries matching the given criteria.

        If ``'phone_number'`` or ``'esn'`` is specified, then the response will be a :class:`Number` instance or None
        if no match is found. If ``'extension'`` and ``'location'`` are specified, the response will be a
        :class:`Number` if that extension matches within the provided location. If ``'extension'`` is specified
        without a ``'location'``, a :class:`Number` instance will be returned if there is only one match. A list will
        be returned if there are multiple matches. All others will return a list or None if there are no matches.

        Args:
            phone_number (str, optional): The phone number to match.
            extension (str, optional): The extension to match.
            esn (str, optional): The ESN to match.
            state (str, optional): The state to match.
            location (wxcadm.Location, optional): The Location to match.

        Returns:
            wxcadm.Number: The matching number
            list[wxcadm.Number]: The matched numbers

        """
        if phone_number is None and extension is None and esn is None and state is None and location is None:
            raise ValueError('A parameter is required')
        # Handle the single-value searches first
        for number in self.data:
            if phone_number is not None and phone_number in number.phone_number:
                return number
            if esn is not None and esn == number.esn:
                return number
            # If an extension and a location were provided, the user is expecting a single entry
            if extension is not None and location is not None:
                if extension == number.extension and location == number.location:
                    return number
        # Then do the list-return searches
        if state is not None or location is not None or extension is not None:
            result = []
            for number in self.data:
                # Extensions can exist in more than one location
                if extension is not None and extension == number.extension:
                    result.append(number)
                if state is not None and state == number.state:
                    result.append(number)
                if location is not None and location.id == number.location.id:
                    result.append(number)
            # To handle legacy extension searches, only return the Number if it's the only one in the result
            if len(result) == 1:
                return result[0]
            else:
                return result
        return None

    def get_by_owner(self, owner):
        for number in self.data:
            if number.owner == owner:
                return number
        return None

    def add(self,
            location: wxcadm.Location,
            numbers: list,
            number_type: Optional[str] = 'DID',
            state: Optional[str] = 'ACTIVE'):
        """ Add a list of numbers to a Location

        .. note::

        This is only supported for Locations using Local Gateway or Non-integrated PSTN as the PSTN type.

        Args:
            location (Locaton): The :class:`Location` to add the numbers to
            numbers (list): A list of numbers, as strings
            number_type (str, optional): The type of numbers being added. `'TOLLFREE'` and `'DID'` are supported.
                Defaults to `DID`
            state (str, optional): The state to put the numbers in. Valid values are `'ACTIVE'` and `'INACTIVE'`.
                Defaults to `'ACTIVE'` 
            
        Returns:
            NumberList: The updated :class:`NumberList` with the newly added numbers

        Raises:
            wxcadm.APIError: Raised when the number add is rejected by Webex

        """
        payload = {
            'phoneNumbers': numbers,
            'numberType': number_type,
            'state': state
        }
        self.org.api.post(f'v1/telephony/config/locations/{location.id}/numbers', payload=payload)
        self.refresh()
        return self

    def validate(self, numbers: list):
        """ Validate a list of phone numbers prior to adding.

        Args:
            numbers (list): A list of phone numbers, each as a string

        Returns:
            dict: The validation response from Webex

        """
        response = self.org.api.post(
            f'v1/telephony/config/actions/validateNumbers/invoke',
            payload={'phoneNumbers': numbers}
        )
        return response

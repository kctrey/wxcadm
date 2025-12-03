from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .number import NumberList
from collections import UserList
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config

import wxcadm
from .common import *
from wxcadm import log


@dataclass_json
@dataclass
class PSTNProvider:
    id: str
    """ The ID of the PSTN Provider """
    name: str = field(metadata=config(field_name="displayName"))
    """ The name of the PSTN Provider"""
    services: list = field(metadata=config(field_name="pstnServices"), default_factory=list)
    """ The services offered by the PSTN Provider """


class PSTNProviderList(UserList):
    def __init__(self, location: wxcadm.Location):
        super().__init__()
        self.location = location
        self.data = []
        response = self.location.org.api.get(f'v1/telephony/pstn/locations/{self.location.id}/connectionOptions')
        for entry in response:
            self.data.append(PSTNProvider.from_dict(entry))

    def get(self, id: Optional[str] = None, name: Optional[str] = None) -> Optional[PSTNProvider]:
        """ Get a PSTN Provider by ID or Name

        Args:
            id (str, optional): The ID of the PSTN Provider
            name (str, optional): The Name of the PSTN Provider

        Returns:
            PSTNProvider: The PSTN Provider

        """
        if id is not None:
            for entry in self.data:
                if entry.id == id:
                    return entry
            return None
        if name is not None:
            for entry in self.data:
                if entry.name == name:
                    return entry
            return None
        return None


class LocationPSTN:
    def __init__(self, location: wxcadm.Location):
        self.location = location
        self.available_providers = PSTNProviderList(location)
        """ The :class:`PSTNProviderList` of available providers for the Location """
        log.info(f"Getting PSTN information for Location: {self.location.name}")
        try:
            response = self.location.org.api.get(f'v1/telephony/pstn/locations/{self.location.id}/connection')
            log.debug(f"Response: {response}")
            self.provider = PSTNProvider.from_dict(response)
            self.type = response['pstnConnectionType']
        except wxcadm.APIError as e:
            if "PSTN for the location is not configured" in e.args[0].get('errorMessage', ''):
                log.info("No PSTN configured for Location")
                self.provider = None
            else:
                log.warning(f"API Error: {e.args}")
                raise e

    def set_provider(self, provider: Union[PSTNProvider, str, wxcadm.RouteGroup, wxcadm.Trunk]):
        """ Set the PSTN Provider for the Location

        The Provider can be expressed as a string, which is the Provider's ID, a :class:`PSTNProvider`, a
        :class:`~.routing.Trunk` or a :class:`~.routing.RouteGroup`.

        Args:
            provider (str, PSTNProvider, RouteGroup, Trunk): The new Provider, Route Group or Trunk to use

        Returns:
            bool: True on success, False otherwise

        """
        log.info(f"Setting new PSTN Provider for Location {self.location.name}")
        if isinstance(provider, str):
            provider = self.available_providers.get(id=provider)
            if provider is None:
                raise ValueError(f"Provider with ID {provider} not found")
        if isinstance(provider, wxcadm.Trunk) or isinstance(provider, wxcadm.RouteGroup):
            if isinstance(provider, wxcadm.Trunk):
                payload = {
                    'premiseRouteType': 'TRUNK'
                }
            else:
                payload = {
                    'premiseRouteType': 'ROUTE_GROUP'
                }
            payload['premiseRouteId'] = provider.id
        else:
            payload = {
                'id': provider.id,
            }
        self.location.org.api.put(
            f"v1/telephony/pstn/locations/{self.location.id}/connection",
            payload=payload
        )
        self.provider = provider
        return True

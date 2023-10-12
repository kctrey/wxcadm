from __future__ import annotations

import humps

import wxcadm.location
from wxcadm import log
from .common import *
from .exceptions import PutError


class RealtimeClass:
    def __init__(self):
        data: dict = webex_api_call('get', self.data_url)
        for key, val in data.items():
            self.__setattr__(humps.decamelize(key), val)
            self._api_fields.append(humps.decamelize(key))
        self._initialized = True

    def config_json(self) -> dict:
        return_dict = {}
        for field in self._api_fields:
            value = self.__getattribute__(field)
            return_dict[humps.camelize(field)] = value
        return return_dict

    def __setattr__(self, name, value):
        if self._initialized:
            old_val = self.__getattribute__(name)
            log.info(f"Changing {name} from {old_val} to {value}")
            object.__setattr__(self, name, value)
            try:
                webex_api_call('put', self.data_url,
                               payload=self.config_json())
            except wxcadm.exceptions.APIError as e:
                log.warning("The change failed.")
                object.__setattr__(self, name, old_val)
                raise PutError(e)
        else:
            object.__setattr__(self, name, value)
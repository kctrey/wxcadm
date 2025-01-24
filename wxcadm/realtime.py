from __future__ import annotations

import humps

import wxcadm.location
from wxcadm import log
from .common import *
from .exceptions import PutError


class RealtimeClass:
    def __init__(self):
        data: dict = webex_api_call('get', self.data_url)
        log.debug(f"[RealTime] Received {data}")
        for key, val in data.items():
            log.debug(f"[RealTime] Setting {key} to {val}")
            self.__setattr__(humps.decamelize(key), val)
            self._api_fields.append(humps.decamelize(key))
        self._initialized = True

    def config_json(self) -> dict:
        return_dict = {}
        for field in self._api_fields:
            value = self.__getattribute__(field)
            log.debug(f"[RealTime] Adding {field} to payload")
            return_dict[humps.camelize(field)] = value
        log.debug(f"[RealTime] Returning {return_dict}")
        return return_dict

    def __setattr__(self, name, value):
        if self._initialized:
            old_val = self.__getattribute__(name)
            log.info(f"[RealTime] Changing {name} from {old_val} to {value}")
            object.__setattr__(self, name, value)
            try:
                webex_api_call('put', self.data_url,
                               payload=self.config_json())
            except wxcadm.exceptions.APIError as e:
                log.warning("[RealTime] The change failed.")
                object.__setattr__(self, name, old_val)
                raise PutError(e)
        else:
            object.__setattr__(self, name, value)
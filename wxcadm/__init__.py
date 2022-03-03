name = 'wxcadm'

import logging

from .wxcadm import Webex, RedSky, XSIEvents, XSICallQueue
from .exceptions import (
    OrgError, LicenseError, APIError, TokenError,
    PutError, XSIError, NotAllowed, CSDMError
)

# Set up logging
logging.basicConfig(level=logging.INFO,
                    filename="./wxcadm.log",
                    format='%(asctime)s %(module)s:%(levelname)s:%(message)s')
# Since requests is so chatty at Debug, turn off logging propagation
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)

def set_logging_level(level: str):
    """ Sets the logging level

    Args:
        level (str): Valid values are ``none``, ``debug``, ``info``, ``warn``, ``error``, and ``critical``

    Returns:
        bool: True if successful. All other conditions raise an exception.

    Raises:
        ValueError: Raised if the level value does not match the valid values.

    """
    if level.lower() == "none":
        new_level = "NOTSET"
    elif level.lower() == "debug":
        new_level = "DEBUG"
    elif level.lower() == "info":
        new_level = "INFO"
    elif level.lower() == "warn":
        new_level = "WARN"
    elif level.lower() == "error":
        new_level = "ERROR"
    elif level.lower() == "critical":
        new_level = "CRITICAL"
    else:
        raise ValueError(f"{level} is not a valid logging level")
    logging.getLogger().setLevel(new_level)
    return True


name = 'wxcadm'

import logging

from .wxcadm import Webex, RedSky, XSIEvents, XSICallQueue
from .exceptions import (
    OrgError, LicenseError, APIError, TokenError,
    PutError, XSIError, NotAllowed, CSDMError
)

# Set up NullHandler for logging
logging.getLogger(name).addHandler(logging.NullHandler())

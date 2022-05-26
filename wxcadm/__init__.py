import logging

from .wxcadm import Webex, RedSky, XSIEvents, XSICallQueue
from .exceptions import (
    OrgError, LicenseError, APIError, TokenError,
    PutError, XSIError, NotAllowed, CSDMError
)

from .common import decode_spark_id
from .wxcadm import console_logging

# Set up NullHandler for logging
logging.getLogger(__name__).addHandler(logging.NullHandler())

name = 'wxcadm'

import logging

from .wxcadm import Webex, RedSky
from .exceptions import (
    OrgError, LicenseError, APIError, TokenError,
    PutError, XSIError, NotAllowed, CSDMError
)

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    filename="./wxcadm.log",
                    format='%(asctime)s %(module)s:%(levelname)s:%(message)s')
# Since requests is so chatty at Debug, turn off logging propagation
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)
from __future__ import annotations

import logging

# Set up NullHandler for logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())

from .webex import Webex
from .xsi import XSIEvents, Call, XSI
from .exceptions import *
from .common import *




from requests import Response
import xmltodict
from typing import Optional


class XSIResponse:
    def __init__(self, response: Response):
        self.raw_response = response.json()
        self.summary: Optional[str] = None
        self.

        if self.raw_response.get('ErrorInfo'):
            self.summary = self.raw_response['ErrorInfo']['summary']['$']
        if response.ok:
            self.success = True
        else:
            self.success = False

    def __bool__(self):
        if self.success is True:
            return True
        else:
            return False

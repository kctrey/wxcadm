from requests import Response
import xmltodict
from typing import Optional


class XSIResponse:
    """ An XSIResponse is returned by Webex for all XSI commands """
    def __init__(self, response: Response):
        self.raw_response = response.json()
        """ The raw response dict """
        self.summary: Optional[str] = None
        """ Summary text for errors """
        self.success: bool = False
        """ Whether or not the command was successful """

        if self.raw_response.get('ErrorInfo'):
            self.summary = self.raw_response['ErrorInfo']['summary']['$']
        if response.ok:
            self.success = True
        else:
            self.success = False

    def __bool__(self):
        """ True when self.success is True """
        if self.success is True:
            return True
        else:
            return False

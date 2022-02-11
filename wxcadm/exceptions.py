class OrgError(Exception):
    pass


class LicenseError(OrgError):
    """Exceptions dealing with License problems within the Org"""
    pass


class APIError(Exception):
    """The base class for any exceptions dealing with the API"""
    pass


class TokenError(APIError):
    """Exceptions dealing with the Access Token itself"""
    pass


class PutError(APIError):
    """Exception class for problems putting values back into Webex"""
    pass


class XSIError(APIError):
    """Exception class for problems with the XSI API. Serves as a base class for other errors."""
    pass

class NotAllowed(XSIError):
    """Exception class for XSI actions that are not allowed by the platform due to user settings"""
    pass

class CSDMError(APIError):
    def __init__(self, message):
        super().__init__(message)


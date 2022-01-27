class OrgError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LicenseError(OrgError):
    def __init__(self, message):
        """Exceptions dealing with License problems within the Org"""
        super().__init__(message)


class APIError(Exception):
    def __init__(self, message):
        """The base class for any exceptions dealing with the API"""
        super().__init__(message)


class TokenError(APIError):
    def __init__(self, message):
        """Exceptions dealing with the Access Token itself"""
        super().__init__(message)


class PutError(APIError):
    def __init__(self, message):
        """Exception class for problems putting values back into Webex"""
        super().__init__(message)


class XSIError(APIError):
    def __init__(self, message):
        """Exception class for problems with the XSI API. Serves as a base class for other errors."""
        super().__init__(message)

class NotAllowed(XSIError):
    def __init__(self, message):
        """Exception class for XSI actions that are not allowed by the platform due to user settings"""
        super().__init__(message)

class CSDMError(APIError):
    def __init__(self, message):
        super().__init__(message)


from builtins import Exception

__all__ = ['OrgError', 'LicenseError', 'APIError', 'TokenError', 'PutError', 'XSIError', 'NotAllowed', 'CSDMError',
           'LicenseOverageError', 'NotSubscribedForLicenseError']


class OrgError(Exception):
    """The base error class for Org-related exceptions"""
    def __init__(self, message):
        super(OrgError, self).__init__(message)


class LicenseError(OrgError):
    """Exceptions dealing with License problems within the Org"""
    def __init__(self, message):
        super(LicenseError, self).__init__(message)

class NotSubscribedForLicenseError(LicenseError):
    """ An exception indicating that the user is not subscribed to a license for the given feature."""
    def __init__(self, message):
        super(NotSubscribedForLicenseError, self).__init__(message)

class LicenseOverageError(LicenseError):
    """ An exception indicating that the user has exceeded the license limit for the given feature."""
    def __init__(self, message):
        super(LicenseOverageError, self).__init__(message)

class APIError(Exception):
    """The base class for any exceptions dealing with the API"""
    def __init__(self, message):
        super(APIError, self).__init__(message)


class TokenError(APIError):
    """Exceptions dealing with the Access Token itself"""
    def __init__(self, message):
        super(TokenError, self).__init__(message)


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

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .person import Person
from collections import UserList

import wxcadm.org
from wxcadm import log
from .common import *
from .location import Location


class NumberManagementJob:
    """ The class for Number Moves.

    This class is never instantiated directly. It is created with the :class:`NumberMoveJobList`

    """

    def __init__(self, parent: wxcadm.Org, id: str, details: Optional[dict] = None):
        self.parent = parent
        self.id = id
        """ The Number Move Job ID """
        self.details: dict
        """ The full details of the Number Move Job from Webex """
        if details is None:
            self.details = self._get_details()
        else:
            self.details = details

    def _get_details(self):
        response = webex_api_call('get', f'v1/telephony/config/jobs/numbers/manageNumbers/{self.id}')
        return response

    @property
    def completed(self) -> bool:
        """ Whether the job has completed execution

        Note that this does not indicate that the job was successful. The :attr:`success` attribute should be used to
        determine whether the job was successful or not

        """
        self.details = self._get_details()
        if self.details['latestExecutionStatus'] == 'COMPLETED':
            return True
        else:
            return False

    @property
    def success(self) -> bool:
        """ Whether the job was successful

        This property will return False even if the job is not complete. It should really be called only after
        :attr:`completed` is True

        """
        self.details = self._get_details()
        if int(self.details['counts']['numbersFailed']) > 0:
            return False

        total_numbers = int(self.details['counts']['totalNumbers'])
        success_total = int(self.details['counts']['numbersDeleted']) + int(self.details['counts']['numbersMoved'])

        if success_total == total_numbers:
            return True
        else:
            return False


class NumberManagementJobList(UserList):
    _endpoint = "v1/telephony/config/jobs/numbers/manageNumbers"
    _endpoint_items_key = "items"
    _item_endpoint = "v1/telephony/config/jobs/numbers/manageNumbers/{item_id}"
    _item_class = NumberManagementJob

    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing NumberMoveJobList")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_data()

    def _get_data(self) -> list:
        log.debug("_get_data() started")
        params = {}

        if isinstance(self.parent, wxcadm.Org):
            log.debug(f"Using Org ID {self.parent.id} as Data filter")
            params['orgId'] = self.parent.id
            params['max'] = 1000
        else:
            log.warn("Parent class is not Org so all items will be returned")
        response = webex_api_call('get', self._endpoint, params=params)
        log.info(f"Found {len(response)} items")

        items = []
        for entry in response:
            items.append(self._item_class(parent=self.parent, id=entry['id'], details=entry))
        return items

    def refresh(self):
        """ Refresh the list of instances from Webex

        Returns:
            bool: True on success, False otherwise.

        """
        self.data = self._get_data()
        return True

    def get(self, id: str):
        """ Get the instance associated with a given Job ID

        Args:
            id (str, optional): The Number Management Job ID to find

        Returns:
            NumberManagementJob: The Number Management Job instance correlating with the given ID

        """
        for item in self.data:
            if item.id == id:
                return item
        return None

    def create(self,
               job_type: str,
               target_location: wxcadm.Location | str,
               numbers: list
               ):
        """ Create a Number Management Job

        .. note::

            At this time, only the "move" value is accepted for the `job_type` argument, because Webex only supports
            move operations via the API. Also, the API currently limits a Number Move to a single number per job. The
            API schema is written to support more, so it may be supported at some point, but for now, the `numbers` list
            must contain only a single entry.

        Args:
            job_type (str): Only "move" is supported currently
            target_location (Location | str): A :class:`Location` instance or a string representing the Location ID to
            move the numbers to
            numbers (list[str]): A list of numbers, as strings, to move to the target Location

        Returns:
            NumberManagementJob: The created NumberManagementJob

        """
        # Determine if the numbers are valid
        numbers_to_move = []
        # Get a copy of the Org numbers for processing
        org_numbers = self.parent.numbers
        for number in numbers:
            number_found = False
            for org_number in org_numbers:
                if number in org_number.get('phoneNumber', ''):
                    number_found = True
                    numbers_to_move.append(org_number)
            if number_found is False:
                raise KeyError(f"{number} was not found in the Org")

        if isinstance(target_location, wxcadm.Location):
            target_location_id = target_location.id
        else:
            target_location_id = target_location

        # Build the payload for the move job
        payload = {'operation': 'MOVE', 'targetLocationId': target_location_id, 'numberList': []}
        for number in numbers_to_move:
            payload['numberList'].append({'locationId': number['location'].id, 'numbers': [number['phoneNumber']]})

        response = wxcadm.webex_api_call('post', 'v1/telephony/config/jobs/numbers/manageNumbers',
                                         params={'orgId': self.parent.id},
                                         payload=payload)
        job_id = response['id']
        return NumberManagementJob(parent=self.parent, id=job_id)


class UserMoveJob:
    """ The class for User Location Moves

    This class is never instantiated directly. It is created with the :class:`UserMoveJobList`

    """

    def __init__(self, parent: wxcadm.Org, id: str, details: Optional[dict] = None):
        self.parent = parent
        self.id = id
        """ The User Move Job ID """
        self.details: dict
        """ The full details of the User Move Job from Webex """
        if details is None:
            self.details = self._get_details()
        else:
            self.details = details

    def _get_details(self):
        response = webex_api_call('get', f'v1/telephony/config/jobs/person/moveLocation/{self.id}')
        return response

    @property
    def completed(self) -> bool:
        """ Whether the job has completed execution

        Note that this does not indicate that the job was successful. The :attr:`success` attribute should be used to
        determine whether the job was successful or not

        """
        self.details = self._get_details()
        if self.details['latestExecutionStatus'] == 'COMPLETED':
            return True
        else:
            return False

    @property
    def success(self) -> bool:
        """ Whether the job was successful

        This property will return False even if the job is not complete. It should really be called only after
        :attr:`completed` is True

        """
        self.details = self._get_details()
        if int(self.details['counts']['failed']) > 0:
            return False

        total_numbers = int(self.details['counts']['totalMoves'])
        success_total = int(self.details['counts']['moved'])

        if success_total == total_numbers:
            return True
        else:
            return False


class UserMoveJobList(UserList):
    _endpoint = "v1/telephony/config/jobs/person/moveLocation"
    _endpoint_items_key = "items"
    _item_endpoint = "v1/telephony/config/jobs/person/moveLocation/{item_id}"
    _item_class = UserMoveJob

    def __init__(self, parent: wxcadm.Org):
        super().__init__()
        log.debug("Initializing UserMoveJobList")
        self.parent: wxcadm.Org = parent
        self.data: list = self._get_data()

    def _get_data(self) -> list:
        log.debug("_get_data() started")
        params = {}

        if isinstance(self.parent, wxcadm.Org):
            log.debug(f"Using Org ID {self.parent.id} as Data filter")
            params['orgId'] = self.parent.id
            params['max'] = 1000
        else:
            log.warn("Parent class is not Org so all items will be returned")
        response = webex_api_call('get', self._endpoint, params=params)
        log.info(f"Found {len(response)} items")

        items = []
        for entry in response:
            items.append(self._item_class(parent=self.parent, id=entry['id'], details=entry))
        return items

    def refresh(self):
        """ Refresh the list of instances from Webex

        Returns:
            bool: True on success, False otherwise.

        """
        self.data = self._get_data()
        return True

    def get(self, id: str):
        """ Get the instance associated with a given Job ID

        Args:
            id (str, optional): The Number Management Job ID to find

        Returns:
            NumberManagementJob: The Number Management Job instance correlating with the given ID

        """
        for item in self.data:
            if item.id == id:
                return item
        return None

    def create(self,
               target_location: wxcadm.Location | str,
               people: list[wxcadm.person.Person],
               validate_only: Optional[bool] = False
               ):
        """ Create a Number Management Job

        .. note::

            At this time, the API currently limits a User Move to a single user per job. The
            API schema is written to support more, so it may be supported at some point, but for now, the `users` list
            must contain only a single entry.

        Args:
            target_location (Location | str): A :class:`Location` instance or a string representing the Location ID to
            move the numbers to
            people (list[Person]): A list of :class:`Person` instances to move to the target Location
            validate_only (bool, optional): Whether to only perform the validation of the User Move, not actually move
            the users. Defaults to False. False wll perform both a validation and create a User Move Job

        Returns:
            UserMoveValidationResults: The Results of the validation for the User Move
            UserMoveJob: The created UserMoveJob (if `validate_only` is not True and the validation succeeds). If
            validation fails, None will be returned.

        """
        log.info(f"Creating User Move Job")
        if isinstance(target_location, wxcadm.Location):
            target_location_id = target_location.id
        else:
            target_location_id = target_location

        # If we create a job, we'll store it. Otherwise, we'll return None
        user_move_job = None

        # Build the payload for the move job validation
        payload = {'usersList': []}
        for person in people:
            person_payload = {'locationId': target_location_id,
                              'validate': True,
                              'users': [{'userId': person.id, 'extension': person.extension}]}
            payload['usersList'].append(person_payload)

        validation_results = UserMoveValidationResults()
        try:
            response = wxcadm.webex_api_call('post', 'v1/telephony/config/jobs/person/moveLocation',
                                             params={'orgId': self.parent.id},
                                             payload=payload)
        except wxcadm.exceptions.APIError as e:
            log.debug(f"Webex returned an error to Number Move Validation: {e}")

            error_code = e.args[0]['errors'][0]['code']
            error_message = e.args[0]['errors'][0]['message']
            validation_results.add_message('error', error_code, error_message)
        else:
            if 'errors' in response['response']['usersList'][0].keys():
                for error in response['response']['usersList'][0]['errors']:
                    validation_results.add_message('error', error['code'], error['message'])
            if 'impacts' in response['response']['usersList'][0].keys():
                for impact in response['response']['usersList'][0]['impacts']:
                    validation_results.add_message('impact', impact['code'], impact['message'])

        # Create the job if the validation worked and if we weren't asked to only validate
        if validation_results.passed is True and validate_only is not True:
            log.debug(f"Validation passed and Move requested. Creating UserMoveJob call.")
            payload['usersList'][0]['validate'] = False
            try:
                response = wxcadm.webex_api_call('post', 'v1/telephony/config/jobs/person/moveLocation',
                                                 params={'orgId': self.parent.id},
                                                 payload=payload)
            except wxcadm.exceptions.APIError as e:
                log.debug(f"Webex returned an error to Number Move Validation: {str(e)}")
            else:
                log.debug(f"API response: {response}")
                job_id = response['response']['jobDetails']['id']
                log.debug(f"Received Job ID {job_id}")
                self.refresh()
                user_move_job = UserMoveJob(parent=self.parent, id=job_id)

        return validation_results, user_move_job


class UserMoveValidationResults:
    def __init__(self):
        self.messages = []
        """ The messages and their severity. A severity of `error` will prevent the Use Move from being completed. """

    def add_message(self, severity: str, code: Optional[str] = None, message: Optional[str] = None):
        """ Add a message to the Validation Results

        Args:
            severity (str): Either 'error' or 'impact'
            code (str, optional): The code assigned to the error.
            message (str, optional): The validation message

        Returns:
            bool: Always True

        """
        self.messages.append({'severity': severity, 'code': code, 'message': message})
        return True

    @property
    def passed(self) -> bool:
        """ Whether the validation passed with no errors and the User Move would be successful """
        for message in self.messages:
            if message['severity'].lower() == 'error':
                return False
        return True

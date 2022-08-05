from __future__ import annotations

from wxcadm import log


class Location:
    def __init__(self, parent: Org, location_id: str, name: str, address: dict = None):
        """Initialize a Location instance

        .. note::
            Location instances are normally not instantiated manually and are done automatically with the
            :meth:`Org.get_locations` method.

        Args:
            location_id (str): The Webex ID of the Location
            name (str): The name of the Location
            address (dict): The address information for the Location

        Returns:
             Location (object): The Location instance

        """
        self._parent = parent
        self._headers = parent._headers
        self.id: str = location_id
        """The Webex ID of the Location"""
        self.name: str = name
        """The name of the Location"""
        self.address: dict = address
        """The address of the Location"""

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    @property
    def spark_id(self):
        """The ID used by all of the underlying services."""
        return decode_spark_id(self.id)

    @property
    def hunt_groups(self):
        """List of HuntGroup instances for this Location"""
        my_hunt_groups = []
        for hg in self._parent.hunt_groups:
            if hg.location == self.id:
                my_hunt_groups.append(hg)
        return my_hunt_groups

    @property
    def call_queues(self):
        """List of CallQueue instances for this Location"""
        my_call_queues = []
        for cq in self._parent.call_queues:
            if cq.location_id == self.id:
                my_call_queues.append(cq)
        return my_call_queues

    @property
    def available_numbers(self):
        """Returns all of the available numbers for the Location.

        Only returns active numbers, so numbers that have not been activated yet will not be returned.

        Returns:
            list[dict]: A list of available numbers, in dict form

        """
        available_numbers = []
        for number in self._parent.numbers:
            if number['location'].name == self.name \
                    and number.get('state', "") == "ACTIVE" \
                    and number.get('owner', False) is False:
                available_numbers.append(number)
        return available_numbers

    @property
    def main_number(self):
        """Returns the Main Number for this Location, if defined

        Returns:
            str: The main number for the Location. None is returned if a main number cannot be found.

        """
        for number in self._parent.numbers:
            if number['location'].name == self.name and number['mainNumber'] is True:
                return number['number']
        return None

    @property
    def schedules(self):
        """ List of all of the :class:`wxcadm.LocationSchedule` instances for this Location"""
        response = []
        api_resp = webex_api_call("get", f"v1/telephony/config/locations/{self.id}/schedules", headers=self._headers)
        for schedule in api_resp['schedules']:
            this_schedule = LocationSchedule(self, schedule['id'], schedule['name'], schedule['type'])
            response.append(this_schedule)
        return response

    def upload_moh_file(self, filename: str):
        """ Upload and activate a custom Music On Hold audio file.

        The audio file must be a WAV file that conforms with the Webex Calling requirements. It is recommended to test
        any WAV file by manually uploading it to a Location in Control Hub. The method will return False if the WAV file
        is rejected by Webex.

        Args:
            filename (str): The filename, including path, to the WAV file to upload.

        Returns:
            bool: True on success, False otherwise

        .. warning::

            This method requires the CP-API access scope.

        """
        upload = self._parent._cpapi.upload_moh_file(self.id, filename)
        if upload is True:
            activate = self._parent._cpapi.set_custom_moh(self.id, filename)
            if activate is True:
                return True
            else:
                return False
        else:
            return False

    def set_default_moh(self):
        """ Set the MOH to be the Webex Calling system default music.

        Returns:
            bool: True on success, False otherwise

        .. warning::

            This method requires the CP-API access scope.
        """
        activate = self._parent._cpapi.set_default_moh(self.id)
        if activate is True:
            return True
        else:
            return False

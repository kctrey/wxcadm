from __future__ import annotations

from dataclasses import dataclass, field
from wxcadm import log


class PickupGroup:
    def __init__(self, parent, location, id, name, users=None):
        self._parent: object = parent
        self.location_id: str = location
        """The Webex ID of the Location associated with this Pickup Group"""
        self.id: str = id
        """The Webex ID of the Pickup Group"""
        self.name: str = name
        """The name of the Pickup Group"""
        self.users: list = []
        """All of the users (agents) assigned to this Pickup Group"""
        # If no agents were passed, we need to go get the configuration of the PickupGroup
        if users is None:
            response = webex_api_call("get", f"v1/telephony/config/locations/{self.location_id}/callPickups/{self.id}")
            # TODO It doesn't make sense to create a new Person instance for the below.
            #      Once we have an API and a class for Workspaces, it would make sense to tie
            #      the agents to the Person or Workspace instance
            # For now, we just write the values that we get back and the user can find the people with the
            # Person-specific methods
            for agent in response['agents']:
                self.users.append(agent)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def get_config(self):
        """Gets the configuration of the Pickup Group from Webex

        Returns:
            dict: The configuration of the Pickup Group

        """
        config = {**self}
        return config


class CallQueue:
    def __init__(self, parent, id, name, location, phone_number, extension, enabled, get_config=True):
        """
        .. note::
            CallQueue instances are normally not instantiated manually and are done automatically with the
            :meth:`Org.get_call_queues` method.

        """
        self._parent: Org = parent
        """The parent org of this Call Queue"""
        self.id: str = id
        """The Webex ID of the Call Queue"""
        self.name: str = name
        """The name of the Call Queue"""
        self.location_id: str = location
        """The Webex ID of the Location associated with this Call Queue"""
        self.phone_number: str = phone_number
        """The DID of the Call Queue"""
        self.extension: str = extension
        """The extension of the Call Queue"""
        self.enabled: bool = enabled
        """True if the Call Queue is enabled. False if disabled"""
        self.call_forwarding: dict = {}
        """The Call Forwarding config for the Call Queue"""
        self.config: dict = {}
        """The configuration dictionary for the Call Queue"""
        self.spark_id: str = decode_spark_id(self.id)
        """ The Spark IS for the CallQueue"""

        if get_config:
            self.get_queue_config()
            self.get_queue_forwarding()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def get_queue_config(self):
        """Get the configuration of this Call Queue instance

        Returns:
            CallQueue.config: The config dictionary of this Call Queue

        """
        r = requests.get(_url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id,
                         headers=self._parent._headers)
        response = r.json()
        self.config = response
        return self.config

    def get_queue_forwarding(self):
        """Get the Call Forwarding settings for this Call Queue instance

        Returns:
            CallQueue.call_forwarding: The Call Forwarding settings for the Person

        """
        # TODO: The rules within Call Forwarding are weird. The rules come back in this call, but they are
        #       different than the /selectiveRules response. It makes sense to aggregate them, but that probably
        #       requires the object->JSON mapping that we need to do for all classes
        r = requests.get(_url_base + "v1/telephony/config/locations/" + self.location_id +
                         "/queues/" + self.id + "/callForwarding",
                         headers=self._parent._headers)
        response = r.json()
        self.call_forwarding = response
        return self.call_forwarding

    def push(self):
        """Push the contents of the CallQueue.config back to Webex

        Returns:
            CallQueue.config: The updated config attribute pulled from Webex after pushing the change

        """
        # TODO: Right now this only pushes .config. It should also push .call_forwarding and .forwarding_rules
        log.info(f"Pushing Call Queue config to Webex for {self.name}")
        url = _url_base + "v1/telephony/config/locations/" + self.location_id + "/queues/" + self.id
        r = requests.put(url,
                         headers=self._parent._headers, json=self.config)
        response = r.status_code
        self.get_queue_config()
        return self.config


class HuntGroup:
    def __init__(self, parent: Org,
                 id: str,
                 name: str,
                 location: str,
                 enabled: bool,
                 phone_number: str = None,
                 extension: str = None,
                 config: bool = True
                 ):
        """Initialize a HuntGroup instance

        .. note::
            HuntGroup instances are normally not instantiated manually and are done automatically with the
            :meth:`Org.get_hunt_groups` method.

        Args:
            parent (Org): The Org instance to which the Hunt Group belongs
            id (str): The Webex ID for the Hunt Group
            name (str): The name of the Hunt Group
            location (str): The Location ID associated with the Hunt Group
            enabled (bool): Boolean indicating whether the Hunt Group is enabled
            phone_number (str, optional): The DID for the Hunt Group
            extension (str, optional): The extension of the Hunt Group

        Returns:
            HuntGroup: The HuntGroup instance

        """

        # Instance attrs
        self.parent: Org = parent
        self.id: str = id
        """The Webex ID of the Hunt Group"""
        self.name: str = name
        """The name of the Hunt Group"""
        self.location_id: str = location
        """The Location ID associated with the Hunt Group"""
        self.enabled: bool = enabled
        """Whether the Hunt Group is enabled or not"""
        self.phone_number: str = phone_number
        """The DID for the Hunt Group"""
        self.extension: str = extension
        """The extension of the Hunt Group"""
        self.agents: list = []
        """List of agents/users assigned to this Hunt Group"""
        self.distinctive_ring: bool = False
        """Whether or not the Hunt Group has Distinctive Ring enabled"""
        self.alternate_numbers_settings: dict = {}
        """List of alternate numbers for this Hunt Group"""
        self.language: str = ""
        """The language name for the Hunt Group"""
        self.language_code: str = ""
        """The short name for the language of the Hunt Group"""
        self.first_name: str = ""
        """The Caller ID first name for the Hunt Group"""
        self.last_name: str = ""
        """The Caller ID last name for the Hunt Group"""
        self.time_zone: str = ""
        """The time zone for the Hunt Group"""
        self.call_policy: dict = {}
        """The Call Policy for the Hunt Group"""
        self.agents: list = []
        """List of users assigned to this Hunt Group"""
        self.raw_config: dict = {}
        """The raw JSON-to-Python config from Webex"""

        # Get the config unless we are asked not to
        if config:
            log.info(f"Getting config for Hunt Group {self.id} in Location {self.location_id}")
            self.get_config()

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.id

    def get_config(self):
        """Get the Hunt Group config, including agents"""
        r = requests.get(_url_base + f"v1/telephony/config/locations/{self.location_id}/huntGroups/{self.id}",
                         headers=self.parent._headers)
        response = r.json()
        self.raw_config = response
        self.agents = response['agents']
        self.distinctive_ring = response.get("distinctiveRing", False)
        self.alternate_numbers_settings = response['alternateNumberSettings']
        self.language = response['language']
        self.language_code = response['languageCode']
        self.first_name = response['firstName']
        self.last_name = response['lastName']
        self.time_zone = response['timeZone']
        self.call_policy = response['callPolicies']

        return self.raw_config

@dataclass
class AutoAttendant:
    """ Class for AutoAttedants within a :class:`wxcadm.Org`

    Inititalizing the instance will automatically fetch the AutoAttendant details from Webex

    .. note::
            AutoAttendant instances are normally not instantiated manually and are done automatically with the
            :meth:`Org.get_auto_attendants` method.

    Args:
        parent (Org): The :class:`wxcadm.Org` instance to which the AutoAttendant belongs
        locaton (Location): The :class:`Location` instance associated with the AutoAttendant
        id (str): The Webex ID of the AutoAttendant
        name (str): The name of the AutoAttendant

    """
    parent: Org
    """ The Org instance that ows this AutoAttendant """
    location: Location
    """ The Location instance to which this AutoAttendant belongs"""
    id: str
    """ The Webex ID of the AutoAttendant """
    name: str
    """ The name of the AutoAttendant """

    config: dict = field(init=False, repr=False)
    """ The configuration dict returned by Webex """
    call_forwarding: dict = field(init=False, repr=False)
    """ The Call Forwarding config returned by Webex """
    cf_rules: dict = field(init=False, repr=False)
    """ The Call Forwarding rules returned by Webex """
    spark_id: str = field(init=False, repr=False)

    def __post_init__(self):
        self.spark_id = decode_spark_id(self.id)
        api_resp = webex_api_call("get", f"v1/telephony/config/locations/{self.location.id}/autoAttendants/{self.id}",
                                  headers=self.parent._headers)
        self.config = api_resp
        api_resp = webex_api_call("get", f"v1/telephony/config/locations/{self.location.id}/autoAttendants/{self.id}"
                                         f"/callForwarding",
                                  headers=self.parent._headers)
        self.call_forwarding = api_resp
        for rule in self.call_forwarding['callForwarding']['rules']:
            api_resp = webex_api_call("get",
                                      f"v1/telephony/config/locations/{self.location.id}/autoAttendants/{self.id}/"
                                      f"callForwarding/selectiveRules/{rule['id']}",
                                      headers=self.parent._headers)
            self.cf_rules = api_resp

    def copy_menu_from_template(self, source: object, menu_type: str = "both"):
        """ Copy the Business Hours, After Hours, or both menus from another :class:`AutoAttendant` instance.

        Note that this copy functionality will not work (yet) if the source Auto Attendant uses a CUSTOM announcement,
        which, unfortunately, is most of them. The Webex API should support this soon, but, until them, the method's
        usefulness is limited.

        Args:
            source (AutoAttendant): The source :class:`AutoAttendant` instance to copy from
            menu_type (str, optional): The menu to copy. 'business_hours', 'after_hours' or 'both' are valid. Defaults
                to 'both'.

        Returns:
            bool: True on success. False otherwise.

        Raises:
            ValueError: Raised when the menu_type value is not one of the accepted values.

        """
        if menu_type.lower() == "both":
            self.config['businessHoursMenu'] = source.config['businessHoursMenu']
            self.config['afterHoursMenu'] = source.config['afterHoursMenu']
        elif menu_type.lower() == "business_hours":
            self.config['businessHoursMenu'] = source.config['businessHoursMenu']
        elif menu_type.lower() == "after_hours":
            self.config['afterHoursMenu'] = source.config['afterHoursMenu']
        else:
            raise ValueError(f"{menu_type} must be 'business_hours', 'after_hours' or 'both'")

        resp = webex_api_call("put", f"v1/telephony/config/locations/{self.location.id}/autoAttendants/{self.id}",
                              headers=self.parent._headers, payload=self.config)
        if resp:
            return True
        else:
            return False

    def upload_greeting(self, type: str, filename: str) -> bool:
        """ Upload a new greeting to the Auto Attendant

        This method takes a WAV file name, including path, and uploads the file to the Auto Attendant. The file must be
        in the correct format or it will be rejected by Webex.

        Args:
            type (str): The type of greeting. Valid values are 'business_hours' or 'after_hours'.
            filename (str): The file name, including the path, to upload to Webex

        Returns:
            bool: True on success, False otherwise.

        .. warning::

            This method requires the CP-API access scope.

        """
        if type not in ['business_hours', 'after_hours']:
            raise ValueError("Valid type values are 'business_hours' and 'after_hours'")

        cpapi = self.parent._cpapi
        success = cpapi.upload_aa_greeting(self, type, filename)
        if success is True:
            success = cpapi.set_custom_aa_greeting(self, type, filename)
            if success is True:
                return True
            else:
                return False
        else:
            return False


@dataclass
class PagingGroup:
    parent: Location
    id: str
    name: str
    spark_id: str = field(init=False, repr=False)
    config: dict = field(init=False, repr=False)

    def __post_init__(self):
        self.spark_id = decode_spark_id(self.id)
        self.refresh_config()

    def refresh_config(self):
        """ Pull a fresh copy of the Paging Group config from Webex, in case it has changed. """
        api_resp: dict = webex_api_call("get", f"v1/telephony/config/locations/{self.parent.id}/paging/"
                                        f"{self.id}",
                                        headers=self.parent._headers)
        self.config = api_resp


@dataclass
class LocationSchedule:
    """ The class for Location Schedules within a :class:`Location`

    When the instance is initialized, it will fetch the configuration from Webex.

    .. note::
            LocationSchedule instances are normally not instantiated manually and are done automatically with the
            :attr:`Location.schedules` property.

    Args:
        parent (Location): The `Location` instance to which the LocationSchedule is assigned.
        id (str): The Webex ID of the LocationSchedule
        name (str): The name of the LocationSchedule
        type (str): The type of LocationShedule, either 'businessHours' or 'Holidays'

    """
    parent: Location
    """ The `Location` instance to which the LocationSchedule is assigned """
    id: str
    """ The Webex ID of the LocationSchedule """
    name: str
    """ The name of the LocationSchedule """
    type: str
    """ The type of LocationSchedule, either 'businessHours' or 'Holidays' """
    config: dict = field(init=False, repr=False)
    """ The configuration returned by Webex """

    def __post_init__(self):
        self.refresh_config()

    def refresh_config(self):
        """ Pull a fresh copy of the schedule configuration from Webex, in case it has changed. """
        api_resp = webex_api_call("get", f"v1/telephony/config/locations/{self.parent.id}/schedules/"
                                         f"{self.type}/{self.id}",
                                  headers=self.parent._headers)
        self.config = api_resp

    def add_holiday(self, name: str, date: str, recur: bool = False, recurrence: Optional[dict] = None):
        """ Add a new all-day event to a Holidays schedule

        This method provides a quicker way to add an all-day event to a Holidays schedule than using
        :py:meth:`add_event()`. When used on a businessHours schedule, a TypeError will be raised.

        If :attr:`recur` is True and the :attr:`recurrence` dict is not present, the method will set the holiday to
        repeat yearly on the same month and day, which works for holidays like Christmas that fall on the same date.
        If you need to add a holiday, such as Thanksgiving, that recurs on the 4th Thursday of November,
        the :attr:`recurrence` dictionary should be used. For example, Thanksgiving can be defined as follows::

            recurrence = {
                'recurForEver': True,
                'recurYearlyByDay': {
                    'day': 'THURSDAY',
                    'week': 'FOURTH',
                    'month': 'NOVEMBER'
                }
            }

        The format of this dict, and accepted values can be found
        `here <https://developer.webex.com/docs/api/v1/
        webex-calling-organization-settings-with-location-scheduling/create-a-schedule-event>`_

        Args:
            name (str): The name of the holiday
            date (str): The date the holiday occurs this year in the format YYYY-MM-DD.
            recur (bool, optional): Whether the holiday recurs.
            recurrence (dict, optional): A dict of the recurrence info.

        Returns:
            bool: True on success, False otherwise

        Raises:
            TypeError: Raised when attempting to add a holiday to a businessHours schedule

        """
        log.debug(f"add_holiday() started")
        new_event = {"name": name,
                     "startDate": date, "endDate": date, "allDayEnabled": True}
        date_object = datetime.strptime(date, "%Y-%m-%d")
        # If this isn't a Holidays schedule, we shouldn't accept a new holiday
        if self.type.lower() != "holidays":
            log.debug("Trying to add a holiday to a non-holidays schedule. Raising exception.")
            raise TypeError("Schedule is not of type 'holidays'. Cannot add holiday.")
        if recur is True:
            if recurrence is not None:
                new_event['recurrence'] = recurrence
            else:
                new_event['recurrence'] = {"recurForEver": True,
                                           "recurYearlyByDate": {"dayOfMonth": date_object.strftime("%d"),
                                                                 "month": date_object.strftime("%B").upper()
                                                                 }
                                           }
        api_resp = webex_api_call("post", f"v1/telephony/config/locations/"
                                         f"{self.parent.id}/schedules/{self.type}/{self.id}/events",
                                  headers=self.parent._headers, payload=new_event)
        if api_resp:
            self.refresh_config()
            return True
        else:
            return False

    def delete_event(self, event: str):
        """ Delete an event from within the LocationSchedule

        The event can be passed by name or by ID since both are unique.

        Args:
            event (str): The event name or event ID

        Returns:
            bool: True on success, False otherwise

        """
        log.debug("delete_event() started")
        # Since we accept both the event name or ID, we need to loop through the events to find the one we need.
        for e in self.config['events']:
            if e['name'] == event or e['id'] == event:
                api_resp = webex_api_call("delete", f"v1/telephony/config/locations/{self.parent.id}"
                                                    f"/schedules/{self.type}/{self.id}/events/{e['id']}",
                                          headers=self.parent._headers)
                if api_resp is True:
                    # Get a new copy of the config
                    self.refresh_config()
                    return True
                else:
                    self.refresh_config()
                    return False
        return False

    def create_event(self, name: str, start_date: str, end_date: str, start_time: str = "",
                     end_time: str = "", all_day: bool = False, recurrence: Optional[dict] = None):
        """ Create a new event within the LocationSchedule instance

        Due to the flexibility of the event recurrence needs to be provided as a dict. The format of this dict, and
        accepted values can be found `here <https://developer.webex.com/docs/api/v1/webex-calling-organization-settings-with-location-scheduling/create-a-schedule-event>`_

        For example, the following dict would define an event that recurs every weekday, from 9:00-5:00::

            recurrence = {
                'recurForEver': True,
                'recurWeekly': {
                    'monday': True
                }
            }


        Args:
            name (str): The name of the event
            start_date (str): The start date of the event
            end_date (str): The end date of the event
            start_time (str, optional): If this is not an all-day event, the time the event starts
            end_time (str, optional): If this is not an all-day event, the time the event ends
            all_day (bool, optional): True if this is an all-day event. start_time and end_time will be ignored.
            recurrence (dict, optional): Dict of recurrence configuration

        Returns:
            bool: True on success, False otherwise

        """
        log.debug("create_event() started")
        # Input validation
        if all_day is False and (start_time == "" or end_time == ""):
            raise ValueError("If all_day == False, both start_time and end_time are required.")

        # Build the payload
        payload = {}
        payload['name'] = name
        payload['startDate'] = start_date
        payload['endDate'] = end_date
        payload['allDay'] = all_day
        if all_day is False:
            payload['startTime'] = start_time
            payload['endTime'] = end_time
        if recurrence is not None:
            payload['recurrence'] = recurrence

        api_resp = webex_api_call("post", f"v1/telephony/config/locations/{self.parent.id}/"
                                          f"schedules/{self.type}/{self.id}/events",
                                  headers=self.parent._headers, payload=payload)
        if api_resp:
            self.refresh_config()
            return True
        else:
            self.refresh_config()
            return False

    def update_event(self, id: str, name: str = None, start_date: str = None, end_date: str = None, start_time: str = None,
                     end_time: str = None, all_day: bool = None, recurrence: dict = None):
        log.debug("update_event() started")
        # Input validation
        if all_day is False and (start_time == "" or end_time == ""):
            raise ValueError("If all_day == False, both start_time and end_time are required.")

        # Build the payload
        payload = self.get_event_config_by_id(id)
        if name is not None:
            payload['name'] = name
        if start_date is not None:
            payload['startDate'] = start_date
        if end_date is not None:
            payload['endDate'] = end_date
        if all_day is not None:
            payload['allDay'] = all_day
            if all_day is False:
                if start_time is not None:
                    payload['startTime'] = start_time
                if end_time is not None:
                    payload['endTime'] = end_time
        if recurrence is not None:
            payload['recurrence'] = recurrence

        api_resp = webex_api_call("put", f"v1/telephony/config/")
        if api_resp:
            return True
        else:
            return False

    def get_event_config_by_id(self, id: str) -> Optional[dict]:
        """ Get the 'events' dict for a specific event.

        This method is useful if you are modifying an event and want to provide the full config.

        Args:
            id (str): The Event ID

        Returns:
            dict: The config of the event as a dict. If the Event ID is not found, None is returned.

        """
        for e in self.config['events']:
            if e['id'] == id:
                return e
        return None

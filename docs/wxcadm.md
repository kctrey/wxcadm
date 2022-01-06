Module wxcadm
=============

Classes
-------

`APIError(message)`
:   Common base class for all non-exit exceptions.
    
    The base class for any exceptions dealing with the API

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

    ### Descendants

    * wxcadm.PutError
    * wxcadm.TokenError

`Call(parent, id: str = '', address: str = '')`
:   The Call class represents a call for a person. Since Webex supports calls in the Webex API as well as XSI API,
    the class supports both styles. When initialized, the parent instance is checked to see if it is a Person
    instance or an XSI instance. At the moment, the Webex API only supports user-scoped call control, so most of the
    development focus right now is the XSI API, which is more feature-rich
    
    Inititalize a Call instance for a Person
    Args:
        parent (XSI): The Person or XSI instance that owns this Call
        id (str, optional): The Call ID of a known call. Usually only done during a XSI.calls method
        address (str, optional): The address to originate a call to when the instance is created
    Returns:
        Call: This Call instance

    ### Instance variables

    `id`
    :   The Call ID for this call

    `status`
    :   The status of the call
        Returns:
            dict: {
                'network_call_id' (str): The unique identifier for the Network side of the call
                'personality'(str): The user's personalty (Originator or Terminator)
                'state' (str): The state of the call
                'remote_party' (dict): {
                    'address' (str): The address of the remote party
                    'call_type' (str): The call type
                }
                'endpoint' (dict): {
                    'type' (str): The type of endpoint in use
                    'AoR' (str): The Address of Record for the endpoint
                }
                'appearance' (str): The Call Appearance number
                'start_time' (str): The UNIX timestanp of the start of the call
                'answer_time' (str): The UNIX timestamp when the call was answered
                'status_time' (str): The UNIX timestamp of the status response

    ### Methods

    `conference(self, address: str = '')`
    :   Starts a multi-party conference. If the call is already held and an attended transfer is in progress,
        meaning the user is already talking to the transfer-to user, this method will bridge the calls.
        Args:
            address (str, optional): The address (usually a phone number or extension) to conference to. Not needed
                when the call is already part of an Attended Transfer
        Returns:
            bool: True if the conference is successful

    `finish_transfer(self)`
    :   Complete an Attended Transfer. This method will only complete if a `transfer(address, type="attended")`
        has been done first.
        Returns:
            bool: Whether or not the transfer completes

    `hangup(self)`
    :   Hang up the call
        Returns:
            bool: Whether the command was successful

    `hold(self)`
    :   Place the call on hold
        Returns:
            bool: Whether the hold command was successful

    `originate(self, address: str, comment: str = '')`
    :   Originate a call on behalf of the Person
        Args:
            address (str): The address (usually a phone number) to originate the call to
            comment (str, optional): Text comment to attach to the call
        Returns:
            bool: Whether the command was successful

    `resume(self)`
    :   Resume a call that was placed on hold
        Returns:
            bool: Whether the command was successful

    `send_dtmf(self, dtmf: str)`
    :   Transmit DTMF tones outbound
        Args:
            dtmf (str): The string of dtmf digits to send. Accepted digits 0-9, star, pound. A comma will pause
                between digits (i.e. "23456#,123")
        Returns:
            bool: True if the dtmf was sent successfuly

    `transfer(self, address: str, type: str = 'blind')`
    :   Transfer the call to the selected address. Type of transfer can be controlled with `type` param. VM
        transfers will transfer the call directly to the voice mail of the address, even if the address is the
        user's own address. Attended transfers require a subsequent call to `finish_transfer()` when the actual transfer
        should happen.
        Args:
            address (str): The address (usually a phone number or extension) to transfer the call to
            type (str): ['blind','vm','attended']:
                The type of transfer.
        Returns:
            bool: True if successful. False if unsuccessful

`CallQueue(parent, id, name, location, phone_number, extension, enabled, get_config=True)`
:   

    ### Instance variables

    `call_forwarding`
    :   The Call Forwarding config for the Call Queue

    `config`
    :   The configuration dictionary for the Call Queue

    `enabled`
    :   True if the Call Queue is enabled. False if disabled

    `extension`
    :   The extension of the Call Queue

    `id`
    :   The Webex ID of the Call Queue

    `location_id`
    :   The Webex ID of the Location associated with this Call Queue

    `name`
    :   The name of the Call Queue

    `phone_number`
    :   The DID of the Call Queue

    ### Methods

    `get_queue_config(self)`
    :   Get the configuration of this Call Queue instance
        Returns:
            CallQueue.config: The config dictionary of this Call Queue

    `get_queue_forwarding(self)`
    :   Get the Call Forwarding settings for this Call Queue instance
        
        Returns:
            CallQueue.call_forwarding: The Call Forwarding settings for the Person

    `push(self)`
    :   Push the contents of the CallQueue.config back to Webex
        Returns:
            CallQueue.config: The updated config attribute pulled from Webex after pushing the change

`Conference(parent: object, calls: list, comment: str = '')`
:   The class for Conference Calls started by a Call.conference()
    
    Initialize a Conferece instance for an XSI instance
    Args:
        parent (XSI): The XSI instance that owns this conference
        calls (list): Call IDs associated with the Conference. Always two Call IDs to start a Conference.
            Any additional Call IDs will be added to the conference as it is created.
        comment (str, optional): An optional text comment for the Conference
    Returns:
        Conference: This instance of the Conference class

    ### Instance variables

    `comment`
    :   Text comment associated with the Conference

    ### Methods

    `deaf(self, call: str)`
    :   Stop audio and video from being sent to a participant. Audio and video from that participant are unaffected.
        Args:
            call (str): The Call ID to make deaf
        Returns:
            bool: Whether the command was successful

`HuntGroup(parent: object, id: str, name: str, location: str, enabled: bool, phone_number: str = None, extension: str = None, config: bool = True)`
:   Initialize a HuntGroup instance
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

    ### Instance variables

    `agents`
    :   List of users assigned to this Hunt Group

    `alternate_numbers_settings`
    :   List of alternate numbers for this Hunt Group

    `call_policy`
    :   The Call Policy for the Hunt Group

    `distinctive_ring`
    :   Whether or not the Hunt Group has Distinctive Ring enabled

    `enabled`
    :   Whether the Hunt Group is enabled or not

    `extension`
    :   The extension of the Hunt Group

    `first_name`
    :   The Caller ID first name for the Hunt Group

    `id`
    :   The Webex ID of the Hunt Group

    `language`
    :   The language name for the Hunt Group

    `language_code`
    :   The short name for the language of the Hunt Group

    `last_name`
    :   The Caller ID last name for the Hunt Group

    `location`
    :   The Location ID associated with the Hunt Group

    `name`
    :   The name of the Hunt Group

    `phone_number`
    :   The DID for the Hunt Group

    `raw_config`
    :   The raw JSON-to-Python config from Webex

    `time_zone`
    :   The time zone for the Hunt Group

    ### Methods

    `get_config(self)`
    :   Get the Hunt Group config, including agents

`LicenseError(message)`
:   Common base class for all non-exit exceptions.
    
    Exceptions dealing with License problems within the Org

    ### Ancestors (in MRO)

    * wxcadm.OrgError
    * builtins.Exception
    * builtins.BaseException

`Location(location_id: str, name: str, address: dict = {})`
:   Initialize a Location instance
    Args:
        location_id (str): The Webex ID of the Location
        name (str): The name of the Location
        address (dict): The address information for the Location
    Returns:
         Location (object): The Location instance

`Org(name: str, id: str, people: bool = True, locations: bool = True, xsi: bool = False, parent: wxcadm.Webex = None)`
:   Initialize an Org instance
    
    Args:
        name (str): The Organization name
        id (str): The Webex ID of the Organization
        people (bool, optional): Whether to automatically get all people for the Org
        locations (bool, optional): Whether to automatically get all of the locations for the Org
        xsi (bool, optional): Whether to automatically get the XSI Endpoints for the Org
        parent (Webex, optional): The parent Webex instance that owns this Org.
    
    Returns:
        Org: This instance of the Org class

    ### Instance variables

    `call_queues`
    :   The Call Queues for this Org

    `hunt_groups`
    :   The Hunt Groups for this Org

    `id`
    :   The Webex ID of the Organization

    `licenses`
    :   A list of all of the licenses for the Organization as a dictionary of names and IDs

    `locations`
    :   A list of the Location instances for this Org

    `name`
    :   The name of the Organization

    `people`
    :   A list of all of the Person stances for the Organization

    `pickup_groups`
    :   A list of the PickupGroup instances for this Org

    ### Methods

    `create_person(self, email: str, location: str, licenses: list = [], calling: bool = True, messaging: bool = True, meetings: bool = True, phone_number: str = '', extension: str = '', first_name: str = '', last_name: str = '', display_name: str = '')`
    :   Create a new user in Webex. Also creates a new Person instance for the created user.
        Args:
            email (str): The email address of the user
            location (str): The ID of the Location that the user is assigned to.
            licenses (list, optional): List of license IDs to assign to the user. Use this when the license IDs
                are known. To have the license IDs determined dynamically, use the `calling`, `messaging` and
                `meetings` parameters.
            calling (bool, optional): BETA - Whether to assign Calling licenses to the user. Defaults to True.
            messaging (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            meetings (bool, optional): BETA - Whether to assign Messaging licenses to the user. Defaults to True.
            phone_number (str, optional): The phone number to assign to the user.
            extension (str, optional): The extension to assign to the user
            first_name (str, optional): The user's first name. Defaults to empty string.
            last_name (str, optional): The users' last name. Defaults to empty string.
            display_name (str, optional): The full name of the user as displayed in Webex. If first name and last name are passed
                without display_name, the display name will be the concatenation of first and last name.
        Returns:
            Person: The Person instance of the newly-created user.

    `get_call_queues(self)`
    :   Get the Call Queues for an Organization. Also stores them in the Org.call_queues attribute.
        Returns:
            list[CallQueue]: List of CallQueue instances for the Organization

    `get_hunt_groups(self)`
    :   Get the Hunt Groups for an Organization. Also stores them in the Org.hunt_groups attribute.
        Returns:
            list[HuntGroup]: List of HuntGroup instances for the Organization

    `get_locations(self)`
    :   Get the Locations for the Organization. Also stores them in the Org.locations attribute.
        Returns:
            list[Location]: List of Location instance objects. See the Locations class for attributes.

    `get_people(self)`
    :   Get all of the people within the Organization. Also creates a Person instance and stores it in the
            Org.people attributes
        Returns:
            list[Person]: List of Person instances

    `get_person_by_email(self, email)`
    :   Get the Person instance from an email address
        Args:
            email (str): The email of the Person to return
        Returns:
            Person: Person instance object. None in returned when no Person is found

    `get_pickup_groups(self)`
    :   Get all of the Call Pickup Groups for an Organization. Also stores them in the Org.pickup_groups attribute.
        Returns:
            list[PickupGroup]: List of Call Pickup Groups as a list of dictionaries.
                See the PickupGroup class for attributes.

    `get_wxc_people(self)`
    :   Get all of the people within the Organization **who have Webex Calling**
        Returns:
            list[Person]: List of Person instances of people who have a Webex Calling license

    `get_xsi_endpoints(self)`
    :   Get the XSI endpoints for the Organization. Also stores them in the Org.xsi attribute.
        Returns:
            dict: Org.xsi attribute dictionary with each endpoint as an entry

`OrgError(message)`
:   Common base class for all non-exit exceptions.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

    ### Descendants

    * wxcadm.LicenseError

`Person(user_id, parent: object = None, config: dict = {})`
:   Initialize a new Person instance. If only the `user_id` is provided, the API calls will be made to get
        the config from Webex. To save on API calls, the config can be provided which will set the attributes
        without an API call.
    Args:
        user_id (str): The Webex ID of the person
        parent (object, optional): The parent object that created the Person instance. Used when the Person
            is created within the Org instance
        config (dict, optional): A dictionary of raw values from the `GET v1/people` items. Not normally used
            except for automated people population from the Org init.

    ### Instance variables

    `barge_in`
    :   Dictionary of Barge-In config as returned by Webex API

    `call_forwarding`
    :   Dictionary of the Call Forwarding config as returned by Webex API

    `caller_id`
    :   Dictionary of Caller ID config as returned by Webex API

    `calling_behavior`
    :   Dictionary of Calling Behavior as returned by Webex API

    `display_name`
    :   The user's name as displayed in Webex

    `dnd`
    :   Dictionary of DND settings as returned by Webex API

    `email`
    :   The user's email address

    `extension`
    :   The extension for this person

    `first_name`
    :   The user's first name

    `id`
    :   The Webex ID of the Person

    `intercept`
    :   Dictionary of Call Intercept config as returned by Webex API

    `last_name`
    :   The user's last name

    `licenses`
    :   List of licenses assigned to the person

    `location`
    :   The Webex ID of the user's assigned location

    `numbers`
    :   The phone numbers for this person from Webex CI

    `recording`
    :   Dictionary of the Recording config as returned by Webex API

    `roles`
    :   The roles assigned to this Person in Webex

    `vm_config`
    :   Dictionary of the VM config as returned by Webex API

    `wxc`
    :   True if this is a Webex Calling User

    `xsi`
    :   Holds the XSI instance when created with the `start_xsi()` method.

    ### Methods

    `change_phone_number(self, new_number: str, new_extension: str = None)`
    :   Change a person's phone number and extension
        Args:
            new_number (str): The new phone number for the person
            new_extension (str, optional): The new extension, if changing. Omit to leave the same value.
        Returns:
            Person: The instance of this person, with the new values

    `disable_vm_to_email(self, push=True)`
    :

    `enable_vm_to_email(self, email: str = None, push=True)`
    :

    `get_barge_in(self)`
    :

    `get_call_forwarding(self)`
    :

    `get_call_recording(self)`
    :

    `get_caller_id(self)`
    :

    `get_calling_behavior(self)`
    :

    `get_dnd(self)`
    :

    `get_full_config(self)`
    :   Fetches all of the Webex Calling settings for the Person. Due to the number of API calls, this
        method is not performed automatically on Person init and should be called for each Person during
        any subsequent processing. If you are only interested in one of the features, calling that method
        directly can significantly improve the time to return data.

    `get_intercept(self)`
    :

    `get_vm_config(self)`
    :

    `push_vm_config(self)`
    :

    `start_xsi(self)`
    :   Starts an XSI session for the Person

`PickupGroup(parent, location, id, name, users=None)`
:   

    ### Instance variables

    `id`
    :   The Webex ID of the Pickup Group

    `location_id`
    :   The Webex ID of the Location associated with this Pickup Group

    `name`
    :   The name of the Pickup Group

    `users`
    :   All of the users (agents) assigned to this Pickup Group

    ### Methods

    `get_config(self)`
    :   Gets the configuration of the Pickup Group from Webex
        Returns:
            dict: The configuration of the Pickup Group

`PutError(message)`
:   Common base class for all non-exit exceptions.
    
    Exception class for problems putting values back into Webex

    ### Ancestors (in MRO)

    * wxcadm.APIError
    * builtins.Exception
    * builtins.BaseException

`TokenError(message)`
:   Common base class for all non-exit exceptions.
    
    Exceptions dealing with the Access Token itself

    ### Ancestors (in MRO)

    * wxcadm.APIError
    * builtins.Exception
    * builtins.BaseException

`Webex(access_token: str, create_org: bool = True, get_people: bool = True, get_locations: bool = True, get_xsi: bool = False)`
:   The base class for working with wxcadm.
    
    Initialize a Webex instance to communicate with Webex and store data
    Args:
        access_token (str): The Webex API Access Token to authenticate the API calls
        create_org (bool, optional): Whether to create an Org instance for all organizations.
        get_people (bool, optional): Whether to get all of the People and created instances for them
        get_locations (bool, optional): Whether to get all Locations and create instances for them
        get_xsi (bool, optional): Whether to get the XSI endpoints for each Org. Defaults to False, since
            not every Org has XSI capability
    Returns:
        Webex: The Webex instance

    ### Instance variables

    `headers`
    :   The "universal" HTTP headers with the Authorization header present

    `orgs`
    :   A list of the Org instances that this Webex instance can manage

`XSI(parent, get_profile: bool = False, cache: bool = False)`
:   The XSI class holds all of the relevant XSI data for a Person
    Args:
        parent (Person): The Person who this XSI instance belongs to
        get_profile (bool): Whether or not to automatically get the XSI Profile
        cache (bool): Whether to cache the XSI data (True) or pull it "live" every time (**False**)

    ### Instance variables

    `alternate_numbers`
    :   The Alternate Numbers for this Person

    `anonymous_call_rejection`
    :   The Anonymous Call Rejection settings for this Person

    `calls`
    :   Get the list of active calls and creates Call instances. Also destroys any Call instances that are no longer
        valid.
        Returns:
            list[Call]: List of Call instances

    `monitoring`
    :   The Monitoring/BLF settings for this person

    `profile`
    :   The XSI Profile for this Person

    `registrations`
    :   The device registrations asscociated with this Person

    `single_number_reach`
    :   The SNR (Office Anywhere) settings for this Person

    ### Methods

    `get_fac(self)`
    :

    `get_services(self)`
    :

    `new_call(self, address: str = '')`
    :   Create a new Call instance
        Args:
            address (str, optional): The address to originate a call to
        Returns:
            Call: The Call instance

    `new_conference(self, calls: list = [], comment: str = '')`
    :   Crates a new Conference instance. A user can only have one Conference instance, so this will replace any
        previous Conference. At the moment, this **should not be called directly** and will be done dynamically by
        a Call.conference()
        Args:
            calls (list): A list of Call IDs involved in this conference. A conference is always started with only
                two Call IDs. Call IDs after the first two will be ignored.
            comment (str, optional): An optional text comment for the conference
        Returns:
            The instance of the Conference class
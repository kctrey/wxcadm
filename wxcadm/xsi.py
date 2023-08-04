from __future__ import annotations

import uuid
import json
import srvlookup
import xmltodict
import traceback
import re
import requests
import threading
from typing import Optional, Union
from threading import Thread
import time

import wxcadm
from wxcadm import log
from .common import *
from .exceptions import *
from .xsi_response import XSIResponse


class XSIEvents:
    def __init__(self, parent: Org):
        """ Initialize an XSIEvents instance to provide access to XSI-Events

        Args:
            parent (Org): The Webex.Org instance that these Events are associated with. Currently, only Org-level
                events can be monitored. User-level subscriptions will be added later.
        """
        self._parent = parent
        self._headers = parent._headers
        self.events_endpoint = parent.xsi['events_endpoint']
        self.channel_endpoint = parent.xsi['events_channel_endpoint']
        self.xsi_domain = parent.xsi['xsi_domain']
        self.application_id = uuid.uuid4()
        """ The unique Application ID used to identify the application to Webex """
        self.enterprise = self._parent.spark_id.split("/")[-1]
        log.debug(f"Using Enterprise ID: {self.enterprise} to initialize XSIEvents")
        """ The Enterprise ID used to identify the Webex Org to the XSI Events service """
        self.channel_sets = []
        self.queue = None

    def open_channel(self, queue):
        """ Open an XSI Events channel and start pushing Events into the queue.

        For now, this only accepts a Queue instance as the queue argument.

        Args:
            queue (Queue): The Queue instance to place events into

        Returns:
            XSIEventsChannelSet: The :class:`XSIEventsChannelSet` instance that was opened

        """
        self.queue = queue
        log.debug("Initializing Channel Set")
        channel_set = XSIEventsChannelSet(self)
        self.channel_sets.append(channel_set)
        return channel_set


class XSIEventsChannelSet:
    def __init__(self, parent: XSIEvents):
        """ Inititalize an XSIEventsChannelSet instance to manage channels and subscriptions.

        Calling this method, which is normally done with the :meth:`XSIEvents.open_channel()` method, automatically
        creates the channels to each XSP in the region and begins send heartbeat messages on them.

        Args:
            parent (XSIEvents): The XSIEvents instance to which this ChanelSet belongs.
        """
        self.parent = parent
        self._headers = self.parent._headers
        self.id = uuid.uuid4()
        """ The unique ID of the Channel Set """
        log.debug(f"Channel Set ID: {self.id}")
        self.channels = []
        """ List of :py:class:`XSIEventChannel` instances within the Channel Set """
        self.subscriptions = []
        """ List of :py:class:`XSIEventsSubscription` instances associated with the the Channel Set """
        self.queue = self.parent.queue
        """ The Python :py:class:`Queue` that was provided to :py:class`XSIEvents` to queue messages """

        # Now init the channels. Get the SRV records to ensure they get opended with each XSP
        log.debug(f"Getting SRV records for {self.parent.xsi_domain}")
        srv_records = srvlookup.lookup("xsi-client", "TCP", self.parent.xsi_domain)
        self.srv_records = srv_records
        log.debug(f"\t{srv_records}")
        for record in srv_records:
            my_endpoint = re.sub(self.parent.xsi_domain, record.host, self.parent.channel_endpoint)
            my_events_endpoint = re.sub(self.parent.xsi_domain, record.host, self.parent.events_endpoint)
            log.debug(f"Establishing channel with endpoint: {record.host}")
            channel = XSIEventsChannel(self, my_endpoint, my_events_endpoint)
            self.channels.append(channel)

    def restart_failed_channel(self, channel: XSIEventsChannel, wait: int = 0):
        """ Starts a new channel, using an :py:class:`XSIEventsChannel` with an ``active=False`` status as the source
        to determine where the new channel should be established to.

        Args:
            channel (XSIEventsChannel: The :py:class:`XSIEventsChannel` instance that failed.

        Returns:
            bool: True on success, False otherwise.

        """
        if channel.active is True:
            log.warning("Cannot restart an active channel")
            return False
        log.debug(f"[{threading.current_thread().name}] ==== Restarting Failed XSIEventsChannel "
                  f"with endpoint {channel.endpoint.split('/')[2]} in {wait} seconds ====")
        time.sleep(wait)
        new_channel = XSIEventsChannel(self, channel.endpoint, channel.events_endpoint)
        self.channels.append(new_channel)
        # Send a DELETE on the failed channel, just to make sure it is removed from the server
        channel.delete()
        return True

    def audit_channelset(self):
        """ Audit the known channels against what Webex Calling has listed.

        ..note:
            This method is not fully implemented at this time and is being added for future use.

        Returns:

        """
        r = requests.get(self.parent.events_endpoint + f'/v2.0/channelset/{self.id}',
                         headers=self._headers)
        if r.ok:
            log.debug(f"[{threading.current_thread().name}] Channel Audit: {r.text}")

        return True

    @property
    def active_channels(self):
        active_channels = []
        for channel in self.channels:
            if channel.active is True:
                active_channels.append(channel)
        return active_channels

    def subscribe(self, event_package, person: Person = None):
        """ Subscribe to an Event Package over the channel opened with :meth:`XSIEvents.open_channel()`

        Args:
            event_package (str): The name of the Event Package to subscribe to.
            person (Person, optonal): A Person instance to subscribe to the event package for. If not provided,
                the entire Organization will be subscribed.

        Returns:
            XSIEventsSubscription: The Subscription instance. False is returned if the subscription fails.

        """
        log.info(f'Subscribing to {event_package}')
        if len(self.active_channels) == 0:
            log.warning("Cannot subscribe when no channels are active")
            raise XSIError("Cannot subscribe with no active channels")
        subscription = XSIEventsSubscription(self, event_package, person=person)
        if subscription and subscription.active is True:
            self.subscriptions.append(subscription)
            log.debug(f'\tCurrent Subscriptions: {self.subscriptions}')
            return subscription
        else:
            log.warning(f"The subscription did not activate")
            return False

    def unsubscribe(self, subscription_id: str):
        """ Unsubscribe from an Event Package that was previously subscribed to with :meth:`subscribe()`

        Args:
            subscription_id (str): The ID of the XSIEventsSubscription instance

        Returns:
            bool: True if unsubscription was successful, False otherwise

        """
        log.info(f"Unsubscribing subscription: {subscription_id}")
        all_success = True
        for subscription in self.subscriptions:
            if subscription.id == subscription_id or subscription_id.lower() == "all":
                success = subscription.delete()
                if success:
                    self.subscriptions.remove(subscription)
                else:
                    all_success = False
        return all_success

    def close(self):
        """ Close all :py:class:`XSIEventsChannel` and delete all :py:class:`XSIEventsSubscription`

        Returns:
            bool: Always True

        """
        for subscription in self.subscriptions:
            subscription.delete()
        for channel in self.channels:
            log.debug(f"Deleting Channel {channel.id} with {channel.endpoint}")
            channel.delete()
        return True


class XSIEventsChannel:
    def __init__(self, parent: XSIEventsChannelSet, endpoint: str, events_endpoint: str):
        """ The `XSIEventsChannel` handles a single channel in an `XSiEventsChannelSet`

        Upon initialization, the instance will start two threads, one for monitoring the events received across the
        long-running channel and one for sending heartbeats to keep the channel alive.

        .. note::

            This class does not need to be initialized manually. It is done from the :py:class:`XSIEventsChannelSet`
            instance.

        Args:
            parent (XSIEventsChannelSet): The :py:class:`XSIEventsChannelSet` to which this channel belongs
            endpoint (str): The XSI endpoint to connect the long-running channel to
            events_endpoint (str):  The XSI Events endpoint to send heartbeats and acknowledgements to
        """
        self.parent = parent
        self._headers = self.parent.parent._headers
        self.id = ""
        self.endpoint = endpoint
        self.events_endpoint = events_endpoint
        self.queue = self.parent.queue
        self.active = True
        self.needs_restart = False
        self.last_refresh = ""
        self.xsp_ip:str = ''
        self.session = requests.Session()
        self.cookies = None
        self.channel_thread = Thread(target=self._channel_daemon, daemon=True)
        self.heartbeat_thread = Thread(target=self._heartbeat_daemon, daemon=True)

        # Start the channel thread
        self.channel_thread.start()
        # Wait a few seconds for the channel to come up before starting the heartbeats
        time.sleep(2)
        self.heartbeat_thread.start()

    def _channel_daemon(self):
        """ A Thread-safe daemon to watch the :py:class:`XSIEventsChannel` for incoming messages.

        .. note::

            This method is called automatically when the `XSIEventsChannel` is initialized and never should be
            called manually

        Returns:
            bool: Will always return True when the channel is closed

        """
        payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
                  '<Channel xmlns=\"http://schema.broadsoft.com/xsi\">' \
                  f'<channelSetId>{self.parent.id}</channelSetId>' \
                  '<priority>1</priority>' \
                  '<weight>50</weight>' \
                  '<expires>7200</expires>' \
                  f'<applicationId>{self.parent.parent.application_id}</applicationId>' \
                  '</Channel>'

        tid = tracking_id()
        log.debug(f"[{threading.current_thread().name}][{tid}] Sending Channel Start Request (Streaming) "
                  f"to {self.endpoint}/v2.0/channel")
        log.debug(f"\tHeaders: {self._headers}\n\tPayload: {payload}")
        r = self.session.post(
            f"{self.endpoint}/v2.0/channel",
            headers={'TrackingID': tid, **self._headers}, data=payload, stream=True)
        # An issue with the F5 in Oct 2022 showed that we need to handle non-ok responses better
        if not r.ok:
            log.debug(f"\tHeaders: {r.headers}")
            log.debug(f"\tBody: {r.text}")
            log.warning(f"Unable to establish connection with {self.endpoint}")
            ip = 'unknown'
            self.active = False
            self.needs_restart = True
        else:
            # Get the real IP of the remote server so we can send subsequent messages to that
            ip, port = r.raw._connection.sock.getpeername()
        log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                  f"Received response from {ip}. Status code {r.status_code}")
        # log.debug(f"[{r.headers.get('TrackingID', 'Unknown')}] Headers: {r.headers}")
        log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                  f"Saving Cookies: {r.cookies.get_dict()}")
        self.cookies = r.cookies

        self.xsp_ip = str(ip)
        chars = ""
        self.last_refresh = time.time()
        for char in r.iter_content():
            decoded_char = char.decode('utf-8')
            chars += decoded_char
            # The next line spits character-by-character data out, so it's not really useful outside of development
            # log.debug(chars)
            if "</Channel>" in chars:
                log.debug(f"[{threading.current_thread().name}][{tid}] Channel setup: {chars} from {self.xsp_ip}")
                m = re.search("<channelId>(.+)</channelId>", chars)
                self.id = m.group(1)
                chars = ""
            if "<ChannelHeartBeat xmlns=\"http://schema.broadsoft.com/xsi\"/>" in chars:
                log.debug(f"[{threading.current_thread().name}][{tid}] Heartbeat received on channel {self.id}")
                # Check how long since a channel refresh and refresh if needed
                time_now = time.time()
                if time_now - self.last_refresh >= 3600:
                    log.debug(f"[{threading.current_thread().name}] Refreshing channel: {self.id}")
                    self._refresh_channel()
                    self.last_refresh = time.time()
                # Check any subscriptions and refresh them while we are at it
                for subscription in self.parent.subscriptions:
                    if time_now - subscription.last_refresh >= 3600:
                        log.debug(f"[{threading.current_thread().name}] Refreshing subscription: {subscription.id}")
                        subscription._refresh_subscription()
                        subscription.last_refresh = time.time()
                chars = ""
            if "</xsi:Event>" in chars:
                event = chars
                log.debug(f"[{threading.current_thread().name}][{tid}] Full Event: {event}")
                message_dict = xmltodict.parse(event)
                # Reset ready for new message
                chars = ""
                if message_dict['xsi:Event']['@xsi1:type'] == 'xsi:ChannelTerminatedEvent':
                    # ChannelTerminatedEvent doesn't require or accept an ACK, so we don't need to do that.
                    log.debug(f"[{threading.current_thread().name}][{tid}] "
                              f"Received ChannelTerminatedEvent for channel "
                              f"{message_dict['xsi:Event']['xsi:channelId']} "
                              f"with reason {message_dict['xsi:Event']['xsi:reason']}")
                    # TODO - At some point, we should probably report the channel termination up to see if the channel
                    #        needs to be restarted, or if it happened because we torn it down. The xsi:reason should
                    #        help with that.
                else:
                    self.parent.queue.put(message_dict) # Moved here 2.3.4 to prevent sending TerminatedEvent to Queue
                    try:
                        self._ack_event(message_dict['xsi:Event']['xsi:eventID'])
                    except KeyError:
                        log.debug("xsi:Event received but no xsi:eventID to ACK")
                        log.debug(f"\t{message_dict}")
                        pass
            if decoded_char == "\n":
                # Discard this for now
                # log.debug(f"Discard Line: {chars}")
                chars = ""
        log.debug(f"[{threading.current_thread().name}][{tid}] Channel Loop ended: {self.id}")
        self.active = False
        if self.needs_restart is True:
            self.parent.restart_failed_channel(self, wait=60)
        return True

    def _heartbeat_daemon(self):
        """ A Thread-safe daemon to send heartbeats on the  :py:class:`XSIEventsChannel`

        .. note::

            This method is called automatically when the `XSIEventsChannel` is initialized and never should be
            called manually

        Returns:
            bool: Always returns True when the function completes and the channel is down.

        """
        while self.active:
            tid = tracking_id()
            log.debug(f"[{threading.current_thread().name}][{tid}] Sending heartbeat for channel: {self.id}")
            try:
                r = self.session.put(self.events_endpoint + f"/v2.0/channel/{self.id}/heartbeat",
                                headers={'TrackingID': tid, **self._headers}, stream=True)
                ip, port = r.raw._connection.sock.getpeername()
                if r.ok:
                    log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                              f"{ip} - Heartbeat successful")
                    # On success, send a heartbeat every 15 seconds
                    next_heartbeat = 15
                else:
                    log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                              f"{ip} - Heartbeat failed: {r.text} [{r.status_code}]")
                    if r.status_code == 404:
                        # If the channel can't be found on the server, kill the channel and restart it
                        self.active = False
                        self.parent.restart_failed_channel(self)
                        next_heartbeat = 0
                    else:
                        # Losing a heartbeat is ok, but we should try another one sooner than 15 seconds
                        next_heartbeat = 10
            except Exception as e:
                log.debug(f"[{threading.current_thread().name}] Heartbeat failed: {traceback.format_exc()}")
                # If the heartbeat couldn't be sent for some reason, retry sooner than 15 seconds
                next_heartbeat = 10
            #self.parent.audit_channelset()
            time.sleep(next_heartbeat)
        return True

    def _ack_event(self, event_id):
        """ Send an ACK to the XSI Events server to acknowledge the Event was received.

        .. note::

            This method is called automatically by the `channel_daemon()` and should never be called manually

        Args:
            event_id (str): The XSI Event ID that the ACK needs to be sent for.

        Returns:
            bool: True if the ACK was accepted by the server. False otherwise.

        """
        payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
                  '<EventResponse xmlns=\"http://schema.broadsoft.com/xsi\">' \
                  f'<eventID>{event_id}</eventID>' \
                  '<statusCode>200</statusCode>' \
                  '<reason>OK</reason>' \
                  '</EventResponse>'
        tid = tracking_id()
        log.debug(f"[{threading.current_thread().name}][{tid}] Acking event: {event_id}")
        r = self.session.post(self.events_endpoint + "/v2.0/channel/eventresponse",
                          headers={'TrackingID': tracking_id(), **self._headers}, data=payload)
        if r.ok:
            return True
        else:
            log.debug(f"[{threading.current_thread().name}][{tid}] "
                      f"The ACK was not successful: {r.text}")
            return False

    def _refresh_channel(self):
        """ Send a command to refresh the :py:class:`XSIEventsChannel`

        .. note::

            This method is called automatically by the `heartbeat_daemon()` and should never be called manually

        Returns:
            bool: True on success, False otherwise.

        """
        tid = tracking_id()
        log.debug(f"[{threading.current_thread().name}][{tid}] Refreshing Channel: {self.id}")
        payload = "<Channel xmlns=\"http://schema.broadsoft.com/xsi\"><expires>7200</expires></Channel>"
        r = self.session.put(self.events_endpoint + f"/v2.0/channel/{self.id}",
                         headers={'TrackingID': tracking_id(), **self._headers}, data=payload)
        if r.ok:
            log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                      f"Channel refresh succeeded")
            return True
        else:
            log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                      f"Channel refresh failed: {r.text}")
            return False

    def delete(self):
        """ Delete the :py:class:`XSIEventsChannel` instance

        This method will close the channel and delete it from the server.

        Returns:
            bool: True on success, False otherwise

        """
        tid = tracking_id()
        log.debug(f"[{threading.current_thread().name}][{tid}] Deleting Channel: {self.id}")
        r = self.session.delete(self.events_endpoint + f'/v2.0/channel/{self.id}',
                            headers={'TrackingID': tid, **self._headers})
        log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                  f"Channel Delete received {r.status_code} from server")
        if r.ok:
            self.active = False
            return True
        else:
            log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                      f"Channel Delete response: {r.text}")
            return False

class XSIEventsSubscription:
    def __init__(self, parent: XSIEventsChannelSet, event_package: str, person: Person = None):
        """ Initialize an XSIEventsSubscription

        Initializing the subscription also sends the subscription to the XSI API over the events_endpoint.

        Args:
            parent (XSIEventsChannelSet): The XSIEventsChannelSet instance to issue the subscription for.
            event_package (str): The XSI Event Package to subscribe to.
            person (Person): A Person instance to subscribe to the event package for. If not provided,
                the entire Organization will be subscribed.
        """
        self.id: Optional[str] = None
        self.parent = parent
        if person is None:
            self.target = "serviceprovider"
        else:
            self.target = person
        self.events_endpoint = self.parent.parent.events_endpoint
        self._headers = self.parent._headers
        self.last_refresh = time.time()
        """ The date and time that the subscription was last refreshed """
        self.event_package = event_package
        log.info(f"Subscribing to: {self.event_package} at {self.events_endpoint}")
        payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
                  '<Subscription xmlns=\"http://schema.broadsoft.com/xsi\">' \
                  f'<event>{self.event_package}</event>' \
                  f'<expires>7200</expires><channelSetId>{self.parent.id}</channelSetId>' \
                  f'<applicationId>{self.parent.parent.application_id}</applicationId></Subscription>'
        if person is None:
            r = requests.post(self.events_endpoint + f"/v2.0/serviceprovider/{self.parent.parent.enterprise}",
                              headers={"TrackingId": tracking_id(), **self._headers}, data=payload)
            # Adding the following debug to help with failed subscriptions.
            log.debug("Subscribe API Call:")
            log.debug(f"\tURL: {self.events_endpoint}/v2.0/serviceprovider/{self.parent.parent.enterprise}")
            log.debug(f"\tHeaders: {self._headers}")
            log.debug(f"\tPayload: {payload}")
        else:
            if isinstance(person, wxcadm.person.Person):
                # Make sure we have the Person's XSI Profile
                user_id = person.spark_id.split("/")[-1]
                r = requests.post(self.events_endpoint + f"/v2.0/user/{user_id}",
                                  headers=self._headers, data=payload)
            else:
                raise ValueError("The user argument requires a Person instance")
        if r.ok:
            response_dict = xmltodict.parse(r.text)
            log.debug(f"Response: {response_dict}")
            self.id = response_dict['Subscription']['subscriptionId']
            log.debug(f"[{r.headers.get('TrackingID', 'Unknown')}] Subscription ID: {self.id}")
            self.active = True
        else:
            log.warning(f"Subscription failed: [{r.status_code}] {r.text}")
            self.active = False

    def _refresh_subscription(self):
        """ Refresh the subscription

        .. note::

            This method is called automatically by the channels based on the subscription expiration

        Returns:
            bool: True on success, False otherwise

        """

        payload = "<Subscription xmlns=\"http://schema.broadsoft.com/xsi\"><expires>7200</expires></Subscription>"
        r = requests.put(self.events_endpoint + f"/v2.0/subscription/{self.id}",
                         headers={'TrackingID': tracking_id(), **self._headers}, data=payload)
        if r.ok:
            log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                      f"Subscription refresh succeeded")
            return True
        else:
            log.debug(f"[{threading.current_thread().name}][{r.headers.get('TrackingID', 'Unknown')}] "
                      f"Subscription refresh failed: {r.text}")
            return False

    def delete(self):
        """ Delete the subscription from the server

        Once the subscription is deleted, no events for that subscription will be received.

        Returns:
            bool: True on success, False otherwise

        """
        log.debug(f"Deleting XSIEventsSubscription: {self.id}, {self.event_package}")
        r = requests.delete(self.events_endpoint + f"/v2.0/subscription/{self.id}",
                            headers={'TrackingID': tracking_id(), **self._headers})
        if r.ok:
            log.debug(f"[{r.headers.get('TrackingID', 'Unknown')}] Subscription delete succeeded")
            return True
        else:
            log.debug(f"[{r.headers.get('TrackingID', 'Unknown')}] Subscription delete failed: {r.text}")
            return False


class XSICallQueue:
    def __init__(self, call_queue_id: str, org: Org):
        """ Initialize an instance to control calls within a Webex Calling Call Queue.

        This class is used primarily when monitoring XSI Events where there is a need to control calls that come
        into a Call Queue. Since Call Queues are "virtual" users within the call control, there are special methods
        required to deal with those calls.

        Args:
            call_queue_id (str): The ID of the Call Queue as shown in the ``xsi:targetId`` of an XSI Event
            org (Org): The instance of the wxcadm.Org class (i.e. "webex.org"). This is needed to provide the right
                authentication and URLs for the XSI service.
        """
        log.info(f"Starting XSICallCenter for {call_queue_id}")
        self.id = call_queue_id
        self.org = org
        self._calls = []
        self._headers = org._headers
        self._params = org._params

    def attach_call(self, call_id: str):
        """ Attach an active call to the XSICallQueue instance

        Attaching a call provides a :class:`wxcadm.Call` instance that can be used to control the call. Note that not
        all call controls are available to a Call Queue call, but the basic ones, including Transfer, are available.

        Args:
            call_id (str): The callId from the XSI Events message

        Returns:
            Call: The :class:`wxcadm.Call` instance that was attached

        """
        call = Call(self, id=call_id)
        self._calls.append(call)
        return call


class XSI:
    def __init__(self, parent, get_profile: bool = False, cache: bool = False):
        """The XSI class holds all of the relevant XSI data for a Person

        Args:
            parent (Person): The Person who this XSI instance belongs to
            get_profile (bool): Whether or not to automatically get the XSI Profile
            cache (bool): Whether to cache the XSI data (True) or pull it "live" every time (**False**)

        """
        log.info(f"Initializing XSI instance for {parent.email}")
        # First we need to get the XSI User ID for the Webex person we are working with
        log.info("Getting XSI identifiers")
        user_spark_id = decode_spark_id(parent.id)
        self.id = user_spark_id.split("/")[-1]

        # Inherited attributes
        self.xsi_endpoints = parent._parent.xsi
        self._cache = cache

        # API attributes
        self._headers = {"Content-Type": "application/json",
                         "Accept": "application/json",
                         "X-BroadWorks-Protocol-Version": "25.0",
                         **parent._headers}
        self._params = {"format": "json"}

        # Attribute definitions
        self._calls: list = []
        self._profile: dict = {}
        """The XSI Profile for this Person"""
        self._registrations: dict = {}
        """The Registrations associated with this Person"""
        self.fac = None
        self.services = {}
        self._alternate_numbers: dict = {}
        """The Alternate Numbers for the Person"""
        self._anonymous_call_rejection: dict = {}
        """The Anonymous Call Rejection settings for this Person"""
        self._executive_assistant: dict = {}
        """The Executive Assistant settings for this Person"""
        self._executive: dict = {}
        """The Executive settings for this Person"""
        self._single_number_reach: dict = {}
        """The SNR (Office Anywhere) settings for this Person"""
        self._monitoring: dict = {}
        """The BLF/Monitoring settings for this Person"""
        self.conference: object = None

        # Get the profile if we have been asked to
        if get_profile:
            self._profile = self.profile

    def new_call(self, address: str = None, phone: str = 'All', aor: Optional[str] = None):
        """Create a new Call instance

        Args:
            address (str, optional): The address to originate a call to
            phone (str, optional): The phone to use for the call. Valid values are ``All``, ``Primary``,
                or ``SharedCallAppearance``. The SharedCallAppearance argument also requires an address-or-record
                ``aor`` argument with the AoR of the Shared device.
            aor (str, optional): The address-of-record of the Shared device to place the call from

        Returns:
            Call: The Call instance

        """
        # If we got an address, pass it to the new instance
        call = Call(self)
        if address is not None:
            call.originate(address=address, phone=phone, aor=aor)
        self._calls.append(call)
        return call

    def new_conference(self, calls: list, comment: str = ""):
        """
        Crates a new Conference instance. A user can only have one Conference instance, so this will replace any
        previous Conference. At the moment, this **should not be called directly** and will be done dynamically by
        a Call.conference()

        Args:
            calls (list): A list of Call IDs involved in this conference. A conference is always started with only
                two Call IDs. Call IDs after the first two will be ignored.
            comment (str, optional): An optional text comment for the conference

        Returns:
            The instance of the Conference class

        """
        self.conference = Conference(self, calls, comment)
        return self.conference

    def answer_call(self, call_id: str = None):
        """ Answer an incoming call

        If the call_id is not provided, the method will try and answer the latest/only call for the user.

        Args:
            call_id (str, optional): The call_id to answer

        Returns:
            Call: The :class:`Call` instance of the answered call. None is returned if no calls can be found.

        """
        call = self.calls[-1]
        if call is not None:
            call.resume()
            return call
        else:
            return None


    @property
    def calls(self):
        """
        Get the list of active calls and creates Call instances. Also destroys any Call instances that are no longer
        valid.

        Returns:
            list[Call]: List of Call instances

        """
        # First wipe out all of the existing instances
        for call in self._calls:
            del call
        self._calls.clear()
        calls_data: dict = self.__get_xsi_data(f"/v2.0/user/{self.id}/calls")
        log.debug(f"Calls Data: {calls_data}")
        if "call" not in calls_data['Calls']:
            self._calls = []
            return self._calls
        if type(calls_data['Calls']['call']) is dict:
            this_call = Call(self, id=calls_data['Calls']['call']['callId']['$'])
            self._calls.append(this_call)
        elif type(calls_data['Calls']['call']) is list:
            for call in calls_data['Calls']['call']:
                this_call = Call(self, id=call['callId']['$'])
                self._calls.append(this_call)
        return self._calls

    def attach_call(self, call_id: str):
        """ Attach an active call to the XSICallQueue instance

        Attaching a call provides a :class:`wxcadm.Call` instance that can be used to control the call. Note that not
        all call controls are available to a Call Queue call, but the basic ones, including Transfer, are available.

        Args:
            call_id (str): The callId from the XSI Events message

        Returns:
            Call: The :class:`wxcadm.Call` instance that was attached

        """
        call = Call(self, id = call_id)
        self._calls.append(call)
        return call

    def __get_xsi_data(self, url, params: Optional[dict] = None):
        if params is not None:
            params = {**params, **self._params}
        log.debug(f"Sending API Call: {self.xsi_endpoints['actions_endpoint'] + url}")
        log.debug(f"\tHeaders: {self._headers}")
        log.debug(f"\tParams: {params}")
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + url, headers=self._headers, params=params)
        log.debug(f"Response: {r.status_code}")
        if r.status_code == 200:
            try:
                response = r.json()
                # As of the addition of directory() in 3.1.0, we have to be prepared for paginated responses.
                # There is a chance to add that here so that the invoking method doesn't have to care about it, but
                # for now we are going to just return the dict we get and let the other method decide if it needs more
                # records and send this method the right params
            except json.decoder.JSONDecodeError:
                response = r.text
            return_data = response
        elif r.status_code == 404:
            return_data = False
        else:
            return_data = False
        return return_data

    @property
    def executive(self):
        """The Executive Assistant settings for this Person"""
        if not self._executive or not self._cache:
            self._executive = self.__get_xsi_data(f"/v2.0/user/{self.id}/services/Executive")
        return self._executive

    @property
    def executive_assistant(self):
        """The Executive Assistant settings for this Person"""
        if not self._executive_assistant or not self._cache:
            self._executive_assistant = self.__get_xsi_data(f"/v2.0/user/{self.id}/services/ExecutiveAssistant")
        return self._executive_assistant

    @property
    def monitoring(self):
        """The Monitoring/BLF settings for this person"""
        if not self._monitoring or not self._cache:
            self._monitoring = self.__get_xsi_data(f"/v2.0/user/{self.id}/services/BusyLampField")
        return self._monitoring

    @property
    def single_number_reach(self):
        """The SNR (Office Anywhere) settings for this Person"""
        if not self._single_number_reach or not self._cache:
            self._single_number_reach = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/services/BroadWorksAnywhere")
        return self._single_number_reach

    @property
    def anonymous_call_rejection(self):
        """The Anonymous Call Rejection settings for this Person"""
        if not self._anonymous_call_rejection or not self._cache:
            self._anonymous_call_rejection = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/services/AnonymousCallRejection")
        return self._anonymous_call_rejection

    @property
    def alternate_numbers(self):
        """The Alternate Numbers for this Person"""
        if not self._alternate_numbers or not self._cache:
            self._alternate_numbers = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/services/AlternateNumbers")
        return self._alternate_numbers

    @property
    def profile(self):
        """The XSI Profile for this Person"""
        log.debug("Getting XSI Profile")
        if not self._profile or not self._cache:
            profile_data: dict = \
                self.__get_xsi_data(f"/v2.0/user/{self.id}/profile")
            # The following is a mapping of the raw XSI format to the profile attribute
            log.debug(f"User Profile: {profile_data}")
            if profile_data:
                self._profile['registrations_url'] = profile_data['Profile']['registrations']['$']
                self._profile['schedule_url'] = profile_data['Profile']['scheduleList']['$']
                self._profile['fac_url'] = profile_data['Profile']['fac']['$']
                self._profile['country_code'] = profile_data['Profile']['countryCode']['$']
                self._profile['user_id'] = profile_data['Profile']['details']['userId']['$']
                self._profile['group_id'] = profile_data['Profile']['details']['groupId']['$']
                self._profile['service_provider'] = profile_data['Profile']['details']['serviceProvider']['$']
                # Not everyone has a number and/or extension, so we need to check to see if there are there
                if "number" in profile_data['Profile']['details']:
                    self._profile['number'] = profile_data['Profile']['details']['number']['$']
                if "extension" in profile_data['Profile']['details']:
                    self._profile['extension'] = profile_data['Profile']['details']['extension']['$']
                self._profile['raw'] = profile_data
            else:
                self._profile = None
        return self._profile

    @property
    def registrations(self):
        """The device registrations associated with this Person"""
        if not self._registrations or not self._cache:
            # If we don't have a registrations URL, because we don't have the profile, go get it
            if "registrations_url" not in self._profile:
                self._profile = self.profile
            self._registrations = self.__get_xsi_data(self._profile['registrations_url'])
        return self._registrations

    def get_fac(self):
        # If we don't have a FAC URL, go get it
        if "fac_url" not in self._profile:
            self.profile
        r = requests.get(self.xsi_endpoints['actions_endpoint'] + self._profile['fac_url'],
                         headers=self._headers, params=self._params)
        response = r.json()
        self.fac = response
        return self.fac

    def get_services(self):
        # TODO There are still some services that we should collect more data for. For example, BroadWorks
        #       Anywhere has Locations that aren't pulled without a separate call.

        r = requests.get(self.xsi_endpoints['actions_endpoint'] + "/v2.0/user/" + self.id + "/services",
                         headers=self._headers, params=self._params)
        response = r.json()
        self.services['list'] = response['Services']['service']
        # Now that we have all of the services, pulling the data is pretty easy since the URL
        # is present in the response. Loop through the services and collect the data
        # Some services have no config so there is no URI and we'll just populate them as True
        for service in self.services['list']:
            if "uri" in service:
                r = requests.get(self.xsi_endpoints['actions_endpoint'] + service['uri']['$'],
                                 headers=self._headers, params=self._params)
                # Getting well-formatted JSON doesn't always work. If we can decode the JSON, use it
                # If not, just store the raw text. At some point, it would make sense to parse the text
                # and build the dict directly
                try:
                    response = r.json()
                except json.decoder.JSONDecodeError:
                    response = r.text
                self.services[service['name']['$']] = response
            else:
                self.services[service['name']['$']] = True
        return self.services

    def directory(self,
                  type: Optional[str] = 'Enterprise',
                  first_name: Optional[str] = None,
                  last_name: Optional[str] = None,
                  name: Optional[str] = None,
                  user_id: Optional[str] = None,
                  group_id: Optional[str] = None,
                  number: Optional[str] = None,
                  extension: Optional[str] = None,
                  mobile_number: Optional[str] = None,
                  department: Optional[str] = None,
                  email: Optional[str] = None,
                  any_match: Optional[bool] = False,) -> list[dict]:
        """ Search the Webex Calling directories

        When search filters are applied as arguments, the directory will be searched by those values. If the desire is
        to match any one of the values (logical OR), the ``any_match`` parameter should also be set to True. Note that
        each directory type supports its own filter criteria and not all criteria are available across all directories.
        The following table shows the filter arguments that are available for each type.

        Note that all directory filter arguments are case-sensitive within Webex Calling. If you want to perform a
        case-insensitive search, append "/i" to the search string. For example, ``first_name='John/i'`` will match
        "John", "john" and "JOHN".

        .. list-table:: Directory Types
            :widths: 25 75
            :header-rows: 1

            * - Directory Type
              - Available Filters
            * - Enterprise
              - first_name, last_name, name, user_id, group_id, number, extension, mobile_number, department, email
            * - Group
              - first_name, last_name, name, user_id, group_id, number, extension, mobile_number, department, email
            * - Personal
              - name, number


        Args:
            type (str, Optional): The type of diectory to search. Valid values are ``Enterprise``,
                ``Group``, and ``Personal``. Defaults to ``Enterprise``.
            first_name (str, optional): The First Name field in the directory
            last_name (str, optional): The Last Name field in the directory
            name (str, optional): The "combined" name field that allows a search based on First Name and Last Name
            user_id (str, optional): The User ID used on the Webex Calling call control platform. This is the User ID
                that is displayed for the user across all of the XSI APIs
            group_id (str, optional): The Group ID used on the Webex Calling call control platform. This ID is unique
                to the Webex Calling Location and can be used to find all users at a specific Location.
            number (str, optional): The Webex Calling phone number
            extension (str, optional): The Webex Calling extension
            mobile_number (str, optional): The user's mobile number, if populated by Directory Sync
            department (str, optional): The user's department, if populated by Directory Sync
            email (str, optional): The user's email address
            any_match (bool, optional): When True, all arguments will be treated uniquely (OR) and results will be
                returned if any argument matches. For exmaple, if the arguments
                ``first_name=Joe,last_name=Smith,any_match=True`` are passed, the results will include Joe Smith, but
                will also include Joe James and Lisa Smith. Defaults to ``False``.

        Returns:
            list[dict]: A list of matching records, represented as a dictionary. If there are no matches, an empty
                list is returned. If an invalid directory type is requested, None is returned.

        """
        type = type.title()
        log.info(f"Getting {type} directory")
        log.debug(f"\tArgs: {locals()}")
        if type.upper() in ['ENTERPRISE', 'GROUP']:
            params = {
                'firstName': first_name,
                'lastName': last_name,
                'name': name,
                'userId': user_id,
                'groupId': group_id,
                'number': number,
                'extension': extension,
                'mobileNo': mobile_number,
                'department': department,
                'emailAddress': email,
                'searchCriteriaModeOr': any_match,
            }
        elif type.upper() in ['PERSONAL']:
            params = {
                'name': name,
                'number': number
            }
        else:
            log.warning(f"Directory type {type} is not valid")
            return None

        # Set some vars to keep track of the number of records we get and how many more we expect
        more_records = True
        num_records = 0
        next_index = 1
        get_count = 50
        return_records = []
        while more_records is True:
            response = self.__get_xsi_data(f'/v2.0/user/{self.id}/directories/{type}',
                                           params={'start': next_index, 'results': get_count, **params})
            num_records += int(response[type]['numberOfRecords']['$'])
            total_records = int(response[type]['totalAvailableRecords']['$'])
            log.debug(f"Received {num_records}/{total_records} records")
            if int(response[type]['numberOfRecords']['$']) == 0: # No records returned
                return return_records
            if type.upper() in ['ENTERPRISE', 'GROUP']:
                key = f"{type.lower()}Directory"
                if isinstance(response[type][key]['directoryDetails'], dict):   # If we get a dict instead of a list
                    return_records.append(response[type][key]['directoryDetails'])
                else:
                    for entry in response[type][key]['directoryDetails']:
                        return_records.append(entry)
            if type.upper() in ['PERSONAL']:
                if isinstance(response[type]['entry'], dict):   # Single entry returned
                    return_records.append(response[type]['entry'])
                else:
                    for entry in response[type]['entry']:
                        return_records.append(entry)

            # Check and see if we need to get more records
            if num_records < total_records:
                more_records = True
                next_index += int(response[type]['numberOfRecords']['$'])
            else:
                more_records = False

        return return_records



class Call:
    """
    The Call class represents a call for a person. Since Webex supports calls in the Webex API as well as XSI API,
    the class supports both styles. When initialized, the parent instance is checked to see if it is a Person
    instance or an XSI instance. At the moment, the Webex API only supports user-scoped call control, so most of the
    development focus right now is the XSI API, which is more feature-rich

    """

    def __init__(self, parent: Union[Person, XSI, XSICallQueue],
                 id: str = "", address: str = "", user_id: str = ""):
        """Inititalize a Call instance for a Person

        Args:
            parent (XSI): The Person or XSI instance that owns this Call
            id (str, optional): The Call ID of a known call. Usually only done during a XSI.calls method
            address (str, optional): The address to originate a call to when the instance is created

        Returns:
            Call: This Call instance

        """
        self._parent = parent
        """The Person or XSI instance that owns this Call"""
        if user_id:
            self._userid = user_id
        else:
            self._userid: str = self._parent.id
        """The Person or XSI ID inherited from the parent"""
        self._headers = self._parent._headers
        self._params = self._parent._params
        self._url: str = ""
        self.id: str = id
        """The Call ID for this call"""
        self._external_tracking_id: str = ""
        """The externalTrackingId used by XSI"""
        self._status: dict = {}
        """The status of the call"""
        self.held: bool = False
        """ Whether or not the call is on hold """
        self._transfer_call = None
        if type(self._parent) is wxcadm.person.Person:
            # This is where we set things based on whether the parent is a Person
            self._url = _url_base
            self.type = "Person"
            pass
        elif type(self._parent) is wxcadm.xsi.XSICallQueue:
            self._url = self._parent.org.xsi['actions_endpoint'] + f"/v2.0/callcenter/{self._userid}/calls"
            self.type = "CallQueue"
        elif type(self._parent) is wxcadm.xsi.XSI:
            # The Call parent is XSI
            self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls"
            self.type = "XSI"
        elif type(self._parent) is wxcadm.xsi.Call:
            # Another Call created this Call instance (probably for a transfer or conference
            self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._parent._userid}/calls"
            self.type = "Call"
        elif type(self._parent) is wxcadm.org.Org:
            # Basically manually creating a call instance, probably based on an XSI Event or some other way
            # that we determined the call ID and the user it was for
            self._url = self._parent.xsi['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls"
            self.type = "Org/Other"

        if address:
            self.originate(address)

    def originate(self, address: str,
                  comment: str = "",
                  phone: str = 'All',
                  aor: Optional[str] = None,
                  executive: str = None):
        """Originate a call on behalf of the Person

        The optional ``executive`` argument takes an extension or phone number and allows the call to be placed
        on behalf of an executive to which the Person is assigned as an executive assistant. If the Exectuve call is
        not allowed by the system, an :exc:`NotAllowed` is raised.

        Args:
            address (str): The address (usually a phone number) to originate the call to
            comment (str, optional): Text comment to attach to the call
            phone (str, optional): The phone to use for the call. Valid values are ``All``, ``Primary``,
                or ``SharedCallAppearance``. The SharedCallAppearance argument also requires an address-or-record
                ``aor`` argument with the AoR of the Shared device.
            aor (str, optional): The address-of-record of the Shared device to place the call from
            executive (str, optional): The phone number or extension of the Executive to place the call on behalf of

        Returns:
            bool: True when the call was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the Person is not able to place the call for an Executive

        """
        if executive is not None:
            log.info(f"Originating a call to {address} for {self._userid} on behalf of Exec {executive}")
            # TODO: The API call will fail if the Assistant can't place the call for the Exec, but we should
            #   really check that first and not waste the API call (although those take API calls, too)
            params = {"address": address, "executiveAddress": executive}
            r = requests.post(self._url + "/ExecutiveAssistantInitiateCall", headers=self._headers, params=params)
            if r.status_code == 201:
                response = r.json()
                self.id = response['CallStartInfo']['callId']['$']
                self._external_tracking_id = response['CallStartInfo']['externalTrackingId']['$']
                return True
            else:
                raise NotAllowed("Person is not allowed to place calls on behalf of this executive")
        else:
            log.info(f"Originating a call to {address} for {self._userid}")
            params = {"address": address, "info": comment, "location": phone}
            if aor is not None:
                params['locationAddress'] = aor
            r = requests.post(self._url + "/new", headers=self._headers, params=params)
            if r.status_code == 201:
                response = r.json()
                self.id = response['CallStartInfo']['callId']['$']
                self._external_tracking_id = response['CallStartInfo']['externalTrackingId']['$']
                return True
            else:
                return False

    def exec_push(self):
        """Pushes the active Executive Assistant call to the Executive

        This method will only complete if the following conditions are met:
        * The user is an Assistant
        * The call must be active and answered

        Returns:
            bool: True if the push was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the call does not meet the conditions to be pushed

        """
        r = requests.put(self._url + f"/{self.id}/ExecutiveAssistantCallPush", headers=self._headers)
        return XSIResponse(r)

    def hangup(self, decline: bool = False):
        """Hang up the call

        Returns:
            bool: Whether the command was successful

        """
        if decline is True:
            params = {"decline": decline}
        else:
            params = {}
        log.info(f"Hanging up call ID: {self.id}")
        r = requests.delete(self._url + f"/{self.id}",
                            headers=self._headers, params=params)
        return XSIResponse(r)

    @property
    def status(self):
        """The status of the call

        Returns:
            dict::

                {
                'network_call_id' (str): The unique identifier for the Network side of the call
                'personality'(str): The user personalty (Originator or Terminator)
                'state' (str): The state of the call
                'remote_party' (dict): {
                    'address' (str): The address of the remote party
                    'call_type' (str): The call type
                    }
                'endpoint' (dict): {
                    'type' (str): The type of endpoint being used
                    'AoR' (str): The Address of Record for the endpoint
                    }
                'appearance' (str): The Call Appearance number
                'start_time' (str): The UNIX timestanp of the start of the call
                'answer_time' (str): The UNIX timestamp when the call was answered
                'status_time' (str): The UNIX timestamp of the status response
                }

        """
        log.info(f"Getting call status")
        r = requests.get(self._url + f"/{self.id}",
                         headers=self._headers)
        response = r.json()
        log.debug(f"Call Status response: {response}")
        if r.status_code == 200:
            return_data = {}
            ## Added key checking 3.0.4
            call_status = response['Call']
            if 'networkCallId' in call_status:
                return_data['network_call_id'] = call_status['networkCallId']['$']
            if 'personality' in call_status:
                return_data['personality'] = call_status['personality']['$']
            if 'state' in call_status:
                return_data['state'] = call_status['state']['$']
            if 'remoteParty' in call_status:
                return_data['remote_party'] = {
                    "address": call_status['remoteParty']['address']['$'],
                    "call_type": call_status['remoteParty']['callType']['$']
                }
            if 'endpoint' in call_status:
                return_data['endpoint'] = {
                    "type": call_status['endpoint']['@xsi1:type'],
                    "aor": call_status['endpoint']['addressOfRecord']['$']
                }
            if 'appearance' in call_status:
                return_data['appearance'] = call_status['appearance']['$']
            if 'diversionInhibited' in call_status:
                return_data['diversion_inhibited'] = call_status['diversionInhibited']
            if 'startTime' in call_status:
                return_data['start_time'] = call_status['startTime']['$']
            if 'answerTime' in call_status:
                return_data['answer_time'] = call_status['answerTime']['$']
            else:
                return_data['answer_time'] = None
            return_data['status_time'] = int(time.time())
            return return_data
        else:
            return False

    def transfer(self, address: str, type: str = "blind"):
        """Transfer the call to the selected address.

        Type of transfer can be controlled with `type` param. VM transfers will transfer the call directly to the voice
        mail of the address, even if the address is the user's own address. Attended transfers require a subsequent call
        to `finish_transfer()` when the actual transfer should happen.

        Args:
            address (str): The address (usually a phone number or extension) to transfer the call to
            type (str): ['blind','vm','attended']:
                The type of transfer.

        Returns:
            bool: True if successful. False if unsuccessful

        """
        log.info(f"Transferring call {self.id} to {address} for {self._userid}")
        # Set the address param to be passed to XSI
        if self.type == "CallQueue":
            params = {"phoneno": address}
        else:
            params = {"address": address}
        # Handle an attended transfer first. Anything else is assumed to be blind
        if type.lower() == "attended":
            # Attended transfer requires the first call to be put on hold and the second call to be
            # placed, so those are here. A separate call to finish_transfer will be required when the transfer should
            # happen.
            self.hold()
            self._transfer_call = self._parent.new_call()
            self._transfer_call.originate(address)
            return True
        elif type.lower() == "vm":
            r = requests.put(self._url + f"/{self.id}/VmTransfer", headers=self._headers, params=params)
            return XSIResponse(r)
        elif type.lower() == "mute":
            r = requests.put(self._url + f"/{self.id}/MuteTransfer", headers=self._headers, params=params)
            return XSIResponse(r)
        else:
            r = requests.put(self._url + f"/{self.id}/BlindTransfer", headers=self._headers, params=params)
            return XSIResponse(r)

    def finish_transfer(self):
        """
        Complete an Attended Transfer. This method will only complete if a `transfer(address, type="attended")`
        has been done first.

        Returns:
            bool: Whether the transfer completes

        """
        log.info("Completing transfer...")
        r = requests.put(self._url + f"/{self.id}/ConsultTransfer/{self._transfer_call.id}", headers=self._headers)
        return XSIResponse(r)

    def conference(self, address: str = ""):
        """
        Starts a multi-party conference. If the call is already held and an attended transfer is in progress,
        meaning the user is already talking to the transfer-to user, this method will bridge the calls.

        When an address is passed, the existing call will be placed on hold, the second call will be originated, and the
        conference will be connected as soon as the second party answers. If the desired behavior is not to connect the
        parties until later, the calls should be created separately and bridged later.

        Args:
            address (str, optional): The address (usually a phone number or extension) to conference to. Not needed
                when the call is already part of an Attended Transfer

        Returns:
            bool: True if the conference is successful

        """
        # First, check to see if the call is already part of an attended transfer. If so, just build the conference
        # based on the two call IDs
        if self._transfer_call:
            xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
                  f"<Conference xmlns=\"http://schema.broadsoft.com/xsi\">" \
                  f"<conferenceParticipantList>" \
                  f"<conferenceParticipant>" \
                  f"<callId>{self.id}</callId>" \
                  f"</conferenceParticipant>" \
                  f"<conferenceParticipant>" \
                  f"<callId>{self._transfer_call.id}</callId>" \
                  f"</conferenceParticipant>" \
                  f"</conferenceParticipantList>" \
                  f"</Conference>"
            # Building the XML by hand for right now. Probably going to replace it with something JSON-friendly
            headers = self._headers
            headers['Content-Type'] = "application/xml; charset=UTF-8"
            r = requests.post(self._url + f"/Conference", headers=headers, data=xml)
            if r.status_code in [200, 201, 204]:
                return self._parent.new_conference([self.id, self._transfer_call.id])
            else:
                return False
        else:
            # Put the current call on hold if it isn't already
            if self.held is False:
                self.hold()
            # Build the second call
            second_call = self._parent.new_call(address=address)
            # Get the status of the second call. We cannot complete the conference until it is answered.
            call_state = second_call.status.get('state', 'unknown')
            while call_state != 'Active':
                call_state = second_call.status.get('state', 'unknown')

            xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>" \
                  f"<Conference xmlns=\"http://schema.broadsoft.com/xsi\">" \
                  f"<conferenceParticipantList>" \
                  f"<conferenceParticipant>" \
                  f"<callId>{self.id}</callId>" \
                  f"</conferenceParticipant>" \
                  f"<conferenceParticipant>" \
                  f"<callId>{second_call.id}</callId>" \
                  f"</conferenceParticipant>" \
                  f"</conferenceParticipantList>" \
                  f"</Conference>"
            headers = self._headers
            headers['Content-Type'] = "application/xml; charset=UTF-8"
            r = requests.post(self._url + f"/Conference", headers=headers, data=xml)
            if r.status_code in [200, 201, 204]:
                return self._parent.new_conference([self.id, second_call.id])
            else:
                return False

    def send_dtmf(self, dtmf: str):
        """Transmit DTMF tones outbound

        Args:
            dtmf (str): The string of dtmf digits to send. Accepted digits 0-9, star, pound. A comma will pause
                between digits (i.e. "23456#,123")

        Returns:
            bool: True if the dtmf was sent successfully
        """
        params = {"playdtmf": str(dtmf)}
        r = requests.put(self._url + f"/{self.id}/TransmitDTMF", headers=self._headers, params=params)
        return XSIResponse(r)

    def hold(self):
        """Place the call on hold

        Returns:
            bool: Whether the hold command was successful

        """
        r = requests.put(self._url + f"/{self.id}/Hold", headers=self._headers)
        self.held = True
        return XSIResponse(r)

    def resume(self):
        """Resume a call that was placed on hold

        Returns:
            bool: Whether the command was successful

        """
        r = requests.put(self._url + f"/{self.id}/Talk", headers=self._headers)
        self.held = False
        return XSIResponse(r)

    def answer(self):
        r = requests.put(self._url + f"/{self.id}/Talk", headers=self._headers)
        self.held = False
        return XSIResponse(r)

    def park(self, extension: str = None):
        """Park the call

        When called with the ``extension`` argument, the call will be parked using the Call Park Extension feature at
        the chosen extension. When called without ``extension``, the call will be parked with the Group Call Park
        feature, which assigns an extension automatically. Note that Group Call Park requires the Person to be part
        of the Park Group. If a Group Call Park is attemped for a user that isn't park of a Park Group, a
        :exc:`NotAllowed` exception will be raised.

        Args:
            extension (str, optional): The extension to park the call against

        Returns:
            str: The extension that the call is parked against

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the user is not part of a Park Group or the extension is already busy

        """
        if extension is None:
            r = requests.put(self._url + f"/{self.id}/GroupCallPark", headers=self._headers)
            if r.status_code == 200:
                self._park_location = r.headers['Content-Location']
                self._park_address = self._park_location.split("?")[-1]
                self._park_extension = self._park_address.split(":")[-1]
                return self._park_extension
            else:
                raise NotAllowed("The call cannot be parked")
        else:
            params = {"address": extension}
            r = requests.put(self._url + f"/{self.id}/Park", headers=self._headers, params=params)
            if r.status_code == 200:
                self._park_location = r.headers['Content-Location']
                self._park_address = self._park_location.split("?")[-1]
                self._park_extension = self._park_address.split(":")[-1]
                return self._park_extension
            else:
                raise NotAllowed("The call cannot be parked")

    def reconnect(self):
        """Retrieves the call from hold **and releases all other calls**"""
        r = requests.put(self._url + f"{self.id}/Reconnect", headers=self._headers)
        self.held = False
        return XSIResponse(r)

    def recording(self, action: str):
        """Control the recording of the call

        For the recording() method to work, the user must have Call Recording enabled. Any unsuccessful attempt to
        record a call for a user who is not enabled for Call Recording will raise a NotAllowed exception.

        Args:
            action (str): The action to perform.

                'start': Starts recording, if it isn't in process already

                'stop': Stops the recording. Only applies to On Demand call recording.

                'pause': Pauses the recording

                'resume': Resume a paused recording

        Returns:
            bool: True if the recording command was accepted by the server

        Raises:
            wxcadm.exceptions.NotAllowed: The action is not allowed. Normally it indicates that the user does not have
                the Call Recording service assigned.
            ValueError: Raised when the action is not recognized.

        """
        log.info(f"Changing Recoding with an action: {action}")

        if action.lower() == "start":
            r = requests.put(self._url + f"/{self.id}/Record", headers=self._headers)
        elif action.lower() == "resume":
            r = requests.put(self._url + f"/{self.id}/ResumeRecording", headers=self._headers)
        elif action.lower() == "stop":
            r = requests.put(self._url + f"/{self.id}/StopRecording", headers=self._headers)
        elif action.lower() == "resume":
            r = requests.put(self._url + f"/{self.id}/PauseRecording", headers=self._headers)
        else:
            raise ValueError(f"{action} is not a valid action")

        log.debug(f"XSI Response:\n\t{r.text}")
        return XSIResponse(r)


class Conference:
    """The class for Conference Calls started by a Call.conference()"""

    def __init__(self, parent: object, calls: list, comment: str = ""):
        """Initialize a Conference instance for an XSI instance

        Args:
            parent (XSI): The XSI instance that owns this conference
            calls (list): Call IDs associated with the Conference. Always two Call IDs to start a Conference.
                Any additional Call IDs will be added to the conference as it is created.
            comment (str, optional): An optional text comment for the Conference

        Returns:
            Conference: This instance of the Conference class

        """
        self._parent: XSI = parent
        self._calls: list = calls
        self._userid = self._parent.id
        self._headers = self._parent._headers
        self._url = self._parent.xsi_endpoints['actions_endpoint'] + f"/v2.0/user/{self._userid}/calls/Conference/"
        self.comment: str = comment
        """Text comment associated with the Conference"""

    def deaf(self, call: str):
        """Stop audio and video from being sent to a participant. Audio and video from that participant are unaffected.

        Args:
            call (str): The Call ID to make deaf. The Call ID must be part of the Conference.

        Returns:
            bool: True if the command was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the server rejects the command

        """
        r = requests.put(self._url + f"{call}/Deaf", headers=self._headers)
        return XSIResponse(r)

    def mute(self, call: str):
        """Mute a conference participant. Audio and video sent to the participant are unaffected.

        Args:
            call (str): The Call ID to mute. The Call ID must be part of the Conference

        Returns:
            bool: True if the command was successful

        Raises:
            wxcadm.exceptions.NotAllowed: Raised when the server rejects the command

        """
        r = requests.put(self._url + f"{call}/Mute", headers=self._headers)
        return XSIResponse(r)

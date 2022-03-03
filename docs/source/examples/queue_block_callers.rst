Call Queue - Block Callers by Number
====================================
Although Webex Calling does provide Selective Call Forwarding for Call Queues, they have to be maintained for each Queue.
If there is a need to block a nuisance caller across all Call Queues company-wide, XSI Events can be used to monitor
calls into all Call Queues, and XSI Actions can take control of that call, either by ending the call or by transferring
it to an unused extension, which will play a message. It would also be possible to transfer to a custom announcement
informing the caller that they are blocked.

**Note** that you have to have XSI enabled for your Organization in order to use the XSI classes within **wxcadm**.

.. code-block:: python

    import wxcadm
    import queue

    # Define the list of "blocked" numbers
    blocked_callers = ['+181815551234',
                       '+17655559876']
    # Set up the connection to Webex, making sure to include get_xsi=True
    access_token = "Your API Access Token"
    webex = wxcadm.Webex(access_token, get_xsi=True)

    # Start the connection to XSI Events, open a channel and subscribe to the Call Center Queue event package
    events = wxcadm.XSIEvents(webex.org)
    events_queue = queue.Queue()
    channel = events.open_channel(events_queue)
    channel.subscribe("Call Center Queue")

    # Start a loop to watch incoming messages
    while True:
        message = events_queue.get()
        event_type = message['xsi:Event']['xsi:eventData']['@xsi1:type']
        call_queue_id = message['xsi:Event']['xsi:targetId']
        if event_type == "xsi:ACDCallAddedEvent":
            caller_number = message['xsi:Event']['xsi:eventData']['xsi:queueEntry']['xsi:remoteParty']['xsi:address']['#text']
            call_id = message['xsi:Event']['xsi:eventData']['xsi:queueEntry']['xsi:callId']
            # The address comes in the Events as a tel: URI so let's clean it up to get jus the number
            caller_number = caller_number.split(":")[-1]
            if caller_number in blocked_callers:
                # This is a blocked user. In our example, we block them by transferring them to an unused extension
                xsi = wxcadm.XSICallQueue(call_queue_id, org=webex.org)
                call = xsi.attach_call(call_id)
                call.transfer("8889")
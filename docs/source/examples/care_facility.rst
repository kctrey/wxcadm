Alert When User Goes Off-Hook Without Dialing for Too Long
==========================================================
This type of script might be used for a Care Facility where a user might have a medical emergency and is not able
to dial the phone. The script uses XSI Events to monitor the hook and call status for all users and can generate
any action when the defined timer condition is met.

Note that this script would require modification to be suitable for a Production environment, but the basic logic
would remain the same.

.. code-block:: python

    import wxcadm
    import queue
    import time
    import threading

    # Start the connection to Webex
    webex_access_token = "Your API Access Token"
    webex = wxcadm.Webex(webex_access_token, get_xsi=True, fast_mode=True)

    # Start XSI for all Webex Calling users and cache the profile
    xsi_user_map = {}
    for person in webex.org.get_wxc_people():
        person.start_xsi(get_profile=True, cache=True)
        xsi_user_map[person.xsi.profile['user_id']] = person

    # Set up the Events connection and subscribe to Advanced Call package
    events = wxcadm.XSIEvents(webex.org)
    events_queue = queue.Queue()
    channel = events.open_channel(events_queue)
    channel.subscribe("Advanced Call")

    # The channel and the queue are ready for calls
    print("Ready for calls...")

    # Set up a place to store all the users and their off-hook times
    off_hook_phones = {}


    # We need a threaded (or async) function to watch the off_hook_phones and alarm
    def offhook_watcher():
        alarm_after_seconds = 10  # How many seconds to wait after off-hook to alarm
        loop = True
        while loop is True:
            # Make a copy of the off_hook_phones since it isn't thread-safe
            phones = off_hook_phones.copy()
            for user, hooktime in phones.items():
                time_now = time.time()
                offhook_time = hooktime
                if time_now - offhook_time > alarm_after_seconds:
                    # Put any alarm actions you want here
                    print(f"{user} has been off-hook for too long. Sending alert.")
                    # Reset the timer, so we alert every X seconds
                    off_hook_phones[user] = time_now


    # The main loop that watches all the messages. Could easily be a thread of its own.
    main_loop = True
    offhook_watcher_thread = threading.Thread(target=offhook_watcher, daemon=True)
    offhook_watcher_thread.start()
    while main_loop is True:
        message = events_queue.get()
        print(xsi_user_map[message['xsi:Event']['xsi:targetId']].display_name, end=" ")
        print(message['xsi:Event']['xsi:eventData']['@xsi1:type'])
        print(f"\t{message}")
        if message['xsi:Event']['xsi:eventData']['@xsi1:type'] == "xsi:HookStatusEvent":
            hook_status = message['xsi:Event']['xsi:eventData']['xsi:hookStatus']
            if hook_status == "Off-Hook":
                off_hook_phones[xsi_user_map[message['xsi:Event']['xsi:targetId']].display_name] = time.time()
            elif hook_status == "On-Hook" and xsi_user_map[message['xsi:Event']['xsi:targetId']].display_name in off_hook_phones.keys():
                del off_hook_phones[xsi_user_map[message['xsi:Event']['xsi:targetId']].display_name]
        elif message['xsi:Event']['xsi:eventData']['@xsi1:type'] in ['xsi:CallOriginatedEvent', 'xsi:CallAnsweredEvent']:
            if xsi_user_map[message['xsi:Event']['xsi:targetId']].display_name in off_hook_phones.keys():
                del off_hook_phones[xsi_user_map[message['xsi:Event']['xsi:targetId']].display_name]


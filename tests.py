""" tests.py - Script to test wxcadm and the Webex APIs

This script can be used to test wxcadm with a valid Webex API Access Token. It runs through basic GET/PUT tests without
making any changes on Webex. Its primary use is to validate the API endpoints and JSON payloads used by wxcadm, but also
provides some basic information about the Webex Org that the token has access to.

To use the script, create a .env file with the WEBEX_ACCESS_TOKEN variable set to a valid API Access Token.
See .env.example for a sample. env file. You can also set the WEBEX_ACCESS_TOKEN environment variable for your OS.

"""
import time
import wxcadm
import queue
import os
from dotenv import load_dotenv

# A few variables used throughout the script
test_start = time.time()

# Load the .env file for the tests
print("Getting WEBEX_ACCESS_TOKEN from environment")
load_dotenv()

access_token = os.getenv("WEBEX_ACCESS_TOKEN")
if not access_token:
    print("No WEBEX_ACCESS_TOKEN found. Cannot continue.")
    exit(1)

passed_tests = []
failed_tests = []

def start_test():
    print(f"Testing {test}...", end="")
    global test_start
    test_start = time.time()

def pass_test():
    test_end = time.time()
    test_duration = round(test_end - test_start, 2)
    passed_tests.append(test)
    print(f"passed [{test_duration}s]")

def fail_test():
    test_end = time.time()
    test_duration = round(test_end - test_start, 2)
    failed_tests.append(test)
    print(f"failed [{test_duration}s]")

# Test bad access token handling
test = "TokenError"
start_test()
try:
    bad_webex = wxcadm.Webex("Bad Access Token")
except wxcadm.TokenError:
    pass_test()
except:
    fail_test()

# Create a Webex instance for further testing
test = "Webex instance"
start_test()
try:
    webex = wxcadm.Webex(access_token, fast_mode=True)
except:
    fail_test()
    print("Cannot continue without valid token and Webex instance.")
    exit(1)
else:
    pass_test()

# Get the count of records, just for debugging purpose later
people_count = len(webex.org.people)
locations_count = len(webex.org.locations)
print(f"People Count: {people_count}")
print(f"Locations Count: {locations_count}")

# Location tests
test = "Location Schedules get"
start_test()
location = webex.org.locations[0]
try:
    sched = location.schedules
except:
    fail_test()
else:
    pass_test()


# Get Call Queues and make sure data is populated correctly
test = "CallQueue get"
start_test()
try:
    call_queues = webex.org.get_call_queues()
except:
    fail_test()
else:
    pass_test()
    print(f"Call Queues: {len(call_queues)}")
    test = "CallQueue size check"
    start_test()
    if len(call_queues) == len(webex.org.call_queues):
        pass_test()
    else:
        fail_test()
    if len(call_queues) > 0:
        test = "CallQueue config"
        start_test()
        try:
            call_queues[0].get_queue_config()
        except:
            fail_test()
        else:
            pass_test()
        test = "CallQueue forwarding"
        start_test()
        try:
            call_queues[0].get_queue_forwarding()
        except:
            fail_test()
        else:
            pass_test()
        test = "CallQueue config push"
        start_test()
        try:
            config = call_queues[0].push()
        except:
            fail_test()
        else:
            pass_test()
    else:
        print("No Call Queues found. Skipping Call Queue config tests.")


# Person tests
test = "Person full config"
start_test()
person = webex.org.get_wxc_people()[0]
try:
    full_config = person.get_full_config()
except:
    fail_test()
else:
    pass_test()
test = "Person by email"
start_test()
found_person = webex.org.get_person_by_email(person.email)
if person.id == found_person.id:
    pass_test()
else:
    fail_test()
test = "Person VM Config push"
start_test()
try:
    person.push_vm_config()
except:
    fail_test()
else:
    pass_test()
test = "Person CF push"
start_test()
try:
    person.push_cf_config()
except:
    fail_test()
else:
    pass_test()
test = "Person Monitoring get"
start_test()
try:
    mon = person.monitoring
except:
    fail_test()
else:
    pass_test()
test = "Person Hoteling get"
start_test()
try:
    hotel = person.hoteling
except:
    fail_test()
else:
    pass_test()
test = "Person get Outgoing Call Permissions"
start_test()
try:
    ocp = person.outgoing_permission
except:
    fail_test()
else:
    if ocp is False:
        fail_test()
    else:
        pass_test()
test = "Person set Outgoing Call Permissions"
start_test()
try:
    if ocp:
        success = person.set_outgoing_permission(ocp)
    else:
        success = person.set_outgoing_permission()
except:
    fail_test()
else:
    if success:
        pass_test()
    else:
        fail_test()


# XSI tests
test = "XSI availability"
start_test()
endpoints = webex.org.get_xsi_endpoints()
if endpoints is not None:
    pass_test()
    test = "XSI profile"
    start_test()
    person.start_xsi()
    try:
        person.xsi.profile
    except:
        fail_test()
    else:
        pass_test()
    test = "XSI Events"
    start_test()
    events = wxcadm.XSIEvents(webex.org)
    events_queue = queue.Queue()
    channel = events.open_channel(events_queue)
    channel.subscribe("Advanced Call")
    channel.unsubscribe(channel.subscriptions[0].id)
    try:
        message = events_queue.get()
        print(message['xsi:Event']['xsi:eventData']['@xsi1:type'] + "...", end="")
    except:
        fail_test()
    else:
        pass_test()
else:
    fail_test()
    print("XSI not enabled. Skipping XSI tests.")

print(f"Failed Tests: {failed_tests}")

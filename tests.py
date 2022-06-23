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
import logging
import random

# Set up a log file
logging.basicConfig(level=logging.INFO,
                    filename="./wxcadm_tests.log",
                    format='%(asctime)s %(module)s:%(levelname)s:%(message)s')
# Since requests is so chatty at Debug, turn off logging propagation
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("connectionpool").setLevel(logging.WARNING)

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
skipped_tests = []

def start_test():
    logstring = f"Testing {test}..."
    print(logstring, end="")
    logging.info(logstring)

    global test_start
    test_start = time.time()

def pass_test():
    test_end = time.time()
    test_duration = round(test_end - test_start, 2)
    passed_tests.append(test)
    print(f"passed [{test_duration}s]")
    logging.info(f"{test} passed in {test_duration}s")

def fail_test():
    test_end = time.time()
    test_duration = round(test_end - test_start, 2)
    failed_tests.append(test)
    print(f"failed [{test_duration}s]")
    logging.info(f"{test} failed in {test_duration}s")

def skip_test(why: str):
    skipped_tests.append(test)
    print(f"skipped [{why}]")
    logging.info(f"{test} skipped: {why}")

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
    webex = wxcadm.Webex(access_token, get_locations=False)
except:
    fail_test()
    print("Cannot continue without valid token and Webex instance.")
    exit(1)
else:
    pass_test()

# Test with fast_mode=True to see the timing differences
test = "Webex instance - Fast Mode"
start_test()
try:
    webex_fast = wxcadm.Webex(access_token, get_locations=False, fast_mode=True)
except:
    fail_test()
    print("Cannot continue without valid token and Webex instance.")
    exit(1)
else:
    pass_test()
    del webex_fast

# Count of manageable orgs and org report
print(f"This token can access {len(webex.orgs)} Orgs")
for org in webex.orgs:
    print(f"\t{org.name}\t{org.id}\t{wxcadm.wxcadm.decode_spark_id(org.id).split('/')[-1]}")
if len(webex.orgs) > 1:
    print(f"Using {webex.orgs[0].nane} for tests.")

# Get the count of records, just for debugging purpose later
people_count = len(webex.orgs[0].people)
print(f"People Count: {people_count}")
# Location tests
test = "Get Locations"
start_test()
try:
    org_locations = webex.orgs[0].get_locations()
    locations_count = len(webex.orgs[0].locations)
    print(f"Locations Count: {locations_count}")
except:
    fail_test()
    print("Cannot get Locations. Skipping Location tests.")
else:
    pass_test()
    test = "Location Schedules get"
    start_test()
    location = webex.orgs[0].locations[0]
    try:
        sched = location.schedules
    except:
        fail_test()
    else:
        pass_test()

    test = "Location ID to User Location match"
    start_test()
    person = webex.orgs[0].get_wxc_people()[0]
    person_location = webex.orgs[0].get_location(id=person.location)
    if person_location is None:
        fail_test()
    else:
        pass_test()
    # Get Call Queues and make sure data is populated correctly
    test = "CallQueue get"
    start_test()
    try:
        call_queues = webex.orgs[0].get_call_queues()
    except:
        fail_test()
    else:
        pass_test()
        print(f"Call Queues: {len(call_queues)}")
        test = "CallQueue size check"
        start_test()
        if len(call_queues) == len(webex.orgs[0].call_queues):
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

##### Org Level Tests #####
### Webhooks ###
test = "Get Webhooks"
start_test()
try:
    webhooks = webex.orgs[0].webhooks
except:
    fail_test()
else:
    logging.debug(f"Got {len(webhooks)} Webhooks")
    pass_test()
### User Groups ###
test = 'Get UserGroups'
start_test()
try:
    usergroups = webex.org[0].usergroups
except:
    fail_test()
else:
    logging.debug(f"Got {len(usergroups) UserGroups}")
    pass_test()


# Person tests
test = "Person full config"
start_test()
person: wxcadm.wxcadm.Person = random.choice(webex.orgs[0].get_wxc_people())
try:
    full_config = person.get_full_config()
except:
    fail_test()
else:
    pass_test()
test = "Person by email"
start_test()
found_person = webex.orgs[0].get_person_by_email(person.email)
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
    ocp = person.get_outgoing_permission()
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
        success = person.push_outgoing_permission(ocp)
except:
    fail_test()
else:
    if success:
        pass_test()
    else:
        fail_test()
#### Application Services Settings ####
test = "Person Get Applications Settings"
start_test()
try:
    app_config = person.get_applications_settings()
except:
    fail_test()
else:
    pass_test()
test = "Person Set Applications Settings"
start_test()
if app_config is False or app_config is None:
    skip_test("Applications Settings not available")
else:
    try:
        success = person.push_applications_settings(app_config)
    except:
        fail_test()
    else:
        if success:
            pass_test()
        else:
            fail_test()
#### Executive Assistant Settings ####
test = "Person get Executive Assistant configs"
start_test()
try:
    ea_config = person.get_executive_assistant()
except:
    fail_test()
else:
    pass_test()
test = "Person set Executive Assistant config"
start_test()
if ea_config is False or ea_config is None:
    skip_test("Executive Assistant config not available")
else:
    try:
        success = person.push_executive_assistant(ea_config)
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
endpoints = webex.orgs[0].get_xsi_endpoints()
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
    test = "XSI Events - Service Provider"
    start_test()
    events = wxcadm.XSIEvents(webex.orgs[0])
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
    test = "XSI Events - Person"
    start_test()
    events = wxcadm.XSIEvents(webex.orgs[0])
    events_queue = queue.Queue()
    channel = events.open_channel(events_queue)
    channel.subscribe("Advanced Call", person=webex.orgs[0].get_wxc_people()[0])
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

logging.info("Tests Complete")
logging.info(f"Passed Tests: {passed_tests}")
logging.info(f"Failed Tests: {failed_tests}")
logging.info(f"Skipped Tests: {skipped_tests}")
print(f"Failed Tests: {failed_tests}")

import time
import wxcadm

#TODO Change this to get the token dynamically
access_token = "ZTgwODg2ZTYtNDY5Mi00ZDc4LWE5NjYtZTU5NmVhMGZhYzMwNjk2YWU0YjQtYWUz_PF84_3db310ec-63fa-4bc3-9438-1b5a35388b64"

passed_tests = []
failed_tests = []

def start_test():
    print(f"Testing {test}...", end="")

def pass_test():
    passed_tests.append(test)
    print("passed")

def fail_test():
    failed_tests.append(test)
    print("failed")

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

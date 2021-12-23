# wxcadm
Python Library for Webex Calling Administration

# Purpose
wxcadm is a Python 3 library to simplify the API calls to Webex in order to manage and report on users of Webex Calling

# Status
The current version in this branch is mostly complete. All the Webex Calling related functions and classes work.

There are still some enhancements being made so pulling a fresh copy will likely give you some additional capabilities.
The current focus is on the XSI API and the features that are available with that. Some of the most useful XSI methods
are already supported, with more being added regularly.

# Quickstart
By creating a Webex instance with a valid API Access Token, the module will pull the Webex Organization information as
well as all of the People within the Organization. The Org instance will contain all People, whether they have the 
Webex Calling service or not. An Org method ```get_webex_people()``` makes it easy to get only the People that have
Webex Calling.

You can obtain a 12-hour access token by logging into https://developer.webex.com and visiting the **Getting Started**
page.

Once you have the access token, the following will initialize the API connection and pull data
``` python
from wxcadm import Webex

access_token = "Your API Access Token"
webex = Webex(access_token)
```
Since most administrators only have access to a single Webex Organization, you can access that Organization with the
**org** attribute. If the administrator has access to more than one Organization, they can be accessed using the
**orgs** attribute, which is a list of the organizations that can be managed.

You can see all of the attributes with
``` python
vars(webex.org)
```
Note that, by default, all of the People are pulled when the Org is initilaized. For large organizations, this may take
a while, but then all of the People are stored as Person objects.

To iterate over the list of people, simply loop through the **people** attribute of the Org. For example:
``` python
for person in webex.org.people:
    # Print all of the attributes of the Person
    print(vars(person))
    # Or access the attributes directly
    email = person.email
```

# Documentation
Full module documentation will be coming soon. Until then, the following examples show the available methods.

```python
from wxcadm import Webex
access_token = "Your API Access Token"
webex = Webex(access_toke)

# Get all of the Locations within the org
locations = webex.org.get_locations()

# Get a list of all of the People who have Webex Calling
wxc_people = webex.org.get_wxc_people()
# Or iterate over the list directly
for person in webex.org.get_wxc_people():
    print(f"Name: {person.display_name}")
    print(f"Email: {person.email}")
```

One of the more useful methods is the ```get_person_by_email()``` method, which takes an email address and returns the
Person instance of that user. This is especially useful if processing an external list of email addresses for bulk
processing.
```python
email_list = ['user1@company.com', 'user2@company.com', 'user3@company.com']
for email in email_list:
    person = webex.org.get_person_by_email(email)
    print(person.display_name)
```
## Common XSI Use Cases
XSI can be used to accomplish a lot of things on behalf of the user. The following are examples of some commomly-used
methods provided by the wxcadm module. **Note that XSI must be enabled by Cisco before it is available to an
Organization.** Contact Cisco TAC to request that XSI be enabled.
### Place a call
``` python
from wxcadm import Webex
access_token = "your_access_token"
webex = Webex(access_token, get_xsi=True)

# Get the person that we want to place the call from
person = webex.org.get_person_by_email("user@domain.com")
# Start a XSI session for the user
person.start_xsi()
# Start a new call
call = person.xsi.new_call()
# Originate (dial) the call
call.originate("17192662837")

# Or create the new call and originate at the same time
person.xsi.new_call(address="17192662837)

# Or, for a simple click-to-dial where no further control is needed,
# you can do it all in one line:
person.start_xsi().new_call().originate("17192662837")

# When it is time to end the call, just call hangup()
call.hangup()
```
### Hold/Resume
``` python
from wxcadm import Webex
access_token = "your_access_token"
webex = Webex(access_token, get_xsi=True)

person = webex.org.get_person_by_email("user@domain.com")
person.start_xsi()
call = person.xsi.new_call()
call.originate("17192662837")

# Put the call on hold
call.hold()

# Resume the call, taking it off hold
call.resume()
```
### Blind Transfer
``` python
from wxcadm import Webex
access_token = "your_access_token"
webex = Webex(access_token, get_xsi=True)

person = webex.org.get_person_by_email("user@domain.com")
person.start_xsi()
call = person.xsi.new_call()
call.originate("17192662837")

# Invoke the transfer method, with the target extension or phone number
target_user = "2345"
call.transfer(target_user)
```
### Attended Transfer
The attended transfer puts the current call on hold and initiates a new call (origination) to the target user. Once
the users talk, a call to `finish_transfer()` will complete the transfer of the original call to the new user.
``` python
from wxcadm import Webex
access_token = "your_access_token"
webex = Webex(access_token, get_xsi=True)

person = webex.org.get_person_by_email("user@domain.com")
person.start_xsi()
call = person.xsi.new_call()
call.originate("17192662837")

# Invoke the transfer method, with the target extension or phone number
target_user = "2345"
call.transfer(target_user, type="attended")

# The original user and the target user will be connected. When ready, finish the transfer
call.finish_transfer()
```
### Attended Transfer with Conference
For a lot of cases, admins want to modify the Attended Transfer so that the transferer stays on the line with both
the caller and the tranferee, then dropping out once introductions hae been made.
``` python
from wxcadm import Webex
access_token = "your_access_token"
webex = Webex(access_token, get_xsi=True)

person = webex.org.get_person_by_email("user@domain.com")
person.start_xsi()
call = person.xsi.new_call()
call.originate("17192662837")

# Invoke the transfer method, with the target extension or phone number
target_user = "2345"
call.transfer(target_user, type="attended")

# When the transferer is ready to bring the caller on, create a conference
call.conference()

# Once the transferer is ready to leave the other parties, simply finish the transfer
call.finish_transfer()
```
## Logging
By default, the module logs to ```wxcadm.log```. At the moment, the logs just show the various methods that are invoked
for API calls to the Webex API.

## Data Structure Note
At the moment, the module works in two ways. In one way, it populates attributes based on the data from Webex. In
another, it stores the JSON representation directly from Webex. The latter is very handy for pushing data back to
Webex, but it requires some knowledge of the API structure, and doesn't abstract it well. Not to mention that the
Webex API doesn't do anything in a standard way.

The purpose of this module is to simplify that so the user doesn't have to have detailed knowledge of the Webex API, so
we are faced with a decision: keep the flexibility provided by the raw data or simplify it, at the cost of compatibility
when the Webex API is changed.

My goal is to find a happy medium, where the attributes get populated dynamically, but I feel that it is going to be a
heavy lift, changing the structure of all of the classes and building a lot of "helper" functions to convert between
the two. Stay tuned...
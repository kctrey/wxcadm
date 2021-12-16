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
## Logging
By default, the module logs to ```wxcadm.log```. At the moment, the logs just show the various methods that are invoked
for API calls to the Webex API.
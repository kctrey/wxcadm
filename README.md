# wxcadm
Python Library for Webex Calling Administration

# Purpose
wxcadm is a Python 3 library to simplify the API calls to Webex in order to manage and report on users of Webex Calling.
Although the primary focus is Webex Calling, many of the other Webex admin functions are included. This library is not
meant to be an interface to the Meetings and Messaging capabilities of Webex....there are plenty of other modules that
provide that.

# Status
The current version in this branch is mostly complete. All the Webex Calling related functions and classes work.

There are still some enhancements being made so pulling a fresh copy will likely give you some additional capabilities.
The current focus is on the XSI API and the features that are available with that. Some of the most useful XSI methods
are already supported, with more being added regularly.

# Quickstart
By creating a Webex instance with a valid API Access Token, the module will pull the Webex Organization information as
well as all the People within the Organization. The Org instance will contain all People, whether they have the 
Webex Calling service or not. An Org method ```get_webex_people()``` makes it easy to get only the People that have
Webex Calling.

You can obtain a 12-hour access token by logging into https://developer.webex.com and visiting the **Getting Started**
page.

Once you have the access token, the following will initialize the API connection and pull data
```python
from wxcadm import Webex

access_token = "Your API Access Token"
webex = Webex(access_token)
```
Since most administrators only have access to a single Webex Organization, you can access that Organization with the
**org** attribute. If the administrator has access to more than one Organization, they can be accessed using the
**orgs** attribute, which is a list of the organizations that can be managed. See the "Regarding Multiple 
Organizations" section below for further information.

You can see all the attributes with
```python
vars(webex.org)
```
Note that, by default, all the People are pulled when the Org is initialized. For large organizations, this may take
a while, but then all the People are stored as Person objects.

To iterate over the list of people, simply loop through the **people** attribute of the Org. For example:
```python
for person in webex.org.people:
    # Print all of the attributes of the Person
    print(vars(person))
    # Or access the attributes directly
    email = person.email
```
## Regarding Multiple Organizations
Most Webex admins only have access to a single Org, but Webex does allow a single admin to manage multiple Orgs. When
the Webex instance is created, it creates the `org` attribute when only one Org is present. If there are mutliple, the
`orgs` attribute contains a list of all the Orgs. `orgs` is created whether there is one Org or multiple, so `Webex.org`
is equivalent to `Webex.orgs[0]`. For example:
```python
from wxcadm import Webex

access_token = "Your API Access Token"
webex = Webex(access_token)
for org in webex.orgs:
    print(org.name)
```
It is recommended to take action on only one Org at a time, although the design allows for more flexibility. For
example, to enable VM-to-Email across all users of every Org, the following is supported:
```python
for org in webex.orgs:
    for person in org.people:
        person.enable_vm_to_email()
```
The `get_org_by_name()` method is provided to allow the selection of the desired org by name.
```python
my_org = webex.get_org_by_name("My Company")
for people in my_org.people:
    person.enable_vm_to_email()
```
# Documentation
**wxcadm** documentation is housed at [Read The Docs](https://wxcadm.readthedocs.io/en/latest/). 

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
heavy lift, changing the structure of all the classes and building a lot of "helper" functions to convert between
the two. Stay tuned... 
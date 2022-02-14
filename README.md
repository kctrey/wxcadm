# wxcadm
Python Library for Webex Calling Administration

# Purpose
wxcadm is a Python 3 library to simplify the API calls to Webex in order to manage and report on users of Webex Calling.
Although the primary focus is Webex Calling, many of the other Webex admin functions are included. This library is not
meant to be an interface to the Meetings and Messaging capabilities of Webex....there are plenty of other modules that
provide that.

# Installation
**wxcadm** is available as a [PIP Package](https://pypi.org/project/wxcadm/)

```
$ python -m pip install wxcadm
```
# Quickstart
By creating a Webex instance with a valid API Access Token, the module will pull the Webex Organization information as
well as all the People within the Organization. The Org instance will contain all People, whether they have the 
Webex Calling service or not. An Org method ```get_webex_people()``` makes it easy to get only the People that have
Webex Calling.

You can obtain a 12-hour access token by logging into https://developer.webex.com and visiting the **Getting Started**
page.

Once you have the access token, the following will initialize the API connection and pull data

```python
import wxcadm

access_token = "Your API Access Token"
webex = wxcadm.Webex(access_token)
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
# Documentation
**wxcadm** documentation is housed at [Read The Docs](https://wxcadm.readthedocs.io/en/latest/). 

.. wxcadm documentation master file, created by
   sphinx-quickstart on Thu Jan 13 13:49:27 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

====================
wxcadm Documentation
====================
Welcome to the documentation home of **wxcadm**, a Python 3 library to simplify the API calls to Webex in order to
manage and report on users of Webex Calling.

Although the primary focus is Webex Calling, many of the other Webex admin functions are included. This library is not
meant to be an interface to the Meetings and Messaging capabilities of Webex....there are plenty of other modules that
provide that.

Status
======
The current version in this branch is mostly complete. All the Webex Calling related functions and classes work.

There are still some enhancements being made so pulling a fresh copy will likely give you some additional capabilities.
The current focus is on the XSI API and the features that are available with that. Some of the most useful XSI methods
are already supported, with more being added regularly.

.. include:: usage/quickstart.rst

Regarding Multiple Organizations
================================
Most Webex admins only have access to a single Org, but Webex does allow a single admin to manage multiple Orgs. When
the Webex instance is created, it creates the ``org`` attribute when only one Org is present. If there are mutliple, the
``orgs`` attribute contains a list of all the Orgs. ``orgs`` is created whether there is one Org or multiple, so
``Webex.org`` is equivalent to ``Webex.orgs[0]``. For example:

.. code-block:: python

   from wxcadm import Webex

   access_token = "Your API Access Token"
   webex = Webex(access_token)
   for org in webex.orgs:
       print(org.name)

It is recommended to take action on only one Org at a time, although the design allows for more flexibility. For
example, to enable VM-to-Email across all users of every Org, the following is supported:

.. code-block:: python

   for org in webex.orgs:
       for person in org.people:
           person.enable_vm_to_email()


The ``get_org_by_name()`` method is provided to allow the selection of the desired org by name.

.. code-block:: python

   my_org = webex.get_org_by_name("My Company")
   for people in my_org.people:
       person.enable_vm_to_email()

Documentation
=============
Full module documentation can be found here: :doc:`reference/wxcadm`

The following examples show many of the common use cases supported by **wxcadm**:

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token)

   # Get all of the Locations within the org
   locations = webex.org.get_locations()

   # Get a list of all of the People who have Webex Calling
   wxc_people = webex.org.get_wxc_people()
   # Or iterate over the list directly
   for person in webex.org.get_wxc_people():
       print(f"Name: {person.display_name}")
       print(f"Email: {person.email}")

One of the more useful methods is the ``get_person_by_email()`` method, which takes an email address and returns the
Person instance of that user. This is especially useful if processing an external list of email addresses for bulk
processing.

.. code-block:: python

   email_list = ['user1@company.com', 'user2@company.com', 'user3@company.com']
   for email in email_list:
       person = webex.org.get_person_by_email(email)
       print(person.display_name)

Common Webex Use Cases
----------------------
These are some commonly-requested changes that most Webex Calling admins have to deal with.

Organization and Location Numbers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In order to create users, or sometimes to report on them, it is useful to pull the numbers associated with an
Org. The ``Org.numbers`` attribute provides a list of numbers, along with the Location each is assigned to. If a
number is assigned to a Person, then the person instance will be included.

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token)
   for number in webex.org.numbers:
      if "owner" in number:
         # The number is assigned
         print(f"{number['number']} is assigned to {number['owner'].email}")
      else:
         # The number is not assigned
         print(f"{number['number']} is not assigned")

Enable VM-to-Email
^^^^^^^^^^^^^^^^^^
By default, the sending of VM as an email attachment is disabled, but most enterprises want this feature. The following
will step through all the Webex Calling users within the Organization and make that change.

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token)
   # Iterate over all of the People who have a Webex Calling license
   for person in webex.org.get_wxc_people():
       # By leaving the email param out of the function call, the function will just use their Webex email
       person.enable_vm_to_email()

Change the user's phone number
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token)
   # Find the Person that you want to change
   person = webex.org.get_person_by_email("user@domain.com")
   # Call the `change_phone_number()` method for the user
   success = person.change_phone_number(new_number="8185551234", new_extension="1234")
   # The Person instance will reflect the change
   if success:
       print(person.numbers)

Get the Hunt Groups and Call Queues the user is an Agent for
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``hunt_groups`` and ``call_queues`` attributes hold all of the instances of each that the user is assigned to as an
"agent". Of course, this would be more useful if there were methods for those Classes, but that's coming soon. For now,
it makes it easy to find all of the places the user is being used.

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token)
   # Find the person you want the details for
   person = webex.org.get_person_by_email("user@domain.com")
   for hunt_group in person.hunt_groups:
       hg_name = hunt_group.name
       # And anything else you want to do
   for call_queue in person.call_queues:
       cq_name = call_queue.name
       # etc...

Workspaces
^^^^^^^^^^
The Webex Calling functionality that is exposed to Workspaces is limited. At this time, the Workspaces and their
associated Workspace Locations can be obtained with the ``get_workspaces()`` method of the Org instance. This will
populate the ``Org.workspaces`` and ``Org.workspace_locations`` attributes, which contain the information. As the API is
enhanced to provide capabilities, new methods will be added to **wxcadm**.

Common XSI Use Cases
--------------------
XSI can be used to accomplish a lot of things on behalf of the user. The following are examples of some commonly-used
methods provided by the wxcadm module. **Note that XSI must be enabled by Cisco before it is available to an
Organization.** Contact Cisco TAC to request that XSI be enabled.

Get the user's profile (phone number)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The XSI Profile is retrieved directly from the Call Control back-end, so it represents the actual user profile, rather
than the Common Identity profile present in the ``Org.people`` attribute. A common use is to get the Webex Calling phone
number for the user rather than what is received from Active Directory.

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token, get_xsi=True)

   # Get the person that we want to get the profile for
   person = webex.org.get_person_by_email("user@domain.com")
   person.start_xsi()      # Starts an XSI session for the Person and creates the XSI instance in Person.xsi
   print(person.xsi.profile)
   # Get the phone number for the person
   country_code = person.xsi.profile['country_code']
   phone_number = person.xsi.profile['number']
   e164_number = f"+{country_code}{phone_number}"

Place a call
^^^^^^^^^^^^
.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
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

Hold/Resume
^^^^^^^^^^^
.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token, get_xsi=True)

   person = webex.org.get_person_by_email("user@domain.com")
   person.start_xsi()
   call = person.xsi.new_call()
   call.originate("17192662837")

   # Put the call on hold
   call.hold()

   # Resume the call, taking it off hold
   call.resume()

Blind Transfer
^^^^^^^^^^^^^^
.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
   webex = Webex(access_token, get_xsi=True)

   person = webex.org.get_person_by_email("user@domain.com")
   person.start_xsi()
   call = person.xsi.new_call()
   call.originate("17192662837")

   # Invoke the transfer method, with the target extension or phone number
   target_user = "2345"
   call.transfer(target_user)

Attended Transfer
^^^^^^^^^^^^^^^^^
The attended transfer puts the current call on hold and initiates a new call (origination) to the target user. Once
the users talk, a call to ``finish_transfer()`` will complete the transfer of the original call to the new user.

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
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

Attended Transfer with Conference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
For a lot of cases, admins want to modify the Attended Transfer so that the transferer stays on the line with both
the caller and the transferee, then dropping out once introductions hae been made.

.. code-block:: python

   from wxcadm import Webex
   access_token = "Your API Access Token"
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

Logging
=======
By default, the module logs to ``wxcadm.log``. At the moment, the logs just show the various methods that are invoked
for API calls to the Webex API.

Data Structure Note
===================
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

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage/installation
   usage/quickstart
   reference/wxcadm


Indexes and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

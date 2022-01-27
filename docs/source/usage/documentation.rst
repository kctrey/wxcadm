Usage Reference
===============
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

Assign Webex Calling to an Existing User
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In order to assign Webex Calling, you must know the Location instance and provide either the phone number, the
extension, or both.

.. code-block:: python

    from wxcadm import Webex

    access_token = "Your API Access Token"
    user = "user@domain.com"
    location_name = "Location Name"
    phone_number = "+18185552345"

    webex = Webex(access_token, fast_mode=True)

    user_location = webex.org.get_location_by_name(location_name)
    person = webex.org.get_person_by_email(user)
    if person is None:
        print(f"Could not find user {user}")
    else:
        success = person.assign_wxc(location=user_location, phone_number=phone_number)
        if success:
            print("Succeeded")
        else:
            print("Failed")

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


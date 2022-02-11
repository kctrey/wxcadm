XSI Usage
=========
XSI is an additional set of APIs provided by Webex, specifically related to Webex Calling. The XSI APIs allow an
integration to access and control the Call Control platform directly. Some things than can be done with the XSI APIs
include:

* Embedding a Webex Calling interface into your own Web apps or desktop software
    * Click-to-dial within your app
    * Real-time notification of call events
        * Call Logging
        * Popup call notifications with custom data from your CRM
    * Management of in-progress calls
        * Conference call management
        * Call Transfer
        * Hold/Resume/Park
* Monitor user services and calls in real-time
    * Advanced CDR generation, tied to business data
    * Compliance audit

Getting Started with XSI
------------------------
In order to use the XSI APIs, they must be activated on the Webex Organization. Contact Cisco TAC to request that XSI
be enabled for your Webex Org.

In order for the **wxcadm** module to interface with XSI, the Org instance must know about the XSI endpoints, which
are unique to each Org. You can trigger the Org instance to determine these endpoints when the Webex instance is
created by passing the ``get_xsi=True`` argument to the Webex class.

.. code-block:: python

    import wxcadm

    access_token = "Your API Access Token"
    webex = wxcadm.Webex(access_token, get_xsi=True)

Or you can call the ``get_xsi_endpoints()`` method on the Org instance

.. code-block:: python

    import wxcadm

    access_token = "Your API Access Token"
    webex = wxcadm.Webex(access_token)
    webex.org.get_xsi_endpoints()

Once the XSI endpoints are known by the Org instance, an XSI instance needs to be started for each Person, which sets
all of the appropriate HTTP headers and URLs for the Person. An XSI session is created with the ``start_xsi()`` method
of the Person instance.

.. code-block:: python

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

   # Get the person that we want to use XSI with
   person = webex.org.get_person_by_email("user@domain.com")
   person.start_xsi()      # Starts an XSI session for the Person and creates the XSI instance in Person.xsi

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

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

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

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

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

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

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

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

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

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

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

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token, get_xsi=True)

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

Executive/Assistant Call Handling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When users are working in an Executive and Executive Assistant configuration, XSI supports a number of methods focused
on the call flows that are unique to that configuration.

To place a call from an Assistant on behalf of the Executive, the :meth:`originate()` method supports an optional
``executive`` argument, which is set to the phone number or extension of the Executive. If the Assistant is associated
with the Executive, the call will be placed on behalf of them.

.. code-block:: python

    import wxcadm
    access_token = "Your API Access Token"
    webex = wxcadm.Webex(access_token, get_xsi=True)

    # Initiate an XSI session for the Assistant
    assistant = webex.org.get_person_by_email("assistant@company.com")
    assistant.start_xsi()
    call = assistant.new_call()
    # Call the originate() method with the optional executive param
    # For this example, we will hard-code the Executive extension as "1234" but any of the Person attributes
    #   related to phone numbers or extensions could be used to determine the Executive's number
    call.originate("7192662837", executive="1234")

    # The call will be placed and the Assistant will be on the call with the Called Address
    # If the Assistant wants to "push" the call to the Executive, ringing their devices and allowing them to pick up
    #   the call, the exec_push() method can be used
    call.exec_push()

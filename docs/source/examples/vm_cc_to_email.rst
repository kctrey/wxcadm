Voicemail - Enable Copy-to-Email
================================
By default, the sending of VM as an email attachment is disabled, but most enterprises want this feature. The following
will step through all the Webex Calling users within the Organization and make that change.

.. code-block:: python

   import wxcadm

   access_token = "Your API Access Token"
   webex = wxcadm.Webex(access_token)

   # Iterate over all of the People who have a Webex Calling license
   for person in webex.org.get_wxc_people():
       # By leaving the email param out of the function call, the function will just use their Webex email
       person.enable_vm_to_email()

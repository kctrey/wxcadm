Voicemail - PIN Reset
=====================
This script will modify a list of users, identified by their email address, to reset their Voicemail PIN to the default
that is set at the Organization level. Note that this example assumes that the default PIn has been set directly in
Control Hub or has been set using another method. This script could be altered to generate a random PIN for each user
as it is ran.

.. code-block:: python

    import wxcadm

    access_token = "Your API Access Token"
    user_list = ['user1@domains.com',
                 'user2@domain.com',
                 'user3@domain.com']

    webex = wxcadm.Webex(access_token)

    for user in user_list:
        person = webex.org.get_person_by_email(user)
        if person is None:
            print(f"User {user} was not found.")
            continue
        person.reset_vm_pin()

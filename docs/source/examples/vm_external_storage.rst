Voicemail - External Storage
============================
Webex Calling allows users to be set up so that the Webex voicemail functions but messages are not stored in the
user's mailbox and are instead sent directly to an email address.

The script below will loop through all Webex Calling users within an Org and change their voicemail configuration to
utilize this functionality, using their Webex email as the email to send the voice messages to.

.. code-block:: python

    from wxcadm import Webex
    access_token = "Your API Access Token"

    webex = Webex(access_token)

    for person in webex.org.get_wxc_people():
        logging.info(f"Changing user: {person.email}")
        person.get_vm_config()
        person.vm_config['messageStorage']['storageType'] = "EXTERNAL"
        person.vm_config['messageStorage']['externalEmail'] = person.email
        person.push_vm_config()
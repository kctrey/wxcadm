# vm_external_storage.py
#
# This script is used to set **all Webex Calling users** to extenal VM storage with their Webex email
# as the email to send all VMs to. This is different than the "CC to email" feature which leaves a copy
# of the VM on the mailbox.

import sys
sys.path.append('../')
from wxcadm.wxcadm import Webex

access_token = "Your API Access Token"

webex = Webex(access_token, fast_mode=True)

for person in webex.org.get_wxc_people():
    logging.info(f"Changing user: {person.email}")
    person.get_vm_config()
    person.vm_config['messageStorage']['storageType'] = "EXTERNAL"
    person.vm_config['messageStorage']['externalEmail'] = person.email
    person.push_vm_config()

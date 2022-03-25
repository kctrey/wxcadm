What's New
==========

v2.1.0
------
- The :class:`wxcadm.XSICallQueue` class was added for control of Call Queue calls
- New method :meth:`wxcadm.Webex.get_person_by_email()` which does what the Org-level method does, but searches across all Orgs that the user can manage.
- Failed "pushes" to Webex for user data no longer raise an exception. They now return False to prevent blocking in scripts.
- :meth:`wxcadm.Person.push_vm_config()` now supports a vm_config dict rather than modifying the :attr:`Person.vm_config` attribute directly.
- Added :meth:`wxcadm.XSI.attach_call()` to allow known Call IDs to be attached to a Person's XSI instance for call control.

v2.0.0
------
-  XSI-Events are now supported!
-  A new :meth:`wxcadm.Person.XSI.answer()` method has been added, which is very useful now that you can see XSI Events for incoming calls
-  Better handling of Token Errors
-  :meth:`wxcadm.Person.set_caller_id()` method
-  Bot-friendly method changes
- :meth:`wxcadm.Person.set_voicemail_rings()` method
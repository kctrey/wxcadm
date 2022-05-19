What's New
==========

v2.2.1
------
- Bug Fix: Removed print() statements from RedSky class
- **Breaking Change** - :meth:`Org.get_auto_attendants()` has been changed to a property :meth:`Org.auto_attednants` to match other classes.
- :meth:`wxcadm.AutoAttendant.upload_greeting()` added to support uploading custom WAV files for Auto Attendants. Note that this requires an Access Token capable of utilizing the CP-API.
- :meth:`wxcadm.XSIEventsChannelSet.subscribe()` now allows a Person target for subscriptions
- Improved :meth:`wxcadm.Org.number` to handle HuntGroup, PagingGroup, and CallQueue owners
- Added support for Paging Groups with :meth:`wxcadm.Org.paging_groups`

v2.2.0
------
- Changed logging to ensure that we only log when enabled by the application
- :meth:`wxcadm.Org.get_location()` was added to search for Location by various keys
- :meth:`wxcadm.Org.get_audit_events()` was added to support auditing of Control Hub changes

v2.1.1
------
- :meth:`wxcadm.Org.numbers` now uses the Webex for Developers API rather than CP-API

v2.1.0
------
- The :class:`wxcadm.XSICallQueue` class was added for control of Call Queue calls
- New method :meth:`wxcadm.Webex.get_person_by_email()` which does what the Org-level method does, but searches across all Orgs that the user can manage.
- Failed "pushes" to Webex for user data no longer raise an exception. They now return False to prevent blocking in scripts.
- :meth:`wxcadm.Person.push_vm_config()` now supports a vm_config dict rather than modifying the :attr:`Person.vm_config` attribute directly.
- Added :meth:`wxcadm.XSI.attach_call()` to allow known Call IDs to be attached to a Person's XSI instance for call control.
- LocationSchedule class and new Location ```schedules``` attribute

v2.0.0
------
-  XSI-Events are now supported!
-  A new :meth:`wxcadm.Person.XSI.answer()` method has been added, which is very useful now that you can see XSI Events for incoming calls
-  Better handling of Token Errors
-  :meth:`wxcadm.Person.set_caller_id()` method
-  Bot-friendly method changes
- :meth:`wxcadm.Person.set_voicemail_rings()` method
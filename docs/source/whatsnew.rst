.. currentmodule:: wxcadm.wxcadm

What's New
==========
v2.3.4
------
- Added debug logging to :py:class:`XSIEventsChannel` to help diagnose heartbeat problems
- :py:meth:`
- BUG FIX: :py:meth:`Org.get_locations()` no longer creates a duplicate of all locations

v2.3.3
------
- Added :py:meth:`Org.delete_person()` to support deleting a user
- BUG FIX: :py:meth:`Location.available_numbers` now returns only unassigned numbers
- :py:meth:`Org.create_person()` now accepts either a :py:class:`Location` instance or the Location ID string for the ``location`` param

v2.3.2
------
- BUG FIX: :py:meth:`XSIEventsChannel.heartbeat_daemon()` now handles uncaught requests exceptions
- Added :py:meth:`Person.role_names()` to return role names for a user, rather than Role IDs
- Added :py:meth:`Org.roles` for full names of Role IDs

v2.3.0
------
- Added :py:class:`UserGroups` and :py:class:`UserGroup` to handle User Group management
- BUG FIX: **wxcadm** no longer gets Webex licenses on Org initialization.
- In addition to the item below, the defaults for Org creation have been changed so that data is not retrieved automatically *unless there is only one org*.
- To handle admins who manage a large number of Orgs, the ``get_location_data`` args has been added to the :py:class:`Webex` class initialization args. This prevents **wxcadm** from making dozens of potentially unnecessary API calls and speed processing time.
- Added Voice Message methods to the :py:class:`Me` class
- :meth:`Webex.me` returns a :py:class:`Me` instance, which is a child of the Person instance, which has some unique methods.
- :meth:`Webex.get_person_by_id` to search across Orgs
- :meth:`Person.upload_busy_greeting()` and :meth:`Person.upload_no_answer_greeting()` for VM greeting uploads
- New :meth:`wxcadm.console_logging()` added to support STDOUT logging for interactive development
- Lots of logging and method clean-up. Standardized getters as "get_xxxx()" and setters (which call the Webex API PUT) as "push_xxxx(config)"
- :meth:`Org.recorded_people` property to return all users with Call Recording enabled
- :meth:`Org.get_wxc_people()` deprecated in favor of :meth:`Org.wxc_people` property
- Person recording config can be pushed with :meth:`Person.push_call_recording()`

v2.2.1
------
- Bug Fix: Removed print() statements from RedSky class
- **Breaking Change** - :meth:`Org.get_auto_attendants()` has been changed to a property :meth:`Org.auto_attednants` to match other classes.
- :meth:`AutoAttendant.upload_greeting()` added to support uploading custom WAV files for Auto Attendants. Note that this requires an Access Token capable of utilizing the CP-API.
- :meth:`XSIEventsChannelSet.subscribe()` now allows a Person target for subscriptions
- Improved :meth:`Org.number` to handle HuntGroup, PagingGroup, and CallQueue owners
- Added support for Paging Groups with :meth:`Org.paging_groups`

v2.2.0
------
- Changed logging to ensure that we only log when enabled by the application
- :meth:`Org.get_location()` was added to search for Location by various keys
- :meth:`Org.get_audit_events()` was added to support auditing of Control Hub changes

v2.1.1
------
- :meth:`Org.numbers` now uses the Webex for Developers API rather than CP-API

v2.1.0
------
- The :class:`XSICallQueue` class was added for control of Call Queue calls
- New method :meth:`Webex.get_person_by_email()` which does what the Org-level method does, but searches across all Orgs that the user can manage.
- Failed "pushes" to Webex for user data no longer raise an exception. They now return False to prevent blocking in scripts.
- :meth:`Person.push_vm_config()` now supports a vm_config dict rather than modifying the :attr:`Person.vm_config` attribute directly.
- Added :meth:`wxcadm.XSI.attach_call()` to allow known Call IDs to be attached to a Person's XSI instance for call control.
- LocationSchedule class and new Location ```schedules``` attribute

v2.0.0
------
-  XSI-Events are now supported!
-  A new :meth:`Person.XSI.answer()` method has been added, which is very useful now that you can see XSI Events for incoming calls
-  Better handling of Token Errors
-  :meth:`Person.set_caller_id()` method
-  Bot-friendly method changes
- :meth:`Person.set_voicemail_rings()` method
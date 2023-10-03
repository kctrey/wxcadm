.. currentmodule:: wxcadm.wxcadm

What's New
==========

.. note::

    v4.0.0 is a significant rewrite of a lot of the methods and API calls to reduce the number of API calls needed in large Orgs with a lot of Users/Locations/Workspaces. I have tried to document all the breaking changes, but there may be some I haven't realized yet. The v4.0.0 series is changing rapidly as I find them.

v4.0.0
------
- New method :meth:`WorkspaceList.create()` to allow Workspace creation with Webex Calling capability
- :class:`Location` and :class:`Org` now both have an :attr:`org_id` property since it is needed often by the API and some things can exist at the Org or Location level
- :class:`ComplianceAnnouncementSettings` at the :class:`Org` and :class:`Location` level for the new Recording Compliance Announcement
- :class:`NumberManagementJob` with List Class :class:`NumberManagementJobList` accessible via :attr:`Org.number_management_jobs`. These classes deal with the ability to move (and eventually delete) numbers.
- Ensured that all HTTPS sessions/requests are closed prior to returning the value to the caller.
- :meth:`Location.enable_webex_calling()` added.
- A placeholder method :meth:`Location.delete()` was added even though it doesn't work. Users were looking for it, so I added it to ensure the docs are correct and users know they need to use Control Hub.
- **BREAKING CHANGE** - :meth:`LocationList.create()` no longer requires an ``announcement_language`` argument since it isn't used on Webex anyway.
- Started building real unit and integration tests in the tests directory. This effort will be ongoing, but it's time to start making testing a little more effective.
- Deprecated :meth:`Org.get_hunt_group_by_id()`. Use :meth:`Org.hunt_groups.get(id=)` instead.
- New List Class :class:`HuntGroupList` accessed with :attr:`Org.hunt_groups` and :attr:`Location.hunt_groups`
- Deprecated :meth:`Org.get_call_queue_by_id()`. Use :meth:`Org.call_queues.get(id=)` instead.
- New List Class :class:`CallQueueList` accessed with :attr:`Org.call_queues` and :attr:`Location.call_queues`
- :meth:`wxcadm.console_logging()` now supports ``"none"`` as a ``level`` argument to turn off STDOUT logging
- Deprecated :py:meth:`Org.create_person()`. Use :py:meth:`Org.people.create()` instead.
- :py:meth:`Webex.get_org_by_name()` is now case-insensitive. Partial matches are also still supported.
- :py:meth:`Webex.get_org_by_id()` now supports UUID Org IDs as well as Webex API IDs
- :py:meth:`Webex.get_person_by_email()` and :py:meth:`Webex.get_person_by_id()` have been optimized to work much faster for tokens with access to many Orgs.
- :py:meth:`LocationList.webex_calling()` filters Locations by whether or not Webex Calling is enabled.
- **BREAKING CHANGE** - :py:meth:`Org.get_location_by_name()` has been deprecated for a while, but a lot of people still used it, including me. The recommended :py:meth:`Org.get_location()` has been moved to :py:meth:`Org.locations.get()` (:py:meth:`LocationList.get()`) and should be used instead.
- New :py:class:`LocationList` class access with :py:meth:`Org.locations`. All list functions have been moved to this class.
- Deprecated :py:meth:`Org.get_auto_attendants()`. Use :py:meth:`Org.auto_attendants` instead.
- The ``location_features.py`` file was getting hard to manage, so some features (Call Queue, Hunt Group, Auto Attendant) have been split to their own files. This will probably the standard moving forward.
- With Unified Locations, it is now necessary to check every Location to ensure Calling is enabled before performing any Calling APIs. All of this is handled within the :py:class:`Location` class internally.
- Deprecated :py:meth:`Org.get_recorded_people()`. Use :py:meth:`Org.people.recorded()` instead.
- Deprecated :py:meth:`Org.get_wxc_people()`. Use :py:meth:`Org.people.webex_calling()` instead.
- Deprecated :py:meth:`Org.get_person_by_email()`. Use :py:meth:`Org.people.get_by_email()` instead.
- Deprecated :py:meth:`Org.get_person_by_id()`. Use :py:meth:`Org.people.get_by_id()` instead.
- **BREAKING CHANGE** - With the creation of :py:class:`PersonList`, the ``people`` and ``people_list`` arguments to the :py:class:`Webex` class have been deprecated. **wxcadm** will never pre-fetch Person-related data from Webex.
- New List Class :py:class:`PersonList` accessed with :py:attr:`Org.people` and :py:attr:`Location.people`
- This version stars the refactor change to a new "List Class" for all lists, starting with WorkspaceLocationList and WorkspaceList. All create/delete methods will be moved to the list class to make it easier to manage elements in a list. Changelog entries going forward will refer to these as List Classes.
- The Org class now has a :py:attr:`workspace_locations` attribute, which is a :py:class:`WorkspaceLocationList`
- :py:meth:`Org.get_workspace_by_id()` has been moved to :py:meth:`Org.workspaces.get_by_id()`
- New :py:class:`WorkspaceList` to provide list functions for :py:meth:`Org.workspaces` and :py:meth:`Location.workspaces`, which both use the new class
- BUG FIX: :py:meth:`Call.recording()` was broken and has been fixed.
- Removed :py:meth:`AutoAttendant.upload_greeting()` now that the Announcement Repository is in place
- Lots of performance improvements to ensure API calls only happen when needed by the caller. Too much data was being populated in advance even though it was never used.
- Refactor Org and Location hunt_groups property to eliminate the need for :py:meth:`Org.get_hunt_groups()`.
- Now that Webex creates UserGroups for all Locations, the :py:class:`UserGroups` doesn't fetch group members on init. This speeds things up and reduces API calls.
- **BREAKING CHANGE** :py:meth:`Person.usergroup` has been removed and replaced with :py:meth:`Person.user_group()`
- Added :py:meth:`Location.create_call_queue()`
- Added methods to :py:class:`RedSky` and :py:class:`RedSkyLocation` to make Network Discovery easier to find and manage
- Added :py:meth:`RedSky.delete_mac_discovery()`, :py:meth:`RedSky.delete_bssid_discovery()`
- Added ``bssid`` argument to :py:meth:`RedSky.get_bssid_discovery`` to allow a single entry to be returned

v3.4.0
------
- Added :py:meth:`RedSky.delete_lldp_chassis()` to remove LLDP mapping
- Changed :py:meth:`Org.locations` to not require :py:meth:`Org.get_locations()` first, so that it behaves like the newer classes. Added new :py:meth:`Org.refresh_locations()` method, which can be used to pull updated Location data.
- Announcement Repository now supported across :py:class:`Org` and :py:class:`Location`. New :py:class:`Announcement` class.
- BUG FIX: :py:meth:`Org.get_call_queue_by_id()` fixed
- Added :py:meth:`Location.auto_attendants` to make finding AAs by Location easier
- BUG FIX: Fixed :py:meth:`Org.create_location()` which had an incorrect API endpoint
- Refactor to remove CSDM requirement for device work now that it is supported in Webex API
- Added :py:meth:`Org.get_workspace_by_id()`
- Added :py:meth:`Person.add_device()` to allow devices to be created for people
- Added :py:meth:`Workspace.add_device()` to allow devices to be created for Workspaces
- Added :py:meth:`Device.delete()` to delete a device
- Added a number of new attributes to :py:class:`Device` that are now provided by Webex
- Added :py:meth:`Org.get_supported_devices()` to provide a list of supported devices now that they can be added
- Changed :py:meth:`Org.get_devices()` and :py:meth:`Org.get_device_by_id()` to deal with mismatched IDs for the same device, but with the same UUID

v3.3.0
------
- **wxcadm** now supports an integration with the Meraki Dashboard with the goal of being able to use Meraki Dashboard data to populate the RedSky Network Discovery.

v3.2.0
------
- Added :py:meth:`Org.get_workspace_devices()` to return Webex Calling Workspaces with their devices, or an empty device list if there are no devices
- Added :py:meth:`Person.enable_vm_notification()` and :py:meth:`Person.disable_vm_notification()` as suggested by @vaijanaths007
- With the release of the Devices API, the :py:class:`Device` class no longer requires CSDM access and can be used with any Integration token
- Complete rewrite of the :class:`Device` class to handle only what is supported by the developer API. More enhancements will come in 3.2.x

v3.1.0
------
- XSI now offers a :py:meth:`directory()` method to search Enterprise, Group and Personal directories.
- PERFORMANCE: **wxcadm** previously retrieved too much data when Orgs and Locations were initialized. The API calls have been moved so they are only performed when the relevant data is needed.
- PERFORMANCE: :py:meth:`Location.numbers` and :py:meth:`Location.available_numbers` now don't pull all numbers for the Org, only the Location
- **wxcadm** now supports Wholesale partners with the :py:class:`WholesaleCustomer` and :py:class:`WholesaleSubscriber` classes
- :py:meth:`Location.set_announcement_language()` added to update Announcement Language for Locations, Users and Features
- BUG FIX: Fixed exception when XSI.profile is called and no profile is returned
- XSI calls, either :py:meth:`new_call()` or :py:meth:`originate()` now accept a ``phone`` argument to specify which phone is to be used to make the call.
- Added support for the real-time CDR API in the :py:class:`Calls` class using the :py:meth:`cdr()` method
- BUG FIX: LocationSchedule.add_holiday() fixed
- The behavior of :py:meth:`Webex.org` has changed. Previously, the ``org`` attribute was only available if the token could only access one Webex Org. Now, ``org`` is always available and will be the first Org in the :py:meth:`Webex.orgs` list, which is the Primary Org for the user.

v3.0.4
------
- BUG FIX: Rejected XSIEventsSubscription is now handled and reported
- BUG FIX: XSIEventsChannel now handles non-OK responses on channel creation
- Finalized :py:meth:`XSI.Call.conference()` to allow a conference to be immediately started from an active call
- BUG FIX: XSI call status fixed for calls that weren't in an answered state

v3.0.3
------
- Added :py:meth:`Device.change_tags()`
- Added :py:meth:`Webex.get_new_token()` method to use the Refresh Token to obtain a new token.
- **wxcadm** now supports Service Applications
- BUG FIX: :py:meth:`XSI.get_fac()` no longer requires the profile to be retrieved first
- Added :py:meth:`Reports.cdr_report()` to make creating a CDR report easier
- Converted :py:meth:`Org.wxc_licenses` to a property to ensure it can be retrieved at any time
- Various optimizations for tokens with access to more than one Org to reduce pre-fetching but not require any special logic
- BUG FIX: Webex.me now works correctly if the token has access to more than one Org
- Added :py:meth:`Org.get_audit_events()` to retrieve Admin Audit Events for an Org

v3.0.2
------
- Added the :py:class:`Reports` class to manage reports
- New :py:meth:`Person.wxc_numbers` to get numbers, including Alias numbers, from Webex Calling instead of CI

v3.0.0
------
- **BREAKING CHANGE:** - XSI Actions for Calls now return a :py:class:`XSIResponse` instead of a boolean indicator of success. This allows flexibility to determine why the XSI API call failed and whether it should be retried.
- The :py:meth:`wxcadm.webex_api_call()` method, which is used by all of the API calls, now supports retry when a 429 is received from Webex. The default retry count is 3.
- Locations now support :py:meth:`outgoing_call_permissions` property and :py:meth:`set_outgoing_call_permissions()` method
- The :py:class:`CallRouting` class and :py:meth:`Org.call_routing` property have been added to support the Trunking, Route Groups, and Dial Plan
- Massive code refactor. **wxcadm** has grown too large to be a single Python file. Debugging and linting was getting overwhelming. v3.0.0 introduces a new package layout that will simplify a lot of things.
- Added the ability to pass a :py:class:`logging.Formatter` to the :py:meth:`wxcadm.console_logging()` method for those who use STDOUT logging and want control of the format.

v2.3.5
------
- Added the :py:class:`Call` class to the package root to allow ``wxcadm.Call()``

v2.3.4
------
- Many changes to XSIEvents and the classes associated with it. XSIEvents should now be much more stable.
- Added debug logging to :py:class:`XSIEventsChannel` to help diagnose heartbeat problems
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
- **Breaking Change** - :meth:`Org.get_auto_attendants()` has been changed to a property :meth:`Org.auto_attendants` to match other classes.
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
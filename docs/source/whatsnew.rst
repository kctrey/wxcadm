.. currentmodule:: wxcadm

What's New
==========

v4.5.1
------
- BUG FIX: :meth:`Person.assign_wxc()` now doesn't error when trying to unassign UCM as part of the WxC assignment
- BUG FIX: :meth:`DeviceMemberList.add() <.device.DeviceMemberList.add()>` now sends the T.38 indicator for ATA devices
- Recordings can now be reassigned in bulk using :meth:`RecordingList.reassign_owner() <.recording.RecordingList.reassign_owner()>`
- Devices has been revamped to handle PhoneOS devices as well as prepare the code for upcoming changes to /v1/devices
   - :class:`~.device.DeviceList` now always uses `/v1/devices` regardless of whether the data is being requested at the Org, Location, Person or Workspace level
   - :class:`~.device.Device` now has a :attr:`~.device.Device.calling_id` property, which is the Webex Calling ID used for all of the `/v1/telephony` API endpoints
   - One behavior that changes in this design is that a the :attr:`Person.devices <.person.Person.devices>` now only returns devices that are owned by the user.
   - A new property :attr:`Person.appearance_devices <.person.Person.appearance_devices>` has been added to find all the devices the user has a line appearance on
- :class:`~.virtual_line.VirtualLine` now has an :attr:`~.virtual_line.VirtualLine.name` attribute

v4.5.0
------
- The inclusion of the `meraki` module as a dependency doesn't make sense for 99% of **wxcadm** users, so I have moved it to an optional dependency. See :ref:`Using Meraki for RedSky Network Discovery`
- :class:`~.call_routing.RouteLists` now supports :meth:`~.call_routing.RouteLists.create()` to create new Route Lists
- All references and properties that were associated with a :class:`WorkspaceLocation` have been removed. All Webex Calling uses Location now and WorkspaceLocation has been deprecated.
- :class:`~.device.DeviceMember` now includes `esn`, `routing_prefix` and `location_id` properties.
- **BREAKING CHANGE** - :meth:`Org.wxc_people()`, which was deprecated in v4.0.0 has been removed
- **BREAKING CHANGE** - The `Org.get_location_by_name()` which was deprecated back in v2.2 has finally been removed
- New :meth:`~.person.Person.delete()` to allow deletion of users
- New :meth:`~.workspace.Workspace.unassign_wxc()` to support removing the Webex Calling license for RoomOS Workspaces
- :meth:`~.workspace.Workspace.assign_wxc()` and :meth:`~.workspace.WorkspaceList.create()` now use the new :class:`~.org.WebexLicenseList` to find an available license
- **BREAKING CHANGE ** - New :class:`~.org.WebexLicenseList` which provides a list of :class:`~.org.WebexLicense` objects. The new list class now provides all of the license searches and also provides logic to assign licenses. This changes the old `Org.licenses`, which returned a dict
- Added docs to :class:`~.cdr.CallDetailRecords`
- Accessing :class:`~.recordings.Recording` attributes no longer "wastes" an API call if it already has the :attr:`Recording.details` dict from Webex
- Started prework to give the :class:`~.cdr.CallDetailRecords` more functionality
- :meth:`PersonList.get() <.person.PersonList.get()>` now supports a ``'uuid'`` argument to find a Person by UUID, which is what is populated in CDRs

v4.4.4
------
- BUG FIX: Fixed Announcement uploads and GETs to pass ``'orgId'`` to allow it to be used across Orgs
- BUG FIX: When a :class:`~.person.Person` has a Webex Calling license but no Location, they were still marked with an :attr:`wxc` attribute of True. This has been resolved to require both a license and a Location.

v4.4.3
------
- BUG FIX: wxcadm was requiring the wrong requests version. Updated to require >-2.31.0

v4.4.2
------
- User Move Jobs now support up to 100 users/people at a time.
- The :class:`~.person.Person` class now supports preferred answer endpoints and assignment of an endpoint
- New :class:`.person.ApplicationLine` available via :attr:`ApplicationLineAssignments.lines <.person.ApplicationLineAssignments.lines>`
- New :class:`~.person.ApplicationLineAssignments` available via :attr:`ApplicationServicesSettings.line_assignments <.person.ApplicationServicesSettings.line_assignments>`
- New :class:`~.person.ApplicationServicesSettings` available via :attr:`Person.applications <.person.Person.applications>`
- :meth:`Location.set_ecbn() <.location.Location.set_ecbn()>` now accepts a :class:`HuntGroup`
- :class:`BargeInSettings <.models.BargeInSettings>` supports :meth:`~.models.BargeInSettings.set_enabled()` and :meth:`~.models.BargeInSettings.set_tone_enabled()` to configure the values
- Barge-In settings for :class:`Person` and :class:`Workspace` have been modernized to a :class:`BargeInSettings <.models.BargeInSettings>` class available via :attr:`Person.barge_in <.person.Person.barge_in>` and :attr:`Workspace.barge_in <.workspace.Workspace.barge_in>`. The old :meth:`Person.get_barge_in()` and :meth:`Person.push_barge_in()` have been deprecated and will be removed in 4.5.0.
- Professional Workspaces can now be listed directly with :meth:`WorkspaceList.professional() <.workspace.WorkspaceList.professional()>`
- BUG FIX: When a Person was synced from Entra ID with an existing phone number, the :meth:`Person.assign_wxc()` would fail if the phone number from Entra ID matched the existing number. The entire `assign_wxc()` was refactored to use the API endpoint directly rather than calling :meth:`Person.update_person()`

v4.4.1
------
- Playlists are now supported via :attr:`Org.playlists <.org.Org.playlists>`. This returns a :class:`PlaylistList <.announcements.PlaylistLists>` with :class:`Playlist <.announcements.Playlist>` entries
- BUG FIX: Adding a PhoneOS (i.e. 9800) phone to a Person or Workspace by MAC address would throw an exception due to the "empty" API response from Webex. Now, the device is found with a second API call and returned, although with limited functionality
- Added :meth:`AnnouncementList.get() <.announcements.AnnouncementList.get()>` to allow Announcements to be retrieved. Especially handy for the new Playlist functionality
- Added :meth:`DeviceList.get_by_status() <.device.DeviceList.get_by_status()>` to allow devices to be retrieved by their connection status
- :class:`Device <.device.Device>`s in a :class:`DeviceList <.device.DeviceList>` now all have the same config values. Previously Devices that were assigned to a Person did not have things like `connection_status`
- BUG FIX: :meth:`Device.set_layout() <.device.Device.set_layout()>` has been fixed
- BUG FIX: :meth:`Person.get_monitored_by() <.person.Person.get_monitored_by()>` now returns the right information

v4.4.0
------
- New method :meth:`LocationList.with_pstn() <.location.LocationList.with_pstn()>` added to retrieve a list of Locations with or without a PSTN provider configured. :meth:`LocationList.without_pstn()` also exists as an alias for :meth:`with_pstn(False)`
- New method :meth:`Location.set_main_number() <.location.Location.set_main_number()>` allows the Main Number to be set. This accepts either a :class:`~.number.Number` or a string.
- :attr:`Location.main_number` now uses new logic to determine the Location's Main Number, and returns it as a :class:`.number.Number` instance
- BUG FIX: The Realtime classes (currently only :class:`~.location_features.VoicePortal`) have been fixed to allow additional API fields that don't come back in the GET. This fixes setting :attr:`VoicePortal.extension`
- PSTN Connections for Locations are now supported! See the :attr:`.location.Location.pstn` property and the docs for the :class:`~.pstn.LocationPSTN` class
- **BREAKING CHNGE** - :meth:`~.location.Location.set_enhanced_emergency_routing` has been removed. :meth:`~.location.Location.set_enhanced_emergency_calling(mode='routing')` should be used instead.
- BUG FIX: :meth:`.location.Location.enable_webex_calling()` now correctly handles addresses without an 'address2' value
- :meth:`~.person.Person.ecbn_null_change()` added to address a bug where Control Hub and Webex Calling are out of sync
- Recording Vendor settings are now available for :class:`~.org.Org` and :class:`~.location.Location` via the :attr:`recording_vendor` property, which returns a :class:`~.recording.OrgRecordingVendorSelection` or :class:`~.recording.LocationRecordingVendorSelection`
- Org-wide Queue settings are available at :attr:`Org.queue_settings`, which returns a :class:`.call_queue.OrgQueueSettings` instance
- **BREAKING CHANGE** - :attr:`.workspace.Workspace.monitoring` now returns a :class:`~.monitoring.MonitoringList` instead of a dict
- :class:`~.monitoring.MonitoringList` with improved functionality. See docs for a complete list of methods
- **BREAKING CHANGE** - :meth:`~.person.get_monitoring()` and :meth:`.person.push_monitoring()` have been removed and replaced with the :attr:`Person.monitoring` attribute, which returns a :class:`.monitoring.MonitoringList` to make managing monitored elements easier
- The :class:`Trunk` class now supports all of the detailed attributes for the trunk
- New method :meth:`NumberList.get_by_owner()` which allows searches by number owner
- :class:`VirtualLine` now supports :meth:`get_call_recording()`, :meth:`enable_call_recording()` and :meth:`disable_call_recording()` like :class:`Person`

v4.3.11
-------
- BUG FIX: :meth:`RedSkyUser.user_locations` has been fixed
- :meth:`Person.enable_call_recording()` now supports arguments specific to Webex Recording.
- BUG FIX: :meth:`Person.disable_call_recording()` has been fixed.
- :meth:`Recording.get_transcript()` has been added to allow the recording transcript to be obtained.
- 4.3.11 includes my yearly clean-up so a log of new documentation, logging, and some (hopefully) small changes to the internals. I've started reworking the People class, which is the oldest one, to match with the behavior of a lot of the newer classes. At some point, this will likely mean breaking some things to replace them, but that will come in 4.4.0.
- Added :meth:`Location.set_enhanced_emergency_calling()`
- Added :attr:`Location.enhanced_emergency_calling`, which returns a :class:`LocationEmergencySettings`
- Generically, I have started using named tuples instead of dicts for attributes returned by Webex for attributes that aren't objects to pass to other calls. For example :attr:`Location.enhanced_emergency_calling` returns a :class:`LocationEmergencySettings`
- BUG FIX: :meth:`Person.push_monitoring()` has been fixed to accept the config returned by :meth:`Person.get_monitoring()` to make it easy to copy from one Person to another.
- BUG FIX: :class:`XsiEventsChannel` now only waits 30 seconds for the channel to come up and then attempt to restart it. Previously it would wait forever, but it was found that some channels never came up.

v4.3.10
-------
- BUG FIX: :meth:`Device.set_layout` and the respective :class:`DeviceLayout` now does not include an empty string for ``'kemType'``
- Added :attr:`Workspace.caller_id` and :meth:`Workspace.set_caller_id()`
- Added :attr:`Location.external_caller_id_name` and :meth:`Location.set_external_caller_id_name` to control this value
- Modified :meth:`Trunks.get()` to also accept ``id`` in addition to ``name``
- Added :meth:`RouteLists.get()` to find RouteLists
- New method :meth:`Location.set_unknown_extension_policy()` to set the Unknown Extension Routing Policy for the Location
- Added :attr:`Location.unknown_extension_policy` to retrieve the current Unknown Extension Routing Policy
- The ``call_policy`` parameter on :meth:`HuntGroupList.create()` was changed to optional with a default Policy for quicker HG builds
- Added :meth:`HuntGroup.add_agent()` to support adding new agents to a Hunt Group
- :meth:`HuntGroupList.create()` not supports adding agents when the Hunt Group is created
- Added :attr:`Location.ecbn` and :meth:`Location.set_ecbn()` to allow direct access and control of Location-level ECBN settings
- Added :attr:`Location.routing_prefix` and :meth:`Location.set_routing_prefix()` to allow direct access and control of the Routing Prefix (i.e. Location Code)
- Added :meth:`Workspace.get_monitored_by()` and :meth:`Person.get_monitored_by()` to allow a list of Users/Workspaces that are monitoring the selected Person/Workspace
- Added :attr:`Workspace.monitoring` to get the dict of monitoring for the Workspace
- Added :meth:`VoicePortal.copy_config()` to support easy cloning of Voice Portal settings
- :class:`Location` now has a :attr:`Location.workspaces` property to get a :class:`WorkspaceList` of all Workspaces at the Location

v4.3.9
------
- BUG FIX: :meth:`NumberManagementJobList.create()` has been fixed
- :meth:`LocationList.webex_calling()` now uses a more efficient API call to reduce the time it takes to populate the data

v4.3.8
------
- MAJOR CHANGE: Most people are already using Python 3.10 or greater, but I just found that the PIP requirements showed Python >= 3.6 which will not work with newer version of the requests library

v4.3.7
------
- BUG FIX: :meth:`LocationList.webex_calling()` did not work for Orgs other than the native one and has been fixed.
- Lots of new attributes in :class:`AutoAttendant`. Most of the config items were not exposed except in the JSON :attr:`AutoAttendant.config` and are now exposed as attributes.
- :meth:`RouteGroup.add_trunk()` to be able to add new a Trunk to a Route Group
- **BREAKING CHANGE**: :meth:`CallRouting.RouteGroups.get_route_group()` has been renamed to simply :meth:`get()` to match other modules

v4.3.6
------
- BUG FIX: Fixed problems with Xsi-Events Heartbeats to invalid channels

v4.3.5
------
- BUG FIX: :meth:`Person.assign_wxc()` was sending the ``manager`` property, which cannot be sent via API
- BUG FIX: :meth:`Org.get_number_assignment()` now returns the correct object

v4.3.4
------
- :meth:`Device.set_layout()` to allow a :class:`DeviceLayout` to be configured on a device
- New method :meth:`Workspace.set_professional_license()` allows Workspaces with a Workspace license to be converted to a Professional license. Not that, as of this release, the Webex API does now allow a Professional Workspace to be downgraded to a Workspace license.
- New property :attr:`Workspace.license_type` returns 'PROFESSIONAL' or 'WORKSPACE' to allow the license type to be determined
- :meth:`WorkspaceList.create()` now accepts a ``license_type`` argument to allow Professional licenses to be assigned to a Workspace
- **BREAKING CHANGE** - :attr:`Workspace.location_id` has been renamed to :attr:`Workspace.location` to reflect that it is a :class:`Location` instance, not an ID string
- New :class:`TranslationPattern` and :class:`TranslationPatternList` accessed via :attr:`Org.translation_patterns` and :attr:`Location.translation_patterns`
- Moved Audit Events to :class:`AuditEvent`, which is contained in :class:`AuditEventList` and still accessed via :meth:`Org.get_audit_events()`
- Added :attr:`Webex.access_token_expires`, :attr:`Webex.refresh_token_expires` which are automatically updated by :meth:`Webex.get_new_token()` to prepare for upcoming keep-alive feature

v4.3.3
------
- Added :meth:`Person.get_ptt()` and :attr:`Person.ptt`, along with :meth:`Person.push_ptt()` to control Push-to-Talk settings
- :meth:`Person.assign_wxc()` now supports a ``license_type`` argument to allow Standard licenses to be applied.
- Added ``Trackingid`` to debug logging for responses from Webex

v4.3.2
------
- Initial work started for CDR analysis in **wxcadm**
- :class:`DECTHandset` now has a :attr:`DECTHandset.mac` property with the MAC address of the handset
- BUG FIX: :meth:`Person.assign_wxc()` has been fixed to support the new API syntax when a phone number is not present

v4.3.1
------
- BUG FIX: :attr:`Person.user_groups` is now a property and correctly returns the list of UserGroups that the Person is assigned to
- :class:`Person` now supports :attr:`Person.login_enabled`
- **wxcadm** now requires requests 2.32.3 to resolve the urllib discrepancy warning
- BUG FIX: :class:`DeviceLayout` now uses the correct API endpoint and works correctly
- BUG FIX: :meth:`Webex.get_person_by_email()` and :meth:`Webex.get_person_by_id()` now returns Calling-related data

v4.3.0
------
- **BREAKING CHANGE**: :meth:`Person.add_device()` and :meth:`Workspace.add_device()` has been removed in favor of :meth:`Person.devices.create()` and :meth:`Workspace.devices.create()` which matches the list-class logic used elsewhere.
- **BREAKING CHANGE**: Adding a new device to a Person or Workspace now requires the :class:`SupportedDevice` to be passed to the :meth:`DeviceList.create()`. As more device types are supported, this provides a way to determine what onboarding methods are supported and what data is required.
- DEPRECATION: :class:`WorkspaceLocation` (and the entire Workspace Location concept) is being replaced with the existing Location ID
- Added :meth:`Workspace.set_ecbn()`, :meth:`Person.set_ecbn()`, :meth:`VirtualLine.set_ecbn()` to set Emergency Callback Number for each
- Added :attr:`Workspace.ecbn`, :attr:`Person.ecbn`, :attr:`VirtualLine.ecbn` to view Emergency Callback Number for each
- Added :attr:`Location.virtual_lines`
- BUG FIX: :meth:`Person.update_person()` now sends ``locationId`` correctly
- All API calls in the :class:`Device` class will now send ``orgId`` as a query parameter
- Added :attr:`Person.org_id`, :attr:`VirtualLine.org_id` and :attr:`Workspace.org_id` to make API calls easier
- :class:`Device` now has a ``layout`` property, which is a :class:`DeviceLayout`
- Added :class:`RebuildPhonesJob` and :class:`RebuildPhonesJobList` which can be accessed from :attr:`Org.rebuild_phones_jobs`
- BUG FIX: All of the :class:`UserMoveJob` methods now send ``orgId`` for tokens with access to multiple Orgs
- BUG FIX: :meth:`DeviceList.create()` now sends ``orgId`` with the POST for tokens with access to multiple Orgs
- DEPRECATION: :meth:`Person.add_device()` has been deprecated. Use :meth:`Person.devices.create()` instead
- BREAKING CHANGE: :attr:`Org.numbers` and :attr:`Location.numbers` now uses :class:`NumberList`
- :meth:`AutoAttendantList.create()` now supports ``business_hours_menu`` and ``after_hours_menu`` as optional arguments, building an empty menu when omitted
- The :class:`Number` and :class:`NumberList` classes have been added to handle all number-management and search functions
- :meth:`webex_api_call()` now supports the HTTP 451 which is used to redirect analytics calls to the correct region
- :meth:`Person.assign_wxc()` now supports an ``unassign_ucm`` parameter to allow UCM licenses to be removed automatically when Webex Calling is added.
- BUG FIX: :meth:`WorkspaceList.get()` now works correctly when UUID is not used by the search
- Created :class:`VoicemailGroup` and :class:`VoicemailGroupList` which can be obtained from :attr:`Org.voicemail_groups` to manage Voicemail Groups
- Created :class:`OutgoingPermissionDigitPattern` and :class:`OutgoingPermissionDigitPatternList` which can be obtained from :attr:`Location.outgoing_permission_digit_patterns` to manage the new capability
- All classes are now imported and exposed at the module level, so, for example, ``wxcadm.people.Person`` can be referenced as ``wxcadm.Person``
- BUG FIX - When adding devices on a secondary Org, the ``orgId`` param is now passed correctly

v4.2.6
------
- Updated requirements to use the latest version of dataclasses-json

v4.2.5
------
- Modified :meth:`Person.update_person()` to handle new attrs
- Internal prep work for SCIM2 API, which may or may not replace the People API for some methods
- Added :attr:`Person.avatar`, :attr:`Person.department`, :attr:`Person.title`, :attr:`Person.manager`, :attr:`Person.manager_id`, :attr:`Person.addresses` which are now handled by the People API
- Added :meth:`DeviceMember.set_hotline()`
- Added :meth:`DeviceMember.set_call_decline_all()`
- Added :meth:`DeviceMember.set_line_label()`
- Changed :meth:`DeviceList.get()` to allow `mac_address` as an argument to find a Device
- Added :meth:`DeviceMemberList.get()` to allow the :class:`DeviceMember` to be found by :class:`Person` or :class:`Workspace`
- Changed :attr:`DeviceMember.allow_call_decline` to :attr:`DeviceMember.call_decline_all` to reflect what it does and what Control Hub calls it

v4.2.4
------
- :class:`Reports` has become :class:`ReportList` and supports the standard list class functions from other classes.
- :meth:`get_report_lines()` now supports both Zip and unzipped data
- Logging enhancements to HTTP DELETE calls
- :class:`DECTNetworkList` and the other DECT classes now support retrieval and updating

v4.2.3
------
- Fixed `spark_id` for :class:`AutoAttendant` and :class:`HuntGroup`

v4.2.2
------
- Added `uuid` to :meth:`HuntGroupList.get()` to support UUID lookup for CDR correlation
- Added `uuid` to :meth:`WorkspaceList.get()` to support UUID lookup for CDR correlation
- Added `uuid` to :meth:`CallQueueList.get()` to support UUID lookup for CDR correlation
- Added `uuid` to :meth:`AutoAttendantList.get()` to support UUID lookup for CDR correlation
- New method :meth:`LocationSchedule.clone()` to allow schedules to be cloned within a Location and across Locations
- :meth:`Person.reset_vm_pin()` previously used the CP-API permissions. A developer API was released that allows the method to work with "normal" scopes.
- The :class:`Device` class now has a :attr:`Device.workspace_location_id` property to determine the primary :class:`WorkspaceLocation` of the device. Note that at this time, the ID returned by the Webex API does not exactly match the `workspaceLocationId` value of the :class:`WorkspaceLocation` so you have to decode the Spark ID with :meth:`decode_spark_id` and use the UUID to match.
- Virtual Lines are now supported with the :class:`VirtualLineList` and :class:`VirtualLine` classes, accessed with the :attr:`Org.virtual_lines` property
- New :meth:`Reports.delete_report()` to allow reports to be deleted.

v4.2.1
------
- BUG FIX: All of the :class:`RedSky` methods had a problem with API pagination and had to be reworked

v4.2.0
------
- The :meth:`MerakiNetwork.redsky_audit()` now correctly handles BSSID masking by setting the "bssidMasking" to False
- BUG FIX: In the event that an Org with no People is accessed, the :attr:`Org.people` will no longer throw a KeyError
- New List Class :class:`DECTNetworkList` accessed with :attr:`Location.dect_networks`. For this release, only the creation of DECT Networks, Base Stations, and Handsets is supported.
- :meth:`DeviceList.create()` to add new devices. This will deprecate the :meth:`Person.add_device()` and :meth:`Workspace.add_device()` methods, which will remain for now.
- New List Class :class:`DeviceList` for use with :attr:`Org.devices`, :attr:`Person.devices` and :attr:`Workspace.devices`
- :class:`Device` now supports :class:`DeviceMemberList` accessible via the :attr:`Device.members` property
- Added a new ``single=True`` argument to :meth:`LocationList.webex_calling()`. There are a few API calls that need a Webex Calling Location, but it doesn't matter which one. This will return a single Location where :attr:`calling_enabled` is True.
- When a :class:`Location` is initialized, it now will not automatically pull the Webex Calling config until it is needed. This speeds up responses when just finding a Location by Name/ID when you don't care whether it is Calling-enabled
- Changed the :class:`Webex` class to add an `org_id` param to the initialization for admins who want to act on a specific Org. This param takes either the Base64 or UUID format Org ID and simply maps that Org from Webex.orgs[x] to the :attr:`Webex.org` attribute.
- Changed the :class:`Webex` class to remove some of the options to pre-collect data. Data is only collected, and the API calls made, when the data is requested, so there is no need to pre-fetch data.

v4.1.1
------
- Added `pyhumps` to the requirements. 'pyhumps' is the library I have elected to use to convert between the Webex camelCase to the Python snake_case. Over the next few versions, I am going to be looking at all existing classes to determine the best way to convert them.
- There is now a superclass :class:`RealtimeClass`, which allows the subclass to call the Webex API as soon as an instance attribute is changed. The first class to utilize this functionality is the :class:`VoicePortal` class, so, for example, setting :attr:`VoicePortal.extension` to a new value will puss the new extension immediately.
- BUG FIX: :meth:`Workspace.add_device()` did not work correctly with `model='Imagicle Customer Managed'`

v4.1.0
------
- New methods :meth:`Person.remove_did()` and :meth:`Person.add_did()` to allow easy unassignment of the DID and the ability to add one, especially useful in User/Number moves between Locations because the number has to be unassigned to move.
- :class:`UserMoveJob` with List Class :class:`UserMoveJobList` accessible via :attr:`Org.user_move_jobs`. These classes deal with the ability to move users between Locations.
- Changed :meth:`XSI.get_fac()` to a property :attr:`XSI.fac_list` to make it similar to other XSI methods and cleaned up the response as a :class:`FeatureAccessCode` list
- :class:`APIError` now returns the exception rather than just a string showing what failed so it can be parsed.

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
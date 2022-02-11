Workspaces - Use Location as Caller ID
======================================
Companies may wish to present the Location name and number as Caller ID for external calls placed from Workspace
devices. This is especially common for conference rooms and common areas where it isn't desirable for the DID to be
displayed to the any called number.

The following scripts illustrate two ways to accomplish this, but the methods used within these examples could be used
for any logic to determine the Workspace ID.

Change All Workspaces Across the Webex Org
------------------------------------------
.. code-block:: python

    import wxcadm

    access_token = "Your API Access Token"

    webex = wxcadm.Webex(access_token, fast_mode=True)     # fast_mode can be used since we aren't dealing with People
    devices = webex.org.devices
    changed_count = 0

    for device in devices:
        # Only act on devices that are "MACHINE" types (Workspaces) and have .calling_type == "WEBEX"
        if device.account_type.upper() == "MACHINE" and device.calling_type.upper() == "WEBEX":
            print(f"Changing workspace: {device.display_name}...", end="")
            # The special LOCATION and LOCATION_NUMBER are used to automatically pick the Location info
            device.change_workspace_caller_id(name="LOCATION", number="LOCATION_NUMBER")
            print("done")
            changed_count += 1

    print(f"Changed {changed_count} workspaces.")

Change Workspaces in Specified Calling Locations
------------------------------------------------
.. code-block:: python

    import wxcadm

    access_token = "Your API Access Token"
    # Define the Webex Calling Location names that you want devices changed in
    locations_to_change = ["Headquarters", "Location 1", "Location X"]

    webex = wxcadm.Webex(access_token, fast_mode=True)     # fast_mode can be used since we aren't dealing with People
    devices = webex.org.devices
    changed_count = 0

    for device in devices:
        # Only act on devices that are "MACHINE" types (Workspaces) and have .calling_type == "WEBEX"
        if device.account_type.upper() == "MACHINE" and device.calling_type.upper() == "WEBEX":
            # And only change devices in the locations_to_change
            if device.calling_location['name'] in locations_to_change:
                print(f"Changing workspace: {device.display_name}...", end="")
                # The special LOCATION and LOCATION_NUMBER are used to automatically pick the Location info
                device.change_workspace_caller_id(name="LOCATION", number="LOCATION_NUMBER")
                print("done")
                changed_count += 1

    print(f"Changed {changed_count} workspaces.)

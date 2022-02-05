RedSky - Add Webex Locations as Buildings
=========================================
This script will go through all of the locations for an Org and create RedSky Buildings for each of them. It will also
create a Location within each building called "Default", which can be used until more Location granularity needs to be
added.

.. code-block:: python

    from wxcadm import Webex, RedSky

    webex_access_token = "Your Webex API Access Token"
    redsky_user = "Your RedSky Horizon admin username"
    redsky_pass = "Your RedSky Horizon admin password"

    # Connect to Webex. You can use fast_mode=True since we won't be dealing with user phone numbers
    webex = Webex(webex_access_token, fast_mode=True)

    # Connect to RedSky
    redsky = RedSky(redsky_user, redsky_pass)

    # Loop through the Locations and add them via RedSky
    # You can store each of the new buldings in a list if needed
    new_buildings = []
    for location in webex.org.locations:
        # If the Location is not in the United States, don't add it
        if location.address['country'] != "US":
            continue
        else:
            building = redsky.add_building(location, create_location=True)
            new_buildings.append(building)

    # And now you have the new_buildings list if you need to do anything with it, For example:
    for building in new_buildings:
        print(f"{building.name},{building.id}")
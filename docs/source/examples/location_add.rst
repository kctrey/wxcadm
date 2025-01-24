Adding and Managing Webex Calling Locations
===========================================
As of v4.4.0 of **wxcadm**, it is possible to add a Location and configure it for Webex Calling, including setting up
a PSTN connection. Note that it is still not possible to add Numbers to Locations that use an Integrated Cloud
Calling PSTN Provider (CCPP), because the APIs between the Provider and Webex are not public.

The steps below outline the creation of a Location.

Create the Location
-------------------
To create a Location, a few items are required:

- Location Name
- Time Zone
- Preferred Language
- Address

The address must be stored in a Python dict in the following format:

.. code-block:: python

    address = {
        'address1': '100 N. Main St',
        'address2': '',
        'city': 'Houston',
        'state': 'TX',
        'postalCode': '32123',
        'country': 'US'
    }

The following code would add a Location called "Site 100" with the address from above, and using the Central time zone
and US-English language:

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    location_time_zone = 'America/Chicago'
    location_language = 'en_US'
    location_address = {
        'address1': '100 N. Main St',
        'address2': '',
        'city': 'Houston',
        'state': 'TX',
        'postalCode': '32123',
        'country': 'US'
    }

    # Connect to Webex
    webex = wxcadm.Webex(webex_access_token)
    # Create the Location
    webex.org.locations.create(
        name=location_name,
        time_zone=location_time_zone,
        preferred_language=location_language,
        address=location_address
    )

Enable Webex Calling for the Location
-------------------------------------
Once the Location has been created, you will need to enable Webex Calling for the Location.

The following will enable Webex Calling on the "Site 100" Location that we created in the previous step:

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Enable Webex Calling
    my_location.enable_webex_calling()

Choose the PSTN Provider for the Location
-----------------------------------------
After Webex Calling has been enabled, a PSTN Provider or connection needs to be defined for the Location. The steps to
select a PSTN Provider and assign it vary depending on the type of PSTN to be used: Integrated Cloud-Connected,
Non-Integrated Cloud-Connected, or Local Gateway (Premise PSTN).

The sections below outline the steps based on the type of PSTN Provider being used.

Integrated and Non-Integrated Cloud-Connected
#############################################
The steps for both Integrated and Non-Integrated Cloud-Connected Providers are the same from an API and **wxcadm**
perspective. The difference is that Phone Numbers cannot be added via API for Integrated Cloud-Connected Providers.

In order to assign the Cloud-Connected Provider, you will have to know the full name of the Provider as it is stored in
Webex. The following code snippet with allow you to print the names of all PSTN Providers that are available for the
newly-created Location:

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Loop through the available providers and print them
    for provider in my_location.pstn.available_providers:
        print(provider.name)

Once you know the name of the Provider you want to assign to the Location, the following code will set the PSTN
Provider:

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    pstn_provider = "The full Provider name"

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Get the Provider instance of the Provider you want to use
    selected_provider = my_location.pstn.available_providers.get(name=pstn_provider)
    # Set the selected provider on the Location
    my_location.pstn.set_provider(selected_provider)

LGW (Premise PSTN)
==================
When using Premise PSTN, the Location can use either a Trunk or a Route Group as the PSTN connection. The one you select
will depend on the LGW architecture in use.

For either case, you will need to know the name of the Trunk or Route Group that you wish to assign.

Trunk
+++++

    .. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    trunk_name = "LGW_1"

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Get the Trunk instance on the Trunk you want to use
    selected_trunk = webex.org.routing.trunks.get(name=trunk_name)
    # Set the selected Trunk as the PSTN connection for the Location
    my_location.pstn.set_provider(selected_trunk)

Route Group
+++++++++++

    .. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    route_group = "RG_East"

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Get the Route Group instance on the RG you want to use
    selected_rg = webex.org.routing.route_groups.get(name=route_group)
    # Set the selected Route Group as the PSTN connection for the Location
    my_location.pstn.set_provider(selected_rg)

Add Numbers (Non-Integrated CCP and Premise PSTN Only)
-------------------------------------------------------
For Non-Integrated Cloud Connected and Premise PSTN, Numbers can be added via the API and are supported by **wxcadm**.

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    number_list = [
        '9152212221',
        '9152212222',
        '9152212223'
    ]

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Add the numbers to the Location
    webex.org.numbers.add(my_location, number_list)

Set the Main Number of the Location
-----------------------------------
Currently, the ability to set the Main Number of a Location, which is required for calls inbound or outbound, is not
supported by the Webex APIs and is, therefore, not supported by **wxcadm**.

Set the Voice Portal Number or Extension
----------------------------------------
When setting up a Location, a Voice Portal extension or phone number must be assigned for Voicemail to work properly.

You own numbering scheme determines whether you require only an extension or a full phone number. In many cases, all
Locations will use the same extension for simplicity. The following code snippet creates a Voice Portal extension
"99998" at the "Site 100" Location.

Note that the Voice Portal commands look slightly different than many of the other **wxcadm** methods. The
:class:`~.location_features.VoicePortal` class is a real-time class where changes to the Python data are pushed directly
to Webex. If you don't know what that means, no big deal; just know that the Voice Portal extension will be changed as
soon as the command is run.

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    voice_portal_extension = '99998'

    webex = wxcadm.Webex(webex_access_token)
    # Get the Location instance of the desired Location
    my_location = webex.org.locations.get(name=location_name)
    # Set the Voice Portal extension
    my_location.voice_portal.extension = voice_portal_extension

Complete Script
===============
In the examples above, you saw how to create the Location and get it set up, all using individual Pyton scripts. In the
real world, you would probably use a single script to do all of the work at one time. The following is an example of all
the previous scripts as a single script.

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Access Token"
    location_name = "Site 100"
    location_time_zone = 'America/Chicago'
    location_language = 'en_US'
    location_address = {
        'address1': '100 N. Main St',
        'address2': '',
        'city': 'Houston',
        'state': 'TX',
        'postalCode': '32123',
        'country': 'US'
    }
    location_trunk = 'LGW_1'
    number_list = [
        '9152212221',
        '9152212222',
        '9152212223'
    ]
    voice_portal_extension = '99998'

    # Connect to Webex
    webex = wxcadm.Webex(webex_access_token)
    # Create the Location
    webex.org.locations.create(
        name=location_name,
        time_zone=location_time_zone,
        preferred_language=location_language,
        address=location_address
    )
    # Grab the newly-created Location for use in the next sections
    webex.org.locations.refresh()
    new_location = webex.org.locations.get(name=location_name)
    # Enable Webex Calling
    new_location.enable_webex_calling()
    # Connect the PSTN (a Premise LGW Trunk, in this case) to the Location
    trunk = webex.org.routing.trunks.get(name=location_trunk)
    new_location.pstn.set_provider(trunk)
    # Add the Numbers to the Location
    webex.org.numbers.add(new_location, number_list)
    # Set the Voice Portal Extension
    new_location.voice_portal.extension = voice_portal_extension

In Summary
==========
Once you have the Location created, **wxcadm** provides methods to help with the management of the Location and its
features. See the :class:`.location.Location` section of these docs to help with anything else.
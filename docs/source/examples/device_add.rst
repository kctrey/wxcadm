Add a Device to a Person or Workspace
=====================================

With **wxcadm** it is possible to add Webex Calling devices to People (i.e. Users) and Workspaces. Each device model
supports onboarding by MAC address, Activation Code, or both. In order to add a device, you must first determine the
:class:`SupportedDevice` model from the :attr:`Org.supported_devices` :class:`SupportedDeviceList`. A method is provided
which allows the SupportedDevice to be searched by model name.

For example, to add a Cisco 8851 to a user using an Activation Code, the following script can be used:

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Webex API Access Token"
    user = "user@domain.com"

    webex = wxcadm.Webex(webex_access_token)

    # Get the SupportedDevice instance for a Cisco 8851 MPP phone
    mpp = webex.org.supported_devices.get('Cisco 8851')

    # Add the device to the user. When the ``create()`` method is called without a ``mac=`` argument, **wxcadm** will
    # confirm the SupportedDevice allows Activation Code onboarding and will add it.
    new_device = webex.org.people.get(email=user).devices.create(model=mpp)

    # Print the Activation Code that was returned by Webex
    print(new_device['activation_code'])

Adding a Device by MAC Address
------------------------------
In many cases, a SupportedDevice does not allow Activation Code onboarding, or the MAC Address is already known. The
onboarding of these devices is different for devices that are managed by the Webex, such as Cisco MPP phones, and those
that are managed by the customer or partner, such as a "Generic IPPhone".

Webex-managed devices do not require or provide a password in their response. For example, to onboard a Cisco 6841 MPP:

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Webex API Access Token"
    user = "user@domain.com"
    phone_mac = "AA:BB:CC:DD:EE:FF"

    webex = wxcadm.Webex(webex_access_token)

    # Get the SupportedDevice instance for a Cisco 6841 MPP phone
    mpp = webex.org.supported_devices.get('Cisco 6841')

    # Add the device to the user
    new_device = webex.org.people.get(email=user).devices.create(model=mpp, mac=phone_mac)

    # Adding a device with a MAC Address creates a :class:`Device` instance. You can access it directly
    device = new_device['device_object']

Adding a Customer-Managed Device
--------------------------------
Adding a Customer-Managed Device will return the SIP credentials needed to provision the device to register with
Webex Calling.

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Webex API Access Token"
    user = "user@domain.com"
    phone_mac = "AA:BB:CC:DD:EE:FF"

    webex = wxcadm.Webex(webex_access_token)

    # Get the SupportedDevice instance for a Generic IPPhone
    mpp = webex.org.supported_devices.get('Generic IPPhone')

    # Add the device to the user
    new_device = webex.org.people.get(email=user).devices.create(model=mpp, mac=phone_mac)

    The new_device dict contains the required provisioning information
    print(f"SIP Auth User: {new_device['sip_auth_user']})
    print(f"SIP Password: {new_device['sp_password']})
    print(f"SIP User: {new_device['sip_userpart']})
    print(f"SIP Domain: {new_device['sip_hostpart']})
    print(f"SIP Outbound Proxy: {new_device['sip_outbound_proxy']})

Listing Supported Device Model Names
------------------------------------
As you can see, knowing the name of the SupportedDevice model is important to adding devices, because the
SupportedDevice ensures that the correct onboarding method is used. To list the SupportedDevice models available for
use, the :class:`SupportedDeviceList` can be accessed with the :attr:`Org.supported_devices` property.

.. code-block:: python

    import wxcadm

    webex_access_token = "Your Webex API Access Token"

    webex = wxcadm.Webex(webex_access_token)
    for model in webex.org.supported_devices:
        print(model.model)
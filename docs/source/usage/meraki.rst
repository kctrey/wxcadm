.. py:currentmodule:: wxcadm.meraki

=========================================
Using Meraki for RedSky Network Discovery
=========================================

With the requirement to provide accurate dispatchable location information for Emergency (i.e. 911) calls in the
United States, it is necessary for Webex Calling admins, or RedSky admins, to know and understand the IP network
architecture at the hardware level. Webex Calling, via the integration with RedSky, uses the network connection in order
to determine the address information to send to the Public Safety Answering Point (PSAP). Since Webex Calling
administrators aren't always aware of new switches and access points as they are added to the corporate network, it
makes sense to use the network inventory systems, such as the Meraki Dashboard, as the source for this data. This
ensures the engineers who are installing and configuring these devices, and who have the best knowledge of the
coverage of the devices, can populate an accurate dispatchable address.

Although this practice is not limited to Cisco network management, the Meraki Dashboard provides an easy way to
access this data and use it in a RedSky envirnoment. **wxcadm** supports a native way to use the Meraki Dashboard API
to obtain this data and automatically populate the RedSky Network Discovery.

In a Meraki network, all devices, whether they are siwtches, switch ports, or Wi-Fi access points, have the ability to
be tagged with various identifiers. **wxcadm** uses a tag in the format "911-Location_Name" to associate the device with
a Location in RedSky. By adding a "911-" tag to any element, the :py:meth:`redsky_audit()` is able to determine the
desired Location and make the correct Network Discovery mapping in RedSky.

Before You Begin
================
The Meraki functionality of **wxcadm** requires the `meraki <https://pypi.org/project/meraki/>`_ Python library, which
is not installed when **wxcadm** is installed with PIP. You will need to install that library in order to use these
methods: ``python3 -m pip install meraki``

**wxcadm** also needs a valid Meraki Dashboard API access token. Instructions on creating an API access token can be
found `here <https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API>`_.

As mentioned in the RedSky section of this documentation, you will also need a RedSky admin username and password.

From the Meraki perspective, the :py:meth:`redsky_audit()` assumes a number of things about the configuration of the
Meraki network. To ensure the full functionality, the following guidelines should be followed:

- The audit is performed at the Network level of the Meraki hierarchy. If multiple networks are used, the audit should
be repeated for each.
- The tag used to identify the Dispatchable Location text (e.g. "Floor 1", "Floor 2", "West side") must follow the
format "``911-Location_Name``" (i.e. "911-Floor_1", "911-Floor_2", "911-West_side")
- Tags can be applied as follows:
  - Switch
    - When a tag is applied to a switch, the entire switch chassis will be assigned to the Location_name of the tag
  - Switch Port
    - When a switch port is tagged, the port will be added to RedSky with the appropriate Location_name
    - If a switch port is tagged, the switch must also be tagged. The Location_names do not have to be the same.
    - Switch ports are considered an override for the switch, so if only one port needs a different Location_name than
the switch.
  - Access Point
    - When a tag is applied to an access point, all SSIDs and bands will be mapped to the same Location_name. This may
not be desirable if the RF coverage is different, but Meraki doesn't provide a method to tag individual BSSIDs.

Building Determination
----------------------
You have seen how the Locations are determined using the device tags in Meraki. As you probably know, RedSky uses a
2-tiered hierarchy for determining the location of a phone device where each Location is associated with a Building.

Because Meraki already has an address field for every network device, **wxcadm** is able to use that address to find
the associated Building in RedSky if it is is built. However, in order for this to work efficiently, the address in
Meraki should be identical to the one in RedSky.

When the :py:meth:`redsky_audit()` method runs, it looks at the address of the Meraki device and attempts to match the
entire address (street address, city, state, ZIP) against an existing RedSky building. If no match is made, the method
ignored the city, state and ZIP code and attempts to locate the building based only on the street address. It does this
because the likelihood of an organization having two buildings with the same street address is fairly uncommon.

If the method is not able to locate a Building that matches the address in Meraki, the Meraki device will be ignored
by the audit and the missing device, along with its address, will be available in the ``missing_buildings`` attribute
of the :py:class:`MerakiAuditResults` that is returned by the :py:meth:`redsky_audit()`. This Building will likely need to be
added manually to RedSky, or the address corrected in Meraki.

.. note::

    The :py:meth:`wxcadm.redsky.RedSky.add_building()` method could be used to automatically add the Building, but this
    is not done automatically by the audit method.

Connecting to Meraki
====================
To begin, you must first establish a connection to the Meraki Dashboard using the :py:class:`Meraki` class within
**wxcadm**. To do this, you will need your Meraki Dashboard API token. You will also need to know the Network name that
you want to perform the audit on, and, if your API token has access to more than one Meraki Organization, you should
know the name of the Organization.

Access to Only One Meraki Org
-----------------------------
When you only have access to a single Meraki Organization, the :py:meth:`Meraki.get_orgs()` method will return a list
with only on element. You can use index 0 to access the Org and retrieve its Networks.

.. code-block:: python

    import wxcadm

    meraki = wxcadm.Meraki("Your API access token")
    orgs = meraki.get_orgs()
    my_org = orgs[0]

Access to More Than One Meraki Org
----------------------------------
If your token has access to more than one Meraki Organization, the :py:meth:`Meraki.get_org_by_name()` method provides
and easy way to return only the :py:class:`MerakiOrg` you are trying to audit.

.. note::

    This method can also be used when the token has access to a single Meraki Organization as long as the Organization
    name is known. This is the recommended approach to ensure the script continues to work even if a user is granted
    access to additional Organizations.

.. code-block:: python

    import wxcadm

    meraki = wxcadm.Meraki("Your API access token")
    my_org = meraki.get_org_by_name("Your Meraki Organization name)

Selecting the Meraki Network
============================
In order to run the audit, which runs across an entire Meraki Network, you must select the Network. The Network name
must be known in order to access it.

.. code-block:: python

    my_network = my_org.get_network_by_name("Your Meraki Network name")

Attaching RedSky to the Meraki Network
======================================
Once the Meraki Network has been selected, the RedSky instance must be attached to it so that the audit method is able
to read/write RedSky data. There are multiple ways to accomplish this, but the recommended method is to pass the RedSky
admin username and password to the :py:meth:`MerakiNetwork.attach_redsky()` method.

.. code-block:: python

    my_network.attach_redsky(username="Your RedSky username", password="Your RedSky password")

Running the Audit
=================
Now that the Network has been selected and RedSky attached, the audit can be run. In "normal" audit mode, **wxcadm**
will make changes to RedSky when it sees something that needs fixed. This includes adding locations, adding LLDP
mapping, adding BSSID mapping, and making changes to existing devices' locations. **wxcadm** also supports an
audit in ``simulated=True`` mode where no changes are made to the RedSky system. The results of the audit are
available in the :py:class:`MerakiAuditResults` returned from the :py:meth:`MerakiNetwork.redsky_audit()`.

Simulated Mode
--------------
To run the audit in Simulated Mode, simply pass ``simulated=True`` to the ``redsky_audit()`` method.

.. code-block:: python

    audit_results = my_network.redsky_audit(simulated=True)
    # The audit will take some time to run. When completed, the MerakiAuditResults can be accessed
    print(audit_results)

Normal (Live Change) Mode
-------------------------
When run without ``simulated=True``, changes will be made directly to RedSky

.. code-block:: python

    audit_results = my_network.redsky_audit()
    # The audit will take some time to run. When completed, the MerakiAuditResults can be accessed
    print(audit_results)

Putting it All Together
=======================
The following is the complete script:

.. code-block:: python

    import wxcadm

    meraki = wxcadm.Meraki("Your API access token")
    my_org = meraki.get_org_by_name("Your Meraki Org name")
    my_network = my_org.get_network_by_name("Your Meraki Network name")
    my_network.attach_redsky(username="Your RedSky username", password="Your RedSky password")
    audit_results = my_network.redsky_audit()
    print(audit_results)


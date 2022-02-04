.. py:currentmodule:: wxcadm

===================
Working with RedSky
===================

Because RedSky powers the E911 capability of Webex Calling, Webex Calling admins often find themselves needing to access
both systems. This happens when adding new Locations in Webex, when enabling RedSky E911 service on existing
locations, or when adding devices. **wxcadm** provides the :class:`RedSky` class in order to interface with the RedSky
APIs.

Before You Begin
================
Since the RedSky portal and Webex do not share user accounts, you will need a RedSky account and a user configured as an
"Organization Administrator" in RedSky Horizon. Starting a connection to RedSky with the :class:`RedSky` class
requires the username and password for the administrator.

Getting Connected
=================
To connect to RedSky, make sure you import the :class:`RedSky` class from **wxcadm**. Then initialize a
:class:`RedSky` instance, passing it the username and password of your administrator account.

.. code-block:: python

    from wxcadm import Webex, RedSky

    username = "admin@domain.com"
    password = "Your admin password"

    redsky = RedSky(username, password)

At that point, you are ready to use the methods within the :class:`RedSky` class. Some methods will automatically
create :class:`RedSkyBuilding` and :class:`RedSkyLocation` instances, which have their own properties and methods.

Network Discovery and Wire-Mapping
==================================
One of the most powerful features of RedSky is its ability to determine the user/device location based on network
connectivity. RedSky supports MAC address, LLDP Chassis/Port, WiFi BSSID, and IP Range mapping. The :class:`RedSky`
class offers methods to retrieve the current mapping as well as methods to add new mapping.

Although the decision regarding how to map a network is up to each customer, LLDP and BSSID are probably the most
definitive way to determine a user location. When a wired device is plugged into an ethernet port, the switch chassis
and port are specific to the location. When a device connects to WiFi, the BSSID of the AP is (usually) specific enough
to determine the user's location.

The following shows how to retrieve all of the mapping:

.. code-block:: python

    from wxcadm import RedSky
    redsky = RedSky("admin@domain.com", "Your admin password")

    mac_mapping = redsky.get_mac_discovery()
    lldp_mapping = redsky.get_lldp_discovbery()
    bssid_mapping = redsky.get_bssid_discovery()
    ip_discovery = redsky.get_ip_range_discovery()


Adding Network Discovery Mappings
---------------------------------
The :meth:`RedSky.add_mac_discovery()`, :meth:`RedSky.add_lldp_discovery()`, :meth:`RedSky.add_bssid_discovery()` and
:meth:`RedSky.add_ip_range_discovery()` methods are provided to allow a mapping of each type to be added to RedSky. See
the method reference for each in the :class:`RedSky` class to determine the parameters needed for each type. The
following is an example of how to add a MAC address mapping. Other mapping types can be done in a similar way.

.. code-block:: python

    from wxcadm import RedSky
    redsky = RedSky("admin@domain.com", "Your admin password")

    # First, you will need to get the RedSkyLocation instance you want to add to
    # Start by finding the building
    building = resky.get_building_by_name("Building Name")
    # Then find the location by name
    location = building.get_location_by_name("Location Name")

    # Then call the add_mac_discovery() method
    mapping = redsky.add_mac_discovery(mac="70:02:B4:77:25:F8", location=location, description="User Phone")
    # The mapping var now holds a dictionary of the full entry in RedSky
    print(mapping)

Deleting Network Discovery Mapping
----------------------------------
Because deleting a mapping can affect E911 calls, **wxcadm** doesn't supply any methods (yet) to perform deletes. These
should still be done in the RedSky Horizon portal directly. These methods may be added at some time, but most admins
rarely need to delete in bulk.
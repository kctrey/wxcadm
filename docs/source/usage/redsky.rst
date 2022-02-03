.. py:currentmodule:: wxcadm

===================
Working with RedSky
===================

Because RedSky powers the E911 capability of Webex Calling, Webex Calling admins often find themselves needing to access
both systems. This happens when adding new Locations in Webex, or when enabling RedSky E911 service on existing
locations. **wxcadm** provides the :class:`RedSky` class in order to interface with the RedSky APIs.

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
create :class:`RedSkyBuilding` and :class:`RedSkyLocation` instances, which have their own propertied and methods.


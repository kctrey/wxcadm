.. wxcadm documentation master file, created by
   sphinx-quickstart on Thu Jan 13 13:49:27 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

====================
wxcadm Documentation
====================
Welcome to the documentation home of **wxcadm**, a Python 3 library to simplify the API calls to Webex in order to
manage and report on users of Webex Calling.

Although the primary focus is Webex Calling, many of the other Webex admin functions are included. This library is not
meant to be an interface to the Meetings and Messaging capabilities of Webex....there are plenty of other modules that
provide that.

Status
======
The current version in this branch is mostly complete. All the Webex Calling related functions and classes work.

There are still some enhancements being made so pulling a fresh copy will likely give you some additional capabilities.
The current focus is on the XSI API and the features that are available with that. Some of the most useful XSI methods
are already supported, with more being added regularly.

.. include:: usage/quickstart.rst

Regarding Multiple Organizations
================================
Most Webex admins only have access to a single Org, but Webex does allow a single admin to manage multiple Orgs. When
the Webex instance is created, it creates the ``org`` attribute when only one Org is present. If there are mutliple, the
``orgs`` attribute contains a list of all the Orgs. ``orgs`` is created whether there is one Org or multiple, so
``Webex.org`` is equivalent to ``Webex.orgs[0]``. For example:

.. code-block:: python

   from wxcadm import Webex

   access_token = "Your API Access Token"
   webex = Webex(access_token)
   for org in webex.orgs:
       print(org.name)

It is recommended to take action on only one Org at a time, although the design allows for more flexibility. For
example, to enable VM-to-Email across all users of every Org, the following is supported:

.. code-block:: python

   for org in webex.orgs:
       for person in org.people:
           person.enable_vm_to_email()


The ``get_org_by_name()`` method is provided to allow the selection of the desired org by name.

.. code-block:: python

   my_org = webex.get_org_by_name("My Company")
   for people in my_org.people:
       person.enable_vm_to_email()

.. include:: usage/documentation.rst

Logging
=======
By default, the module logs to ``wxcadm.log``. At the moment, the logs just show the various methods that are invoked
for API calls to the Webex API.

Data Structure Note
===================
At the moment, the module works in two ways. In one way, it populates attributes based on the data from Webex. In
another, it stores the JSON representation directly from Webex. The latter is very handy for pushing data back to
Webex, but it requires some knowledge of the API structure, and doesn't abstract it well. Not to mention that the
Webex API doesn't do anything in a standard way.

The purpose of this module is to simplify that so the user doesn't have to have detailed knowledge of the Webex API, so
we are faced with a decision: keep the flexibility provided by the raw data or simplify it, at the cost of compatibility
when the Webex API is changed.

My goal is to find a happy medium, where the attributes get populated dynamically, but I feel that it is going to be a
heavy lift, changing the structure of all the classes and building a lot of "helper" functions to convert between
the two. Stay tuned...

.. toctree::
   :maxdepth: 2
   :caption: Usage:

   usage/installation
   usage/quickstart
   usage/documentation
   usage/xsi

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/Webex
   reference/Org
   reference/Location
   reference/Person

.. toctree::
   :maxdepth: 2
   :caption: XSI Reference

   reference/XSI
   reference/Call

.. toctree::
   :maxdepth: 1
   :caption: Full Reference

   reference/wxcadm



Indexes and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

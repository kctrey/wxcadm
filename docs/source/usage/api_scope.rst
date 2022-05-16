About API Scopes
================
Most of the API calls that the **wxcadm** methods use are supported by the "public" Webex API found at
`developer.webex.com <https://developer.webex.com.>`_. The 12-hour token that can be obtained by logging in there
includes all of the necessary scopes to perform all of the API calls that **wxcadm** supports. As mentioned in the
Getting Started with XSI section, you need to have XSI enabled for your Org, however.

Integrations
------------
The 12-hour token from `developer.webex.com`_ is useful for testing, and for running
one-time scripts, but logging in every 12 hours isn't feasible for a full-featured middleware that provides
administrative access to Webex, such as a bot or management portal. To obtain a longer-lived token, which also
includes a refresh token to make the access permanent, a developer should create an
`Integration <https://developer.webex.com/docs/integrations>`_. As specified in the developer documentation, an
Integration must includes the authorization scopes that are required to perform all of the specified functions.
Where possible, this documentation lists the required scopes for each method or property, however an Integration created
with the following scopes should have access to nearly everything that **wxcadm** can do:

- spark-admin:resource_groups_read
- analytics:read_all
- spark-admin:people_write
- spark-admin:organizations_read
- spark-admin:workspace_metrics_read
- spark-admin:places_read
- spark-admin:devices_read
- spark-admin:workspace_locations_write
- spark-admin:telephony_config_read
- spark-admin:telephony_config_write
- spark-admin:devices_write
- spark-admin:workspaces_write
- spark:calls_write
- spark-admin:roles_read
- spark-admin:xsi
- spark-admin:workspace_locations_read
- spark-admin:workspaces_read
- spark-admin:resource_group_memberships_read
- spark-admin:resource_group_memberships_write
- spark-admin:call_qualities_read
- spark:kms
- audit:events_read
- spark-admin:places_write
- spark-admin:licenses_read
- spark-admin:people_read
- spark:xsi (if enabled)

Note that not all of these are required for all functions, but this provides access to almost all of the functions
that **wxcadm** supports.

The CP-API
----------
In some cases, the public Webex API does not provide the full functionality available in Webex Control Hub. Cisco
continues to enhance the Webex API, but, for operations that are not yet available via that API, **wxcadm** also takes
advantage of the CP-API, which is the API that is used by Webex Control Hub directly.

Unfortunately, the authorization
scopes required by the CP-API are different than the scopes that can be defined for an Integration. In these cases, the
only API Access Tokens that have the required scopes are the 12-hour token from developer.webex.com and the "native"
Control Hub token that is used when signing into Control Hub.

Methods that require a token with the CP-API scope are noted in the documentation with the following:

.. warning::

    This method or attribute requires the CP-API access scope.
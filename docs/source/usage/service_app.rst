Service Applications
====================
Service applications, formerly called Authorized Applications, provide a method for an external application to be
authorized to access a customer Webex Org without a user-based OAuth flow. These applications are useful for machine
accounts that need to be able to perform work in Webex on behalf of an Organization. The capabilities of a Service
Application are similar to the Integration method but do not require a web-based authentication by the Webex Admin each
time a token needs to be generated.

.. note::

    Some roles that are available to Inetegrations are not (yet) supported by Service Applications. For example, the
    ``analytics:read_all`` role, which is required for CDR reporting, is not supported by Service Applications at
    this time

Authorization Overview
----------------------
The Service Application flow requires work by two functional entities, the Developer and the Administrator.

The Developer creates the Service Application within Webex. As with Integrations, Service Applications
have a Application ID, a Client Secret, and a list of scopes. The Developer must have their own Webex Org to create the
Service Application within, which will have it's own OAuth token.

The Administrator is the person who authorizes the Service Application to make changes within their Webex Org.

If a company is deploying their own Service Application to make changes in their Webex Org, the Developer and the
Administrator may be within the same Webex Org. That is okay as these entities are functional in nature and the process
is the same.

Flow
....
1. Developer creates the Service Application in their Webex Org with the desired application name, contact information,
and authorization scopes. When the Application is created, the Application ID and Client Secret values should be stored,
because they will be used for future API calls to obtain an access token.

.. code-block:: python

    import wxcadm

    developer_access_token = "The Developer OAuth token"

    # Application information
    app_name = 'Developer App Unique Name'
    app_contact = 'help@developer.com'
    app_logo = 'https://pngimg.com/uploads/hacker/hacker_PNG6.png'
    # The developer also needs the list of scopes required for the app
    app_scopes = [
        'spark:people_read',
        'spark-admin:people_write',
        'spark:people_write',
        'spark:organizations_read',
        'spark-admin:licenses_read',
        'spark-admin:people_read'
    ]

    developer_webex = wxcadm.Webex(developer_access_token)

    new_app = developer_webex.org.applications.create_service_application(
        name = app_name,
        contact = app_contact,
        logo = app_logo,
        scopes = app_scopes
    )

    # Get the App ID and Client Secret value from the new_app dict
    print(f"App ID: {new_app['id']})
    print(f"Client Secret: {new_app['clientSecret']})   # Make sure this is stored somewhere you can use later

2. The developer takes the App ID and provides it to the Administrator, who then must authorize the Service Application
for use in their Webex Org

.. code-block:: python

    import wxcadm

    administrator_access_token = 'The Administrator OAuth Token'
    app_id = 'The App ID provided by the Developer'

    administrator_webex = wxcadm.Webex(administrator_access_token)
    # Get the Service Application by the App ID
    app = administrator_webex.org.applications.get_app_by_id(app_id)

    # Authorize the Service Application
    success = app.authorize()

    # The Administrator will also have to send their Org ID to the Developer
    print(f"My Org ID: {administrator_webex.org.id})

3. Once authorized, the Developer can obtain an OAuth token to access the Administrator's Org

.. code-block:: python

    import wxcadm

    developer_access_token = "The Developer OAuth token"
    app_id = "The App ID for the Service Application that was authorized"
    client_secret = "The Client Secret value for the Service Application, stored during creation"
    admin_org_id = "The 'My Org ID' value received from the Administrator"

    developer_webex = wxcadm.Webex(developer_access_token)

    # Get the Service Application by ID
    app = developer_webex.org.applications.get_app_by_id(app_id)

    # And get the token information for the Administrator Webex Org
    token_info = app.get_token(client_secret, admin_org_id)

4. The token_info dict will have the following keys. The values should be recorded securely and used as needed.
  * ``access_token``: The OAuth token to access the Administrator's Webex Org
  * ``expires_in``: The expiry timer of the access token
  * ``refresh_token``: The OAuth refresh token, needed to generate a new access token
  * ``refresh_token_expires_in``: The expiry timer of the refresh token
  * ``token_type``: The type of token. For a Service Application, this will be set to 'Bearer'

5. When the Developer needs to refresh the access token, the :py:meth:`wxcadm.org.applications.get_token_refresh()`
method can be used:

.. note::

    **wxcadm** provides this method to use the refresh token, but a Developer can also use the /v1/access_token
    directly, as they do with their own OAuth token. The method provided by **wxcadm** is provided for convenience.

.. code-block:: python

    import wxcadm

    developer_access_token = "The Developer OAuth token"
    app_id = "The App ID for the Service Application that was authorized"
    client_secret = "The Client Secret value for the Service Application, stored during creation"
    refresh_token = "The refresh_token value for the existing token"

    developer_webex = wxcadm.Webex(developer_access_token)

    # Get the Service Application by ID
    app = developer_webex.org.applications.get_app_by_id(app_id)

    # And get the token information for the Administrator Webex Org
    token_info = app.get_token_refresh(client_secret, refresh_token)

6. (Optional) If the Developer needs to update the Client Secret in case it was lost or compromised, the
:py:meth:`Applications.regenerate_client_secret()` method can be used.

.. code-block:: python

    import wxcadm

    developer_access_token = "The Developer OAuth token"
    app_id = "The App ID for the Service Application that was authorized"

    developer_webex = wxcadm.Webex(developer_access_token)

    # Get the Service Application by ID
    app = developer_webex.org.applications.get_app_by_id(app_id)

    # Reset the client_secret and store the value
    client_secret = app.regenerate_client_secret()

Conclusion
----------
For those with experience on the Developer side, it should be very clear that Service Applications can greatly simplify
the access flow for applications that need to make changes without a user logging in. Some examples of what can be
accomplished with Service Applications are:

* Routine audits of Calling-related data
* Data backups
* Middleware to automatically collect data from a source system and build it in Webex
* Call data collection for the Webex Org






    



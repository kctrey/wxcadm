The tests.py Script
===================
An example script, called ``tests.py`` can be found `here <https://github.com/kctrey/wxcadm/blob/main/tests.py>`_.

This script is primarily used when adding new methods to **wxcadm** in order to validate they work on a Webex Org. It is
useful for a new user in order to:

1. Check the validity of the Webex Access Token and
2. Get an idea of the performance of the Webex APIs with a given Org size

The script uses a ``.env`` file with a ``WEBEX_ACCESS_TOKEN = "Your API Access Token"`` entry in order to run. When run,
it performs some basic **wxcadm** checks, to ensure that the valid access token works, invalid access tokens are handled
correctly, and reports the Orgs that can be accessed with the token.

It then uses ``wxcadm.Webex.org[0]`` (probably the only Org in most cases) and selects a random Webex Calling user to
perform validation of all of the GET/PUT methods. No data is changed during these tests, as the script is simply
re-inserting configuration data that is already present.

.. warning::

    The script is not "pretty" and it's filled with try/except statements that you wouldn't use in a Production script.
    It provides testing functionality and a basic framework of functionality to learn about **wxcadm**.

The ``tests.py`` script also will valid whether XSI is available, and, if so, will subscribe to Org-level and
Person-level call events. If you are planning to use XSI Events, these tests may prove useful.
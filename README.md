# wxcadm
Python Library for Webex Calling Administration

# Purpose
wxcadm is a Python 3 library to simplify the API calls to Webex in order to manage and report on users of Webex Calling

# Status
This library was originally developed as a CLI utility with built-in functionalty. As more users began to use the command-line tool, it became clear that the real need was a library that could be used to develop various front-end tools.

If you are reading this now, you will find that there is a mix of old and new within the main branch. The existing wxcadm.py still works, using the "old" api calls functions.

The plan is to move everything to a common wxcadm.py library and recreate the CLI tool to show what is possible with the library. For now, WXC.py is the name of the new library, but that will change eventually.

# Quickstart
If you want to play around with the library as-is, it is full featred, but still a little disjointed. You will need both WXC.py and globals.py in order to do anything useful.

``` python
import globals
from WXC import Org

globals.initialize()
```

When the initialize is called, it will prompt for an API Token, which can be obtained from developer.webex.com

You will need that in order to do anything with the library. The WXC library looks in globals.headers for that.

``` python
org = Org()
```

At that point you have an Org object with all of the users in the organiztion. You can look at the public methods in WXC to see some useful things you can do.


# wxcadm
Python Command-Line Toolbox for Webex Calling Administrators

# Prerequisites
This script uses the [simple\_term\_menu](https://pypi.org/project/simple-term-menu/) package in Python 3. You will need to install it before running, because the wxcadm.py will fail without it.

Eventually, it would be nice to use the built-in curses package...

# Menu Structure
- People
  - Back to Main Menu
  - View List of People - Retrieves all of the People in the org in a multi-select list so that you can perform bulk actions on them
- Webex Calling
  - Back to Main Menu
  - VM Email Domain Report - Retrieves a list of all domains that Webex Calling users are forwarding copies of their VMs to and allows selection of a domain to get the list of users
  - Call Forwarding Destination Audit - Runs a report showing Business Continuity Forwarding destination countries only. **Will be enhanced soon**
  - Call Recording Report - Show all Webex Calling users with recording enabled, along with the external identifiers needed for the Dubber platform

# wxcadm
Python Command-Line Toolbox for Webex Calling Administrators

# Prerequisites
This script uses the [simple\_term\_menu](https://pypi.org/project/simple-term-menu/) package in Python 3. You will need to install it before running, because the wxcadm.py will fail without it. I am also using the [phonenumbers](https://pypi.org/project/phonenumbers/) library to parse Call Forward numbers. Hopefully this is only temporary until the API returns everything in a Global E.164 format.

## Installation
The script was designed, and only runs, with Python 3. To install the prerequisite packages, do the following:

```
sudo pip3 install simple_term_menu
sudo pip3 install phonenumbers
```

# Menu Structure
- People
  - Back to Main Menu
  - View List of People - Retrieves all of the People in the org in a multi-select list so that you can perform bulk actions on them
    - User Selection List
      - Back to People List
      - Enable VM to E-Mail - Change all selected user to enable sending a copy of all VMs to the e-mail address of the user
      - Disable VM to E-Mail - Change all selected users to disable sending a copy of all VMs to their e-mail
- Webex Calling
  - Back to Main Menu
  - VM Email Domain Report - Retrieves a list of all domains that Webex Calling users are forwarding copies of their VMs to and allows selection of a domain to get the list of users
  - Call Forwarding Destination Audit - Runs a report that audits all user Call Forwarding against a list of allowed or denied destination countries
  - Call Recording Report - Show all Webex Calling users with recording enabled, along with the external identifiers needed for the Dubber platform
- Locations
  - Back to Main Menu
  - List All Locations - Show a list of all locations and their address
  - Add a Location - Not supported yet
- Tool Config
  - Back to Main Menu
  - Set Call Forwarding Audit Mode - Set the mode (allow or deny) to be used to audit Call Forwarding destinations in the Webex Calling menu
  - Set Call Forwarding Audit Countries - Select the countires that are allowed or denied, based on Audit Mode, in the Call Forwarding Destination Audit
  - Show Call Forwarding Audit Config - Show the current Call Forwarding Destination Audit Mode and Countries
- Quit

# Caveats
There is still no good exception handling on the API calls. And the Webex APIs occasionally don't return data, so that will need to be added soon.

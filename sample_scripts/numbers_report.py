# numbers_report.py
#
# This script is used to report all of the numbers for an Organization.
# To use the script, simply pass your API Access Token as the only argument to the script

import sys
sys.path.append('../')
from wxcadm import Webex, Person

try:
    access_token = sys.argv[1]
except IndexError:
    print("You forgot to pass your API Access Token")
    quit()


webex = Webex(access_token)

for number in webex.org.numbers:
    if "number" in number:
        print(f"{number['number']},{number['location'].name},", end="")
        if "owner" in number:
            if isinstance(number['owner'], Person):
                print(f"{number['owner'].email}")
            else:
                print(f"{number['owner']['firstName']} {number['owner']['lastName']}")
        else:
            print("Unused")


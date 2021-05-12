#!/usr/bin/env python3

from simple_term_menu import TerminalMenu
import requests
import time
import globals
import phonenumbers

# Some colors for a pretty terminal output
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def main():
    main_menu_title = "  Main Menu\n"
    main_menu_items = ["People", "Webex Calling", "Locations", "Quit"]
    main_menu_exit = False
    main_menu = TerminalMenu(
            menu_entries = main_menu_items,
            title = main_menu_title,
            clear_screen = True
    )

    people_menu_title = "  People\n";
    people_menu_items = ["Back to Main Menu", "View List of People"]
    people_menu_back = False
    people_menu = TerminalMenu(
            menu_entries = people_menu_items,
            title = people_menu_title,
            clear_screen = True
    )

    locations_menu_title = "  Locations\n"
    locations_menu_items = ["Back to Main Menu", "List Locations", "Add a Location"]
    locations_menu_back = False
    locations_menu = TerminalMenu(
            menu_entries = locations_menu_items,
            title = locations_menu_title,
            clear_screen = True
    )

    wxc_menu_title = "  Webex Calling\n"
    wxc_menu_items = ['Back to Main Menu', 'VM Email Domain Report', 'Call Forwarding Destination Audit', 'Call Recording Report']
    wxc_menu_back = False
    wxc_menu = TerminalMenu(
            menu_entries = wxc_menu_items,
            title = wxc_menu_title,
            clear_screen = True
    )

    while not main_menu_exit:
        main_sel = main_menu.show()

        if main_sel == 0:
            while not people_menu_back:
                people_sel = people_menu.show()

                if people_sel == 0:
                    people_menu_back = True
                elif people_sel == 1:
                    showPeopleListMenu()
            people_menu_back = False
        elif main_sel == 1:
            while not wxc_menu_back:
                wxc_sel = wxc_menu.show()
                if wxc_sel == 0:
                    wxc_menu_back = True
                elif wxc_sel == 1:
                    showVmDomainReport()
                elif wxc_sel == 2:
                    showCallForwardingDestinationReport()
                elif wxc_sel == 3:
                    showRecordingReport()
            wxc_menu_back = False
        elif main_sel == 2:
            while not locations_menu_back:
                locations_sel = locations_menu.show()
                if locations_sel == 0:
                    locations_menu_back = True
                elif locations_sel == 1:
                    printLocations()
                    input("Press Enter to continue...")
                elif locations_sel == 2:
                    print("Sorry, that isn't supported yet.")
                    input("Press Enter to continue...")
            locations_menu_back = False
        elif main_sel == 3:
            main_menu_exit = True
            print("Quitting...")

def showVmDomainReport():
    print("Running report...\n")
    domain_report = {}
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers)
    people_list = r.json()

    for person in people_list['items']:
        r = requests.get(globals.url_base + 'v1/people/' + person['id'] + '/features/voicemail', headers=globals.headers)
        person_vm = r.json()
        domain = person_vm['emailCopyOfMessage']['emailId'].split('@')[1]
        if domain not in domain_report:
            domain_report[person_vm['emailCopyOfMessage']['emailId'].split('@')[1]] = []
        domain_report[person_vm['emailCopyOfMessage']['emailId'].split('@')[1]].append(person['displayName'])

    domain_menu_title = "  Email Domains - Select a Domain to View Details\n"
    domain_menu_items = list(domain_report)
    domain_menu_items.insert(0,"Back to Webex Calling menu")
    domain_menu_back = False
    domain_menu = TerminalMenu(
            menu_entries = domain_menu_items,
            title = domain_menu_title,
            clear_screen = True
    )

    while not domain_menu_back:
        domain_sel = domain_menu.show()
        if domain_sel == 0:
            domain_menu_back = True
        else:
            for user in domain_report[domain_menu_items[domain_sel]]:
                print(user)
            input("\nPress Enter to continue...")
    domain_menu_back = False

def showCallForwardingDestinationReport():
    print("Running report...\n")
    cf_report = {}
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers)
    people_list = r.json()
    country_codes = getCountryCodes()

    for person in people_list['items']:
        print(person['displayName']+ ": ", end='', flush=True)
        r = requests.get(globals.url_base + 'v1/people/' + person['id'] + '/features/callForwarding', headers=globals.headers)
        person_cf = r.json()
        if "destination" in person_cf['businessContinuity']:
            x = person_cf['businessContinuity']['destination']
            user_cc = str(phonenumbers.parse(x, "US")).split()[2]
            if country_codes[user_cc] == 'Chile':
                print(bcolors.WARNING + "Forwarded to", country_codes[user_cc], bcolors.ENDC, flush=True)
            elif country_codes[user_cc] == 'China':
                print(bcolors.FAIL + "Forwarded to", country_codes[user_cc], bcolors.ENDC, flush=True)
            else:
                print(bcolors.OKGREEN + "Forwarded to", country_codes[user_cc], bcolors.ENDC, flush=True)
        else:
            print("Not forwarded", flush=True)

    input("Press Enter to continue...")

def showRecordingReport():
    print("Running report...\n")
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers)
    people_list = r.json()
    for person in people_list['items']:
        r = requests.get(globals.url_base + 'v1/people/' + person['id'] + '/features/callRecording', headers=globals.headers)
        recording = r.json()
        if recording['enabled']:
            print(person['displayName'])
            print(f"\tRecord: {recording['record']}")
            print(f"\tService Provider: {recording['serviceProvider']}")
            print(f"\tExternal Group: {recording['externalGroup']}")
            print(f"\tExternal ID: {recording['externalIdentifier']}")
            print("=========================================================")

    input("\nPress Enter to continue...")


def showPeopleListMenu():
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers)
    people_list = r.json()
    people_list_items = ['Back to Main Menu']
    for person in people_list['items']:
        people_list_items.append(person['emails'][0])
    people_list_title = "  User List - Select to Change\n"
    people_list_back = False
    people_list_menu = TerminalMenu(
            menu_entries = people_list_items,
            title = people_list_title,
            clear_screen = True,
            multi_select = True
    )

    while not people_list_back:
        person_sel = people_list_menu.show()
        if person_sel[0] == 0:
            people_list_back = True
        else:
            email_list = []
            for selection in person_sel:
                email_list.append(people_list_items[selection])
            showPeopleChangeMenu(email_list)
    people_list_back = False

def showPeopleChangeMenu(user_list):
    menu_title = "  Change Selected Users\n"
    menu_items = ['Back to People List','Enable VM to E-Mail','Disable VM to Email']
    menu_back = False
    menu = TerminalMenu(
            menu_entries = menu_items,
            title = menu_title,
            clear_screen = True
    )

    while not menu_back:
        menu_sel = menu.show()
        if menu_sel == 0:
            menu_back = True
        elif menu_sel == 1:
            enableVmToEmail(user_list)
            input("Press Enter to continue....")
        elif menu_sel == 2:
            disableVmToEmail(user_list)
            input("Press Enter to continue....")
    menu_back = False


def enableVmToEmail(user_list):
    for user in user_list:
        print("Changing " + user + "...", end = '', flush=True)
        user_id = getIdByEmail(user)
        #print(user_id + "...", end='', flush=True)
        payload = {'emailCopyOfMessage': {'enabled': 'true', 'emailId': user}}
        r_change_vm = requests.put(globals.url_base + 'v1/people/' + user_id + '/features/voicemail', headers=globals.headers, json=payload)
        print("done", flush=True)


def disableVmToEmail(user_list):
    for user in user_list:
        print("Changing " + user + "...", end = '', flush=True)
        user_id = getIdByEmail(user)
        payload = {'emailCopyOfMessage': {'enabled': 'false', 'emailId': user}}
        r_change_vm = requests.put(globals.url_base + 'v1/people/' + user_id + '/features/voicemail', headers=globals.headers, json=payload)
        print("done", flush=True)


def getIdByEmail(email):
    payload = {'email': email}
    r = requests.get(globals.url_base + 'v1/people', params=payload, headers=globals.headers)
    user_response = r.json()
    user_id = user_response['items'][0]['id']
    return user_id


def getCountryCodes():
    import json

    country_codes = {}

    with open('country_codes.json') as json_file:
        data = json.load(json_file)

        for entry in data:
            cc = entry['dial_code'][1:]
            country_codes[cc] = entry['name']
    return country_codes

def printLocations():
    r = requests.get(globals.url_base + 'v1/locations', headers=globals.headers)
    location_list = r.json()
    for location in location_list['items']:
        print("Location Name: " + location['name'] + " (" + location['address']['country'] + ")")
        print("Address:")
        print("\t" + location['address']['address1'])
        if location['address']['address2']:
            print("\t" + location['address']['address2'])
        print("\t" + location['address']['city'] + ", " + location['address']['state'] + " " + location['address']['postalCode'])
        print("--------------------------------------------------------------")

if __name__ == "__main__":
    globals.initialize()
    main()

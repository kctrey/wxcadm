#!/usr/bin/env python3

from simple_term_menu import TerminalMenu
import time
import globals
import phonenumbers     # Needed for the Call Forwarding report
import api_calls
import json

debug = False

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
    # Main Menu
    main_menu_title = "  Main Menu\n"
    main_menu_items = ["People", "Webex Calling", "Locations", "Tool Config", "Quit"]
    main_menu_exit = False
    main_menu = TerminalMenu(
            menu_entries = main_menu_items,
            title = main_menu_title,
            clear_screen = True
    )

    # People Menu
    people_menu_title = "  People\n";
    people_menu_items = ["Back to Main Menu", "View List of People"]
    people_menu_back = False
    people_menu = TerminalMenu(
            menu_entries = people_menu_items,
            title = people_menu_title,
            clear_screen = True
    )

    # Locations Menu
    locations_menu_title = "  Locations\n"
    locations_menu_items = ["Back to Main Menu", "List Locations", "Add a Location"]
    locations_menu_back = False
    locations_menu = TerminalMenu(
            menu_entries = locations_menu_items,
            title = locations_menu_title,
            clear_screen = True
    )

    # Webex Calling Menu
    wxc_menu_title = "  Webex Calling\n"
    wxc_menu_items = ['Back to Main Menu', 'VM Email Domain Report', 'Call Forwarding Destination Audit', 'Call Recording Report', 'Enable VM to E-Mail for All Users', 'Show All Webex Calling Users']
    wxc_menu_back = False
    wxc_menu = TerminalMenu(
            menu_entries = wxc_menu_items,
            title = wxc_menu_title,
            clear_screen = True
    )

    # Config Menu
    config_menu_title = "  wxcadm Tool Config\n"
    config_menu_items = ['Back to Main Menu', 'Set Call Forwarding Audit Mode', 'Set Call Forwarding Audit Countries', 'Show Call Forwarding Audit Config']
    config_menu_back = False
    config_menu = TerminalMenu(
            menu_entries = config_menu_items,
            title = config_menu_title,
            clear_screen = True
    )

    while not main_menu_exit:   # As long as we haven't exited the main menu, we have work to do
        main_sel = main_menu.show()

        # The main menu loop, deciding which menu to show when
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
                    showCallForwardingDestinationAudit()
                elif wxc_sel == 3:
                    showRecordingReport()
                elif wxc_sel == 4:
                    setVmToEmailAll()
                elif wxc_sel == 5:
                    showWebexCallingUsers()
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
            while not config_menu_back:
                config_sel = config_menu.show()
                if config_sel == 0:
                    config_menu_back = True
                elif config_sel == 1:
                    setCallForwardingAuditMode()
                elif config_sel == 2:
                    print("This will reset your currently selected cuntries")
                    go = input("Type \'yes\' to continue. Anything else to cancel. ")
                    if go.lower() == 'yes':
                        showCountrySelectMenu()
                elif config_sel == 3:
                    showCallForwardingAuditConfig()
                    input("Press Enter to continue...")
            config_menu_back = False
        elif main_sel == 4:
            main_menu_exit = True
            print("Quitting...")

def showWebexCallingUsers():
    people_list = api_calls.wxc_people()
    for person in people_list['items']:
        print(person['displayName'], person['emails'][0])
    input("\nPress Enter to continue...")

def setVmToEmailAll():
    people_list = api_calls.wxc_people()
    for person in people_list['items']:
        print("Changing " + person['emails'][0] + "...", end = '', flush=True)
        api_calls.Person.Voicemail.set_email_copy(person['id'], person['emails'][0], 'enabled')
        print("done", flush=True)


def showCallForwardingAuditConfig():
    print("Audit Mode:", globals.config['forwarding_audit']['mode'])
    print("Countries:")
    print("\t", end='')
    print(*globals.config['forwarding_audit']['countries'], sep = "\n\t")


def setCallForwardingAuditMode():
    print("Set the Audit Mode for the Call Forwarding Audit\n")
    print("Set to 'allow' to only allow the defined countries as Forwarding destinations and report non-compliance on all others")
    print("Set to 'deny' to allow all countries other than the defined countries as Forwarding destinations")
    print("\n")
    print("Current Audit Mode:", globals.config['forwarding_audit']['mode'])
    print("\n")
    new_audit_mode = input("Enter the new Audit Mode (A)llow / (D)eny: ")

    if new_audit_mode[0].lower() == 'a':
        globals.config['forwarding_audit']['mode'] = 'allow'
    elif new_audit_mode[0].lower() == 'd':
        globals.config['forwarding_audit']['mode'] = 'deny'
    else:
        print("Invalid or no value. No changes.")

    with open("config.json", "w") as cf:
        json.dump(globals.config, cf)

def showCountrySelectMenu():
    # First we set up the menu with some base config
    country_menu_title = "  Select Countries for Call Forwarding Audit (Search with /)"
    country_menu_back = False
    country_menu_items = ['Back to Tool Config Menu \(No changes to current config\)']

    # Now read the contents of the country code file and get them added to the menu
    with open('country_codes.json', 'r') as ccf:
        countries = json.load(ccf)

    for country in countries:
        country_menu_items.append(country['name'])

    country_menu = TerminalMenu(
            menu_entries = country_menu_items,
            title = country_menu_title,
            clear_screen = True,
            multi_select = True,
    )

    while not country_menu_back:
        country_sel = country_menu.show()

        if country_sel[0] == 0:
            country_menu_back = True
        else:
            # Clear the existing selections
            #TODO Could probably improve this flow to allow them to add/delete countries from the existing list
            globals.config['forwarding_audit']['countries'].clear()
            globals.config['forwarding_audit']['countries'] = list(country_menu.chosen_menu_entries)

            with open("config.json", "w") as cf:
                json.dump(globals.config, cf)
            
            print("Saved Call Forwarding Audit config...\n")
            showCallForwardingAuditConfig()
            input("\nPress Enter to continue...")
            country_menu_back = True


def showVmDomainReport():
    print("Running report...\n")
    domain_report = {}      # Dict for report data

    # Get all of the people in the org into people_list
    people_list = api_calls.all_people()

    for person in people_list['items']:
        person_vm = api_calls.Person.voicemail_config(person['id'])
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

def showCallForwardingDestinationAudit():
    print("Running report...\n")

    # Set up a dict to store all of the audit info
    cf_report = {}
    cf_report['always'] = {}
    cf_report['always']['none'] = []
    cf_report['always']['compliant'] = []
    cf_report['always']['noncompliant'] = []
    cf_report['busy'] = {}
    cf_report['busy']['none'] = []
    cf_report['busy']['compliant'] = []
    cf_report['busy']['noncompliant'] = []
    cf_report['noAnswer'] = {}
    cf_report['noAnswer']['none'] = []
    cf_report['noAnswer']['compliant'] = []
    cf_report['noAnswer']['noncompliant'] = []

    people_list = api_calls.all_people()
    country_codes = getCountryCodes()

    for person in people_list['items']:
        if debug: print("User:", person['displayName'])

        # There are three different kinds of forwarding, so let's do each
        for mode in ['always', 'busy', 'noAnswer']:
            person_cf = api_calls.Person.call_forwarding(person['id'])
            if "destination" in person_cf['callForwarding'][mode]:
                if debug: print("Destination found: ", end='')
                cfdest = person_cf['callForwarding'][mode]['destination']
                user_cc = str(phonenumbers.parse(cfdest, "US")).split()[2]
                if debug: print(user_cc, country_codes[user_cc])
                # Handle Audit Mode = block first
                if globals.config['forwarding_audit']['mode'] == 'deny':
                    if country_codes[user_cc] in globals.config['forwarding_audit']['countries']:
                        if debug: print("Adding noncomplient")
                        cf_report[mode]['noncompliant'].append(person['emails'][0])
                    else:
                        if debug: print("Adding compliant")
                        cf_report[mode]['compliant'].append(person['emails'][0])
                elif globals.config['forwarding_audit']['mode'] == 'allow':
                    if country_codes[user_cc] in globals.config['forwarding_audit']['countries']:
                        if debug: print("Adding compliant")
                        cf_report[mode]['compliant'].append(person['emails'][0])
                    else:
                        if debug: print("Adding noncomplient")
                        cf_report[mode]['noncompliant'].append(person['emails'][0])
            else:
                cf_report[mode]['none'].append(person['emails'][0])
    print("Call Forwarding Destination Audit")
    print("Audit Mode:", globals.config['forwarding_audit']['mode'])
    print("Country List:", globals.config['forwarding_audit']['countries'])
    print()
    for mode in cf_report:
        print("Forwarding Mode:", mode)
        print("\tNo Forwarding:", len(cf_report[mode]['none']))
        print("\tCompliant:", len(cf_report[mode]['compliant']))
        print("\tNoncompliant:", len(cf_report[mode]['noncompliant']))
        if len(cf_report[mode]['noncompliant']) > 0:
            print("\t\tUsers: ", end='')
            print(*cf_report[mode]['noncompliant'], sep = ", ")
    input("\nPress Enter to continue...")

def showRecordingReport():
    print("Running report...\n")
    people_list = api_calls.all_people()
    for person in people_list['items']:
        recording = api_calls.Person.call_recording(person['id'])
        if recording['enabled']:
            print(person['displayName'])
            print(f"\tRecord: {recording['record']}")
            print(f"\tService Provider: {recording['serviceProvider']}")
            print(f"\tExternal Group: {recording['externalGroup']}")
            print(f"\tExternal ID: {recording['externalIdentifier']}")
            print("=========================================================")

    input("\nPress Enter to continue...")


def showPeopleListMenu():
    people_list = api_calls.all_people()
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
        user_id = api_calls.Person.id_by_email(user)
        api_calls.Person.Voicemail.set_email_copy(user_id, user, 'enabled')
        print("done", flush=True)


def disableVmToEmail(user_list):
    for user in user_list:
        print("Changing " + user + "...", end = '', flush=True)
        user_id = api_calls.Person.id_by_email(user)
        api_calls.Person.Voicemail.set_email_copy(user_id, user, 'disabled')
        print("done", flush=True)


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
    location_list = api_calls.all_locations()
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

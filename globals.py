import json
import api_calls

def initialize():
    global url_base
    url_base = 'https://webexapis.com/'

    global access_key
    access_key = input('Enter your API Access Key: ')

    bearer_token = 'Bearer ' + access_key

    global headers
    headers = {'Authorization': bearer_token}

    global config
    with open("config.json", "r") as fp:
        config = json.load(fp)

    # The user may admin more than one org, so we need to check for
    # that and see which org they are wanting to work with
    my_orgs = api_calls.my_orgs()
    num_orgs = len(my_orgs['items'])
    global org_id
    if num_orgs == 1:
        org_id = my_orgs['items'][0]['id']
    else:
        print("You have the ability to manage more than one Webex Orgnaization.")
        print("Enter the number of the Organization that you wish to manage in this session.")

        org_num = 0

        for org in my_orgs['items']:
            org_num += 1
            print(org_num, end = " - ")
            print(org['displayName'])

        sel_org = input("Enter the Organization number: ")
        print("\nPlease confirm you selected the correct Organization and type the word 'yes' to continue.\n")
        print("Selected:  " + my_orgs['items'][int(sel_org)-1]['displayName'])
        go = input("Continute? ")
        if go.lower() == 'yes':
            org_id = my_orgs['items'][int(sel_org)-1]['id']
        else:
            quit()

    global params
    params = {'orgId': org_id}

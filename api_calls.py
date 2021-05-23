import globals
import json
import requests
import os.path

def all_people():   # Return a dict of all people in the org
    # https://developer.webex.com/docs/api/v1/people/list-people

    # First check to see if we are allowed to cache the people in this session
    # and grab the cached valus if we have them
    if globals.cache_session:
        # Check for cache file
        if os.path.isfile('session_cache/' + str(globals.session_id) + '.people'):
            with open('session_cache/' + str(globals.session_id) + '.people', 'r') as scf:
                people_list = json.load(scf)
                return(people_list)
    
    foo = {'max': '1000'}
    params = {**foo, **globals.params}
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers, params=params)
    people_list = r.json()

    if 'next' in r.links:
        print("Getting people. For large organizations, this may take a while", end='', flush=True)
        # Tome to deal with pagination
        keep_going = True
        next_url = r.links['next']['url']
        while keep_going == True:
            print(".", end='', flush=True)
            r2 = requests.get(next_url, headers=globals.headers)
            new_people = r2.json()
            if 'items' not in new_people:
                continue
            people_list['items'].extend(new_people['items'])
            if 'next' not in r2.links:
                keep_going = False
                print()
            else:
                next_url = r2.links['next']['url']

    # Save the people_list to cache if configured that way
    if globals.cache_session:
        with open('session_cache/' + str(globals.session_id) + '.people', 'w') as scf:
            json.dump(people_list, scf)

    return(people_list)

def wxc_people():
    wxc_people = {}
    wxc_people['items'] = []

    wxc_license = None
    r = requests.get(globals.url_base + 'v1/licenses', headers=globals.headers, params=globals.params)
    license_list = r.json()
    for license in license_list['items']:
        if license['name'] == 'Webex Calling - Standard Enterprise' or license['name'] == 'Webex Calling SP - Standard Enterprise':
            wxc_license = license['id']

    if not wxc_license:
        print("Something is wrong. There are no Webex Calling - Standard Enterprise licenses in your organization.")
        input("\nPress Enter to continue...")

    people_list = all_people()
    for person in people_list['items']:
        if wxc_license in person['licenses']:
            person_copy = person.copy()
            wxc_people['items'].append(person_copy)

    return(wxc_people)


def all_locations():    # Return a dict of all locations within the org
    # https://developer.webex.com/docs/api/v1/locations/list-locations
    r = requests.get(globals.url_base + 'v1/locations', headers=globals.headers, params=globals.params)
    location_list = r.json()
    return(location_list)


def my_orgs():  # Return a dict of all of the orgs this user can manage, or is a part of
    # https://developer.webex.com/docs/api/v1/organizations/list-organizations
    r = requests.get(globals.url_base + 'v1/organizations', headers=globals.headers)
    my_orgs = r.json()
    return(my_orgs)

class Person:
    def id_by_email(email): # Return the person_id of the user with the provided email
        # https://developer.webex.com/docs/api/v1/people/list-people
        foo = {'email': email}
        params = {**foo, **globals.params}
        r = requests.get(globals.url_base + 'v1/people', params=params, headers=globals.headers)
        user_resp = r.json()
        user_id = user_resp['items'][0]['id']
        return(user_id)

    def call_forwarding(person_id):
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-forwarding-settings-for-a-person
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/callForwarding', headers=globals.headers, params=globals.params)
        person_cf = r.json()
        return(person_cf)


    #TODO Move this to the Voicemail class
    def voicemail_config(person_id):
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-voicemail-settings-for-a-person
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/voicemail', headers=globals.headers, params=globals.params)
        voicemail_config = r.json()
        return(voicemail_config)


    def call_recording(person_id):
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-call-recording-settings-for-a-person
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/callRecording', headers=globals.headers, params=globals.params)
        call_recording = r.json()
        return(call_recording)

    class Voicemail:
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-voicemail-settings-for-a-person
        def set_email_copy(person_id, email, enabled='enabled'):    # Assume we are being asked to enable it unless told differently
            payload = {'emailCopyOfMessage': {'emailId': email}}
            if enabled == 'enabled':
                payload['emailCopyOfMessage']['enabled'] = 'true'
            elif enabled == 'disabled':
                payload['emailCopyOfMessage']['enabled'] = 'false'

            r = requests.put(globals.url_base + 'v1/people/' + person_id + '/features/voicemail', headers=globals.headers, params=globals.params, json=payload)
            return(True)

            

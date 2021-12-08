import globals
import json
import requests
import os.path
import logging

def all_people():   # Return a dict of all people in the org
    # https://developer.webex.com/docs/api/v1/people/list-people

    # First check to see if we are allowed to cache the people in this session
    # and grab the cached valus if we have them
    logging.info("all_people() started")
    if globals.cache_session:
        # Check for cache file
        logging.info("Cache enabled. Checking for cache file")
        if os.path.isfile('session_cache/' + str(globals.session_id) + '.people'):
            logging.info("Cache found. Using cached values")
            with open('session_cache/' + str(globals.session_id) + '.people', 'r') as scf:
                people_list = json.load(scf)
                return(people_list)
    
    logging.info("No cache file found. Collecting people.")
    foo = {'max': '1000'}
    params = {**foo, **globals.params}
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers, params=params)
    people_list = r.json()

    if 'next' in r.links:
        print("Getting people. For large organizations, this may take a while", end='', flush=True)
        # Time to deal with pagination
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
        logging.info("Cache enabled. Writing .people cache")
        with open('session_cache/' + str(globals.session_id) + '.people', 'w') as scf:
            json.dump(people_list, scf)

    return(people_list)

def wxc_people():
    logging.info("wxc_people() started")
    wxc_people = {}
    wxc_people['items'] = []

    wxc_licenses = []

    logging.info("Collecting licenses")

    r = requests.get(globals.url_base + 'v1/licenses', headers=globals.headers, params=globals.params)
    license_list = r.json()
    for license in license_list['items']:
        logging.debug(f"Found license: {license['name']}")
        if "Webex Calling" in license['name']:
            logging.debug(f"{license['name']} is a Webex Calling license")
            wxc_licenses.append(license['id'])

    if not wxc_licenses:
        logging.warn("No Webex Calling licenses found")
        print("Something is wrong. There are no Webex Calling licenses in your organization.")
        input("\nPress Enter to continue...")

    people_list = all_people()
    for person in people_list['items']:
        logging.debug(f"Checking licenses for {person['emails'][0]}")
        for license in person['licenses']:
            if license in wxc_licenses:
                logging.debug(f"License found")
                person_copy = person.copy()
                wxc_people['items'].append(person_copy)

    return(wxc_people)


def all_locations():    # Return a dict of all locations within the org
    # https://developer.webex.com/docs/api/v1/locations/list-locations
    logging.info("all_locations() started")
    r = requests.get(globals.url_base + 'v1/locations', headers=globals.headers, params=globals.params)
    location_list = r.json()
    return(location_list)


def my_orgs():  # Return a dict of all of the orgs this user can manage, or is a part of
    # https://developer.webex.com/docs/api/v1/organizations/list-organizations
    logging.info("my_orgs() started")
    r = requests.get(globals.url_base + 'v1/organizations', headers=globals.headers)
    my_orgs = r.json()
    return(my_orgs)

class XSI:
    def actions_endpoint():
        params = {"callingData": "true"}
        r = requests.get(globals.url_base + 'v1/organizations/' + globals.org_id, headers=globals.headers, params=params)
        response = r.json()
        actions_endpoint = response['xsiActionsEndpoint']
        return(actions_endpoint)
    def events_endpoint():
        params = {"callingData": "true"}
        r = requests.get(globals.url_base + 'v1/organizations/' + globals.org_id, headers=globals.headers, params=params)
        response = r.json()
        events_endpoint = response['xsiEventsEndpoint']
        return(events_endpoint)
    def events_channel_endpoint():
        params = {"callingData": "true"}
        r = requests.get(globals.url_base + 'v1/organizations/' + globals.org_id, headers=globals.headers, params=params)
        response = r.json()
        events_channel_endpoint = response['xsiEventsChannelEndpoint']
        return(events_channel_endpoint)

class Person:
    def id_by_email(email): # Return the person_id of the user with the provided email
        # https://developer.webex.com/docs/api/v1/people/list-people
        logging.info("id_by_email() started")
        foo = {'email': email}
        params = {**foo, **globals.params}
        r = requests.get(globals.url_base + 'v1/people', params=params, headers=globals.headers)
        user_resp = r.json()
        user_id = user_resp['items'][0]['id']
        return(user_id)

    def call_forwarding(person_id):
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-forwarding-settings-for-a-person
        logging.info("call_forwarding() started")
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/callForwarding', headers=globals.headers, params=globals.params)
        person_cf = r.json()
        return(person_cf)

    #TODO Move this to the Voicemail class
    def voicemail_config(person_id):
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-voicemail-settings-for-a-person
        logging.info("voicemail_config() started")
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/voicemail', headers=globals.headers, params=globals.params)
        voicemail_config = r.json()
        return(voicemail_config)

    def call_recording(person_id):
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-call-recording-settings-for-a-person
        logging.info("call_recording() started")
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/callRecording', headers=globals.headers, params=globals.params)
        call_recording = r.json()
        return(call_recording)

    def set_barge_in(person_id, enabled='enabled', tone='disabled'):
        logging.info(f"set_barge_in(enabled={enabled}, tone={tone}) started")
        if enabled == 'enabled':
            payload = {'enabled': 'true'}
            if tone == 'enabled':
                payload['toneEnabled'] = 'true'
            elif tone == 'disabled':
                payload['toneEnabled'] = 'false'
        elif enabled == 'diasabled':
            payload = {'enabled': 'false'}

        r = requests.put(globals.url_base + 'v1/people/' + person_id + '/features/bargeIn', headers=globals.headers, params=globals.params, json=payload)
        return(True)

    class Voicemail:
        # https://developer.webex.com/docs/api/v1/webex-calling-person-settings/read-voicemail-settings-for-a-person
        def set_email_copy(person_id, email, enabled='enabled'):    # Assume we are being asked to enable it unless told differently
            logging.info("set_email_copy() started")
            payload = {'emailCopyOfMessage': {'emailId': email}}
            if enabled == 'enabled':
                payload['emailCopyOfMessage']['enabled'] = 'true'
            elif enabled == 'disabled':
                payload['emailCopyOfMessage']['enabled'] = 'false'

            r = requests.put(globals.url_base + 'v1/people/' + person_id + '/features/voicemail', headers=globals.headers, params=globals.params, json=payload)
            if r.status_code == 200 or r.status_code == 204:
                return(True)
            else:
                return(False)


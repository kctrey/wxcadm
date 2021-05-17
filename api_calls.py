import globals
import requests

def all_people():   # Return a dict of all people in the org
    # https://developer.webex.com/docs/api/v1/people/list-people
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers, params=globals.params)
    people_list = r.json()
    return(people_list)

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

            

import globals
import requests

def all_people():
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers, params=globals.params)
    people_list = r.json()
    return(people_list)

def all_locations():
    r = requests.get(globals.url_base + 'v1/locations', headers=globals.headers, params=globals.params)
    location_list = r.json()
    return(location_list)


def my_orgs():
    r = requests.get(globals.url_base + 'v1/organizations', headers=globals.headers)
    my_orgs = r.json()
    return(my_orgs)

class Person:
    def id_by_email(email):
        foo = {'email': email}
        params = {**foo, **globals.params}
        r = requests.get(globals.url_base + 'v1/people', params=params, headers=globals.headers)
        user_resp = r.json()
        user_id = user_resp['items'][0]['id']
        return(user_id)

    def call_forwarding(person_id):
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/callForwarding', headers=globals.headers, params=globals.params)
        person_cf = r.json()
        return(person_cf)


    #TODO Move this to the Voicemail class
    def voicemail_config(person_id):
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/voicemail', headers=globals.headers, params=globals.params)
        voicemail_config = r.json()
        return(voicemail_config)


    def call_recording(person_id):
        r = requests.get(globals.url_base + 'v1/people/' + person_id + '/features/callRecording', headers=globals.headers, params=globals.params)
        call_recording = r.json()
        return(call_recording)

    class Voicemail:
        def set_email_copy(person_id, email, enabled='enabled'):    # Assume we are being asked to enable it unless told differently
            payload = {'emailCopyOfMessage': {'emailId': email}}
            if enabled == 'enabled':
                payload['emailCopyOfMessage']['enabled'] = 'true'
            elif enabled == 'disabled':
                payload['emailCopyOfMessage']['enabled'] = 'false'

            r = requests.put(globals.url_base + 'v1/people/' + person_id + '/features/voicemail', headers=globals.headers, params=globals.params, json=payload)
            return(True)

            

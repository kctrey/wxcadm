import globals
import requests

def all_people():
    r = requests.get(globals.url_base + 'v1/people', headers=globals.headers)
    people_list = r.json()

    return(people_list)



import json

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


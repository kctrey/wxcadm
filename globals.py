import json
import uuid
import logging

def initialize():
    # Set up logging
    logging.basicConfig(level=logging.INFO, filename='logfile.log', format='%(asctime)s %(module)s:%(levelname)s:%(message)s')
    # Allow cache for People data. Really speeds things up if you have a large enterprise
    global cache_session
    cache_session = True
    if cache_session:
        global session_id
        session_id = uuid.uuid4()
    
    global config
    with open("config.json", "r") as fp:
        config = json.load(fp)
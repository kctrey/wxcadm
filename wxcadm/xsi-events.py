import requests
from threading import Thread, Event
import uuid
import queue
import re
import logging
import time
import xmltodict

logging.basicConfig(level=logging.INFO,
                    filename="./xsi.log",
                    format='%(asctime)s %(module)s:%(levelname)s:%(message)s')

channel_url = "https://api-rialto.broadcloudpbx.com/com.broadsoft.async/com.broadsoft.xsi-events/v2.0/channel"
events_url = 'https://api-rialto.broadcloudpbx.com/com.broadsoft.xsi-events'
access_token = "MDUwYjU2MGUtN2VlZS00NjkxLWEzZGUtYzk2YmJhNzkwZDNmMWNjZDQzZTgtMmNl_PF84_3db310ec-63fa-4bc3-9438-1b5a35388b64"
headers = {"Authorization": f"Bearer {access_token}",
           "Content-Type": "application/xml; charset=UTF-8"}


channel_set_id = ""
channel_id = ""

def send_heartbeats(channel: str):
    global channel_id
    while channel_id:
        logging.debug(f"Sending heartbeat for channel: {channel}")
        session = requests.Session()
        session.headers.update(headers)
        r = session.put(events_url + f"/v2.0/channel/{channel}/heartbeat", headers=headers)
        if r.ok:
            logging.debug("Heartbeat successful")
        else:
            logging.debug(f"Heartbeat failed: {r.text}")
        # Send a heartbeat every 15 seconds
        time.sleep(15)
    return True

def start_channel(messages_in):
    global channel_set_id
    channel_set_id = uuid.uuid4()
    logging.info(f"Channel Set ID: {channel_set_id}")
    payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
              '<Channel xmlns=\"http://schema.broadsoft.com/xsi\">' \
              f'<channelSetId>{channel_set_id}</channelSetId>' \
              '<priority>1</priority>' \
              '<weight>50</weight>' \
              '<expires>300</expires>' \
              '</Channel>'

    logging.debug("Sending request")

    r = requests.post(channel_url, headers=headers, data=payload, stream=True)
    logging.info(f"Headers: {r.headers}")
    logging.info(f"Cookies: {r.cookies}")
    chars = ""
    for char in r.iter_content():
        decoded_char = char.decode('utf-8')
        chars += decoded_char
        #logging.info(chars)
        if "</Channel>" in chars:
            m = re.search("<channelId>(.+)<\/channelId>", chars)
            global channel_id
            channel_id = m.group(1)
            chars = ""
        if "<ChannelHeartBeat xmlns=\"http://schema.broadsoft.com/xsi\"/>" in chars:
            logging.debug("Heartbeat received on channel")
            chars = ""
        if "</xsi:Event>" in chars:
            event = chars
            logging.debug(f"Full Event: {event}")
            message_dict = xmltodict.parse(event)
            messages_in.put(message_dict)
            # Reset ready for new message
            chars = ""
            ack_event(message_dict['xsi:Event']['xsi:eventID'], r.cookies)
        if decoded_char == "\n":
            #logging.info(chars)
            chars = ""

def ack_event(event_id: str, cookies):
    payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
              '<EventResponse xmlns=\"http://schema.broadsoft.com/xsi\">' \
              f'<eventID>{event_id}</eventID>' \
              '<statusCode>200</statusCode>' \
              '<reason>OK</reason>' \
              '</EventResponse>'
    logging.debug(f"Acking event: {event_id}")
    r = requests.post(events_url + "/v2.0/channel/eventresponse", headers=headers, data=payload, cookies=cookies)
    return True

def refresh_channel():
    global channel_id
    payload = "<Channel xmlns=\"http://schema.broadsoft.com/xsi\"><expires>300</expires></Channel>"
    r = requests.put(events_url + f"/v2.0/channel/{channel_id}", headers=headers, data=payload)

def subscribe(event: str):
    global channel_set_id
    enterprise = 'WMYWE170606'
    logging.info(f"Subscribing to: {event} for {enterprise} on channel set {channel_set_id}")
    payload = '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n' \
              '<Subscription xmlns=\"http://schema.broadsoft.com/xsi\">' \
              f'<event>{event}</event>' \
              f'<expires>300</expires><channelSetId>{channel_set_id}</channelSetId>' \
              '<applicationId>wxcadm</applicationId></Subscription>'
    r = requests.post(events_url + f"/v2.0/serviceprovider/{enterprise}", headers=headers, data=payload)
    if r.ok:
        response_dict = xmltodict.parse(r.text)
        subscription_id = response_dict['Subscription']['subscriptionId']
        logging.debug(f"Subscription ID: {subscription_id}")
        return subscription_id
    else:
        return True

if __name__ == '__main__':
    messages_in = queue.Queue()
    actions = queue.Queue()
    logging.info("Starting thread")
    channel_thread = Thread(target=start_channel, args=[messages_in], daemon=True)
    channel_thread.start()
    logging.info("Thread started")
    # Give the channel a second or two to start
    time.sleep(2)
    heartbeat_thread = Thread(target=send_heartbeats, args=[channel_id], daemon=True)
    heartbeat_thread.start()
    call_sub = subscribe("Advanced Call")
    while True:
        message = messages_in.get()
        print(message)

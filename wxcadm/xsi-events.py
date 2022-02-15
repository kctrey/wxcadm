import asyncio
import requests

from aiocometd import Client, AuthExtension

channel_endpoint = "https://api-rialto.broadcloudpbx.com/com.broadsoft.async/com.broadsoft.xsi-events"
events_endpoint = "https://api-rialto.broadcloudpbx.com/com.broadsoft.xsi-events"

def xsi_subscribe(event_package):
    pass

async def events_channel():
    async with Client(channel_endpoint) as client:
        async for message in client:
            print(message)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(events_channel())







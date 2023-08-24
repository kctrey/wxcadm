from __future__ import annotations

import base64
import logging
import uuid
import time
import requests
import sys
from typing import Optional

from .exceptions import *
from wxcadm import log

__all__ = ['decode_spark_id', 'console_logging', 'tracking_id', 'webex_api_call', '_url_base', '_webex_headers']

# Some functions available to all classes and instances (optionally)
_url_base = "https://webexapis.com/"
_webex_headers = {"Authorization": "",
                  "Content-Type": "application/json",
                  "Accept": "application/json"}


def webex_api_call(method: str,
                   url: str,
                   headers: dict = None,
                   params: dict = None,
                   payload: dict = None,
                   retry_count: int = 3,
                   domain: Optional[str] = None,
                   **kwargs):
    """ Generic handler for all Webex API requests

    This function performs the Webex API call as a Session and handles processing the response. It has the ability
    to recognize paginated responses from the API and make subsequent requests to get all data, regardless of
    how many pages (calls) are needed.

    Args:
        method (str): The HTTP method to use. **get**, **post** and **put** are supported.
        url (str): The endpoint part of the URL (after https://webexapis.com/)
        headers (dict, optional): HTTP headers to use with the request. If not provided, **wxcadm** will use the base
            Authorization header from when the Webex instance was initialized.
        params (dict, optional): Any parameters to be passed as part of an API call
        payload (dict, optional): Payload that will be sent in a POST or PUT. Will be converted to JSON during the
            API call
        retry_count (int, optional): Controls the number of times an API call will be retried if the API returns a
            429 Too Many Requests. The wait time between retries will be based on the Retry-After header sent by Webex.
            Default is 3.
        donmain (str, optional): The domain name to use if anything other than https://webexapis.com

    Returns:
        The return value will vary based on the API response. If a list of items are returned, a list will be returned.
            If the details for a single entry are returned by the API, a dict will be returned.

    Raises:
        wxcadm.exceptions.APIError: Raised when the API call fails to retrieve at least one response.

    """
    log.debug("Webex API Call:")
    log.debug(f"\tMethod: {method}")

    # Hacky fix for API calls that don't use the webexapis.com base domain
    if domain is not None:
        url_base = domain
    else:
        url_base = _url_base

    log.debug(f"\tURL: {url_base + url}")
    log.debug(f"\tParams: {params}")

    start = time.time()     # Tracking API execution time
    session = requests.Session()
    if headers is not None:
        session.headers.update(headers)
    else:
        session.headers.update(_webex_headers)

    try_num = 1
    while try_num <= retry_count:
        if method.lower() == "get":
            r = session.get(url_base + url, params=params)
            if r.ok:
                response = r.json()
                # With an 'items' array, we know we are getting multiple values. Without it, we are getting a singe entity
                if "items" in response:
                    log.debug(f"Webex returned {len(response['items'])} items")
                else:
                    return response
            else:
                log.warning("Webex API returned an error")
                log.warning(f"\t[{r.status_code}] {r.text}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                if r.status_code == 400 and kwargs.get('ignore_400', False) is True:
                    log.info("Ignoring 400 Error due to ignore_400=True")
                    return None
                else:
                    raise APIError(f"The Webex API returned an error: [{r.status_code}] {r.text}")

            # Now we look for pagination and get any additional pages as part of the same Session
            if "next" in r.links:
                keep_going = True
                next_url = r.links['next']['url']
                while keep_going:
                    log.debug(f"Getting more items from {next_url}")
                    r = session.get(next_url)
                    if r.ok:
                        new_items = r.json()
                        if "items" not in new_items:
                            continue     # This is here just to handle a weird case where the API responded with no data
                        log.debug(f"Webex returned {len(new_items['items'])} more items")
                        response['items'].extend(new_items['items'])
                        if "next" not in r.links:
                            keep_going = False
                        else:
                            next_url = r.links['next']['url']
                    else:
                        if r.status_code == 429:
                            retry_after = int(r.headers.get('Retry-After', 30))
                            log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                            time.sleep(retry_after)
                            continue
                        else:
                            keep_going = False

            session.close()
            end = time.time()
            log.debug(f"__webex_api_call() completed in {end - start} seconds")
            return response['items']
        elif method.lower() == "put":
            r = session.put(url_base + url, params=params, json=payload)
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    response = r.text
                if response:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return response
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return True
            else:
                log.warning("Webex API returned an error")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    raise APIError(f"The Webex API returned an error: {r.text}")
        elif method.lower() == "put_upload":
            log.debug("Putting a file upload")
            log.debug(payload)
            session.headers['Content-Type'] = payload.content_type
            r = session.put(url_base + url, params=params, data=payload)
            log.debug(f"Response Headers: {r.headers}")
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return response
            else:
                log.warning("Webex API returned an error")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    raise APIError(f"The Webex API returned an error: {r.text}")
        elif method.lower() == "post":
            log.debug(f"Post body: {payload}")
            r = session.post(url_base + url, params=params, json=payload)
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return response
            else:
                log.warning(f"Webex API returned an error: {r.text}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    raise APIError(f"The Webex API returned an error: {r.text}")
        elif method.lower() == "post_upload":
            log.debug("Posting a file upload")
            log.debug(payload)
            session.headers['Content-Type'] = payload.content_type
            r = session.post(url_base + url, params=params, data=payload)
            log.debug(f"Response Headers: {r.headers}")
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return response
            else:
                log.warning("Webex API returned an error")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    raise APIError(f"The Webex API returned an error: {r.text}")
        elif method.lower() == "delete":
            r = session.delete(url_base + url, params=params)
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return response
            else:
                log.warning("Webex API returned an error")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    raise APIError(f"The Webex API returned an error: {r.text}")
        elif method.lower() == "patch":
            r = session.patch(url_base + url, params=params, json=payload)
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    return response
            else:
                log.info(f"Webex API returned an error")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    raise APIError(f"The Webex API returned an error: {r.text}")
        else:
            return False
    return False


def console_logging(level: str = "debug", formatter: Optional[logging.Formatter] = None):
    """ Enable logging directly to STDOUT

    This adds a STDOUT logging handler to the existing logger. Any other handlers that have been applied will continue
    to function at their current logging level.

    Args:
        level (str, optional): The logging level. Valid values are ``"none"``, ``"debug"``, ``"info"``, ``"warning"``
            and ``"critical"``. Defaults to ``debug`` for full debug output.
        formatter (logging.Formatter, optional): A :py:class:`logging.Formatter` object defining the log format for
            logging to the console. If omitted, the format will be the message level and the message.
    """
    handler = logging.StreamHandler(sys.stdout)
    level_map = {"info": logging.INFO,
                 "warning": logging.WARNING,
                 "debug": logging.DEBUG,
                 "critical": logging.CRITICAL}
    if level.lower() != "none":
        handler.setLevel(level_map[level])
        if formatter is not None:
            if isinstance(formatter, logging.Formatter):
                handler.setFormatter(formatter)
            else:
                log.warning("Did not receive logging.Formatter object for formatter argument")
                formatter = logging.Formatter('%(levelname)s:\t%(message)s')
                handler.setFormatter(formatter)
        else:
            formatter = logging.Formatter('%(levelname)s:\t%(message)s')
            handler.setFormatter(formatter)
        log.addHandler(handler)
    else:
        log.debug("Removing Console Logging handlers")
        for handler in log.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream.name == "<stdout>":
                log.removeHandler(handler)


def decode_spark_id(id: str):
    """ Decode the Webex ID to obtain the Spark ID

    Note that the returned string is the full URI, like
        ```ciscospark://us/PEOPLE/5b7ddefe-cc47-496a-8df0-18d8e4182a99```. In most cases, you only care about the ID
        at the end, so a ```.split('/')[-1]``` can be used to obtain that.

    Args:
        id (str): The Webex ID (base64 encoded string)

    Returns:
        str: The Spark ID

    """
    id_bytes = base64.b64decode(id + "==")
    spark_id: str = id_bytes.decode("utf-8")
    return spark_id


def tracking_id():
    id = f"WXCADM_{uuid.uuid4()}"
    return id

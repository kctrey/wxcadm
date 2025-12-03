from __future__ import annotations

import base64
import logging
import uuid
import time
import re
import requests
import sys
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from requests_toolbelt import MultipartEncoder

from .exceptions import *
import wxcadm
from wxcadm import log

__all__ = ['decode_spark_id', 'console_logging', 'tracking_id', 'webex_api_call', '_url_base', '_webex_headers',
           'WebexApi']

# Some functions available to all classes and instances (optionally)
_url_base = "https://webexapis.com/"
_webex_headers = {"Authorization": "",
                  "Content-Type": "application/json",
                  "Accept": "application/json"}

class WebexApi:
    def __init__(self,
                 access_token: str,
                 org_id: Optional[str] = None,
                 url_base: str = "https://webexapis.com/",
                 retry_count: int = 10):
        self.access_token = access_token
        self.org_id = org_id
        self.url_base = url_base
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Always include the orgId param if given an org_id
        self.parameters = None
        if org_id is not None:
            self.parameters = {'orgId': org_id}
        self.retry_count = retry_count
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _clean_endpoint(self, url: str) -> str:
        # This just cleans up the URL to make sure there aren't any // other than after the https:
        if url.startswith("/"):
            url = url[1:]
        if self.url_base.endswith("/"):
            url = self.url_base + url
        else:
            url = self.url_base + "/" + url
        return url

    def _clean_params(self, params: Optional[dict] = None) -> dict:
        new_params = {}
        if self.parameters is not None:
            new_params = self.parameters.copy()
        if params is not None:
            new_params.update(params)
        return new_params

    def get(self,
            endpoint: str,
            params: Optional[dict] = None,
            items_key: str = 'items',
            kwargs: Optional[dict] = None,):
        """ Perform a GET request to the webex API.

        Args:
            endpoint (str): The API endpoint (e.g. `/v1/people`)
            params (dict, optional): The request parameters, in dict format
            items_key (str, optional): The key to use for the list of entries. Defaults to 'items'.

        Returns:

        """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        page_number = 1
        start_time = time.time()
        try_num = 1
        log.debug("Webex API Call:")
        log.debug("\tMethod: GET")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        keep_trying = True
        while try_num <= self.retry_count and keep_trying is True:
            r = self.session.get(url, params=params)
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            if r.ok:
                response = r.json()
                if items_key in response:
                    log.debug(f"Webex returned {len(response[items_key])} items")
                else:
                    return response
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                log.warning(f"\t[{r.status_code}] {r.text}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    try_num += 1
                    continue
                elif r.status_code == 400 and kwargs.get('ignore_400', False) is True:
                    log.info("Ignoring 400 Error due to ignore_400=True")
                    return None
                # The following was added to handle cross-region analytics and CDR
                elif r.status_code == 451:
                    log.info("Retrying GET in different API region")
                    message = r.json()
                    log.debug(message['message'])
                    m = re.search('Please use (.*)', message['message'])
                    if not m:
                        m = re.search('URL: (.*)', message['message'])
                    if m:
                        new_domain = m.group(1)
                        log.info(f'Using {new_domain} as new domain')
                        url_base = f'https://{new_domain}'
                        continue
                else:
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
            if "next" in r.links:
                keep_going = True
                next_url = r.links['next']['url']
                log.debug(f"Next URL: {next_url}")
                while keep_going:
                    log.debug(f"Getting more items from {next_url}")
                    page_number += 1
                    log.debug(f"Page number: {page_number}")
                    r = self.session.get(next_url)
                    log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                    log.debug(f"\tResponse Headers: {r.headers}")
                    if r.ok:
                        new_items = r.json()
                        if items_key not in new_items:
                            continue  # This is here just to handle a weird case where the API responded with no data
                        log.debug(f"Webex returned {len(new_items[items_key])} more items")
                        response[items_key].extend(new_items[items_key])
                        if "next" not in r.links:
                            keep_going = False
                            log.debug("End of paginated response")
                            keep_trying = False
                        else:
                            next_url = r.links['next']['url']
                            log.debug(f"Next URL: {next_url}")
                    else:
                        if r.status_code == 429:
                            retry_after = int(r.headers.get('Retry-After', 30))
                            log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                            time.sleep(retry_after)
                            continue
                        else:
                            keep_going = False
            else:
                try_num = self.retry_count + 1
        end_time = time.time()
        log.debug(f"GET {url} completed in {end_time - start_time} seconds")
        return response[items_key]

    def put(self, endpoint: str,
            payload: Optional[dict] = None,
            params: Optional[dict] = None):
        """ Perform a PUT request to the webex API.

        Args:
            endpoint (str): The API endpoint (e.g. `/v1/people`)
            payload (dict): The payload of the request
            params (dict, optional): The request parameters, in dict format

        Returns:
            Union[dict, bool]: The response if any was present, otherwise True for success.

        """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        start_time = time.time()
        try_num = 1
        log.debug("Webex API Call:")
        log.debug("\tMethod: PUT")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        log.debug("\tPayload: %s", payload)
        while try_num <= self.retry_count:
            r = self.session.put(url, json=payload, params=params)
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    response = r.text
                if response:
                    end_time = time.time()
                    log.debug(f"GET {url} completed in {end_time - start_time} seconds")
                    return response
                else:
                    end_time = time.time()
                    log.debug(f"GET {url} completed in {end_time - start_time} seconds")
                    return True
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    try_num += 1
                    continue
                else:
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        return False

    def put_upload(self,
                   endpoint: str,
                   payload: MultipartEncoder = None,
                   params: Optional[dict] = None):
        """ Perform a PUT request to the webex API that uploads a file.

        This is a special PUT that handles a file. The payload must be in a specific format

        Args:
            endpoint (str): The API endpoint (e.g. `/v1/people`)
            payload (MultipartEncoder): The payload of the request
            params (dict, optional): The request parameters, in dict format

        Returns:
            Union[dict, bool]: The response if any was present, otherwise True for success.

        """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        start_time = time.time()
        log.debug("Webex API Call:")
        log.debug("\tMethod: PUT")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        log.debug("\tPayload: %s", payload)
        # Since we are changing HTTP Headers for this type of call, just use a new session
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": payload.content_type,
            "Accept": "application/json",
        })
        r = session.put(url, json=payload, params=params)
        log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
        log.debug(f"Response Headers: {r.headers}")
        if r.ok:
            try:
                response = r.json()
            except requests.exceptions.JSONDecodeError:
                end_time = time.time()
                log.debug(f"PUT {url} completed in {end_time - start_time} seconds")
                session.close()
                return True
            else:
                end_time = time.time()
                log.debug(f"PUT {url} completed in {end_time - start_time} seconds")
                session.close()
                return response
        else:
            log.warning("Webex API returned an error")
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            session.close()
            try:
                raise APIError(r.json())
            except requests.exceptions.JSONDecodeError:
                raise APIError(r.text)

    def post(self,
             endpoint: str,
             payload: Optional[dict] = None,
             params: Optional[dict] = None):
        """ Perform a POST request to the Webex API.

                Args:
                    endpoint (str): The API endpoint (e.g. `/v1/people`)
                    payload (dict, optional): The payload of the request
                    params (dict, optional): The request parameters, in dict format

                Returns:
                    Union[dict, bool]: The response if any was present, otherwise True for success.

                """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        start_time = time.time()
        log.debug("Webex API Call:")
        log.debug("\tMethod: POST")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        log.debug("\tPayload: %s", payload)
        try_num = 1
        while try_num <= self.retry_count:
            r = self.session.post(url, json=payload, params=params)
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            if r.ok:
                try:
                    response = r.json()
                    log.debug(f"Response: {response}")
                except requests.exceptions.JSONDecodeError:
                    end_time = time.time()
                    log.debug(f"POST {url} completed in {end_time - start_time} seconds")
                    return True
                else:
                    end_time = time.time()
                    log.debug(f"POST {url} completed in {end_time - start_time} seconds")
                    return response
            else:
                log.warning(f"Webex API returned an error: {r.text}")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    try_num += 1
                    continue
                else:
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        return False

    def post_upload(self,
                   endpoint: str,
                   payload: MultipartEncoder = None,
                   params: Optional[dict] = None):
        """ Perform a POST request to the webex API that uploads a file.

        This is a special POST that handles a file. The payload must be in a specific format

        Args:
            endpoint (str): The API endpoint (e.g. `/v1/people`)
            payload (MultipartEncoder): The payload of the request
            params (dict, optional): The request parameters, in dict format

        Returns:
            Union[dict, bool]: The response if any was present, otherwise True for success.

        """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        start_time = time.time()
        log.debug("Webex API Call:")
        log.debug("\tMethod: POST")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        log.debug("\tPayload: %s", payload)
        # Since we are changing HTTP Headers for this type of call, just use a new session
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": payload.content_type,
            "Accept": "application/json",
        })
        r = session.post(url, json=payload, params=params)
        log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
        log.debug(f"Response Headers: {r.headers}")
        if r.ok:
            try:
                response = r.json()
            except requests.exceptions.JSONDecodeError:
                end_time = time.time()
                log.debug(f"POST {url} completed in {end_time - start_time} seconds")
                session.close()
                return True
            else:
                end_time = time.time()
                log.debug(f"POST {url} completed in {end_time - start_time} seconds")
                session.close()
                return response
        else:
            log.warning("Webex API returned an error")
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            session.close()
            try:
                raise APIError(r.json())
            except requests.exceptions.JSONDecodeError:
                raise APIError(r.text)

    def delete(self,
               endpoint: str,
               params: Optional[dict] = None):
        """ Perform a DELETE request to the Webex API.

        Args:
            endpoint (str): The API endpoint (e.g. `/v1/people`)
            params (dict, optional): The request parameters, in dict format

        Returns:
            Union[dict, bool]: The response if any was present, otherwise True for success.

        """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        start_time = time.time()
        log.debug("Webex API Call:")
        log.debug("\tMethod: DELETE")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        try_num = 1
        while try_num <= self.retry_count:
            r = self.session.delete(url, params=params)
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            if r.ok:
                try:
                    response = r.json()
                    log.debug(f'Response: {response}')
                except requests.exceptions.JSONDecodeError:
                    end_time = time.time()
                    log.debug(f"DELETE {url} completed in {end_time - start_time} seconds")
                    return True
                else:
                    end_time = time.time()
                    log.debug(f"DELETE {url} completed in {end_time - start_time} seconds")
                    return response
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    try_num += 1
                    continue
                else:
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        return False

    def patch(self,
              endpoint: str,
              payload: Optional[dict] = None,
              params: Optional[dict] = None):
        """ Perform a PATCH request to the Webex API.

        Args:
            endpoint (str): The API endpoint (e.g. `/v1/people`)
            payload (dict, optional): The payload of the request
            params (dict, optional): The request parameters, in dict format

        Returns:
            Union[dict, bool]: The response if any was present, otherwise True for success.

        """
        # Clean the endpoint to get a good URL
        url = self._clean_endpoint(endpoint)
        # Clean the parameters to include any at the instance level
        params = self._clean_params(params)
        start_time = time.time()
        log.debug("Webex API Call:")
        log.debug("\tMethod: DELETE")
        log.debug("\tURL: %s", url)
        log.debug("\tParameters: %s", params)
        log.debug("\tPayload: %s", payload)
        try_num = 1
        while try_num <= self.retry_count:
            r = self.session.patch(url, json=payload, params=params)
            log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end_time = time.time()
                    log.debug(f"PATCH {url} completed in {end_time - start_time} seconds")
                    return True
                else:
                    end_time = time.time()
                    log.debug(f"PATCH {url} completed in {end_time - start_time} seconds")
                    return response
            else:
                log.info(f"Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    try_num += 1
                    continue
                else:
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        return False




def webex_api_call(method: str,
                   url: str,
                   headers: Optional[dict] = None,
                   params: Optional[dict] = None,
                   payload: dict | MultipartEncoder | None = None,
                   retry_count: Optional[int] = 5,
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
            Default is 5.
        domain (str, optional): The domain name to use if anything other than https://webexapis.com

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
                # With an 'items' array, we know we are getting multiple values.
                # Without it, we are getting a singe entity
                if "items" in response:
                    log.debug(f"Webex returned {len(response['items'])} items")
                else:
                    session.close()
                    return response
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                log.warning(f"\t[{r.status_code}] {r.text}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                if r.status_code == 400 and kwargs.get('ignore_400', False) is True:
                    log.info("Ignoring 400 Error due to ignore_400=True")
                    session.close()
                    return None
                # The following was added to handle cross-region analytics and CDR
                if r.status_code == 451:
                    log.info("Retrying GET in different API region")
                    message = r.json()
                    log.debug(message['message'])
                    m = re.search('Please use (.*)', message['message'])
                    if not m:
                        m = re.search('URL: (.*)', message['message'])
                    if m:
                        new_domain = m.group(1)
                        log.info(f'Using {new_domain} as new domain')
                        url_base = f'https://{new_domain}'
                        continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)

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
            log.debug(f"\tPayload: {payload}")
            r = session.put(url_base + url, params=params, json=payload)
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    response = r.text
                if response:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return response
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return True
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
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
                    session.close()
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return response
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        elif method.lower() == "post":
            log.debug(f"Post body: {payload}")
            r = session.post(url_base + url, params=params, json=payload)
            if r.ok:
                try:
                    response = r.json()
                    log.debug(f"Response: {response}")
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return response
            else:
                log.warning(f"Webex API returned an error: {r.text}")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
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
                    session.close()
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return response
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        elif method.lower() == "delete":
            log.debug(f"Post body: {payload}")
            r = session.delete(url_base + url, params=params)
            if r.ok:
                try:
                    response = r.json()
                    log.debug(f'Response: {response}')
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return response
            else:
                log.warning("Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
        elif method.lower() == "patch":
            r = session.patch(url_base + url, params=params, json=payload)
            if r.ok:
                try:
                    response = r.json()
                except requests.exceptions.JSONDecodeError:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return True
                else:
                    end = time.time()
                    log.debug(f"__webex_api_call() completed in {end - start} seconds")
                    session.close()
                    return response
            else:
                log.info(f"Webex API returned an error")
                log.debug(f"TrackingID: {r.headers.get('Trackingid', 'None')}")
                if r.status_code == 429:
                    retry_after = int(r.headers.get('Retry-After', 30))
                    log.info(f"Received 429 Too Many Requests. Waiting {retry_after} seconds to retry.")
                    time.sleep(retry_after)
                    continue
                else:
                    session.close()
                    try:
                        raise APIError(r.json())
                    except requests.exceptions.JSONDecodeError:
                        raise APIError(r.text)
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


def location_finder(location_id: str, parent):
    """ Return the :class:`Location` for a given Location ID """
    log.debug(f"location_finder: Finding {location_id}")
    if isinstance(parent, wxcadm.Location):
        log.debug("location_finder: Parent is a Location")
        if parent.id == location_id:
            log.debug(f"location_finder: Parent ID matches ({parent.name})")
            return parent
        else:
            log.debug("location_finder: Parent ID doesn't match. Finding by ID at Org.")
            location = parent.parent.locations.get(id=location_id)
            if location is None:
                log.debug("No match found. Returning None.")
            else:
                log.debug(f"Location found ({location.name})")
            return location
    elif isinstance(parent, wxcadm.Org):
        log.debug("location_finder: Parent is an Org")
        location = parent.locations.get(id=location_id)
        if location is None:
            log.debug("No match found. Returning None.")
        else:
            log.debug(f"Location found ({location.name})")
        return location
    return None

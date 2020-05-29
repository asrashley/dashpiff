"""
Utility function to make an HTTP request to origin
"""
import logging
from typing import Dict, List
import urllib

import azure.functions as func
import requests

def make_request(req: func.HttpRequest, origin_host: str,
                 origin_path: str, param: str) -> requests.Response:
    """
    Make an HTTP GET request to origin. It replaces the host and path from
    the request URL with "origin_host" and "origin_path". Any query
    parameters are copied into the origin request.

    :origin_host: the DNS name of origin host
    :origin_path: the URL path to use as the start of the origin request
    :params: the name of URL parameter to extract from the client request
    """
    headers: Dict[str, str] = {}
    headers.update(req.headers)
    headers['host'] = origin_host
    try:
        parts = [origin_path, req.route_params[param]]
        path = '/'.join(parts)
    except KeyError as err:
        logging.warning("Failed to get route parameters from client request: %s", err)
        path = origin_path
    query: str = ''
    if req.params:
        query = urllib.parse.urlencode(req.params)
    url = urllib.parse.urlunsplit(('http', origin_host, path, query, ''))
    logging.debug("Request %s", url)
    return requests.get(url, headers=headers)

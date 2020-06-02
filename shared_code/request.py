"""
Utility function to make an HTTP request to origin
"""
import logging
from typing import Dict
import urllib

import azure.functions as func
import requests

def fetch(req: func.HttpRequest, url: str) -> requests.Response:
    """
    Make an HTTP GET request to origin. It copies the HTTP headers
    from the client request into the origin request. Any query
    parameters are also copied into the origin request.

    :req: the client request
    :url: The origin URL
    """
    headers: Dict[str, str] = {}
    headers.update(req.headers)
    parts = urllib.parse.urlparse(url)
    query = parts.query
    if req.params:
        query = urllib.parse.urlencode(req.params)
    headers['host'] = parts.hostname
    origin_url = urllib.parse.urlunsplit((parts[0], parts[1], parts[2], query, parts[4]))
    logging.debug("Request %s", origin_url)
    return requests.get(origin_url, headers=headers)

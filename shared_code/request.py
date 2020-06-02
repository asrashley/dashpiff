"""
Utility function to make an HTTP request to origin
"""
import binascii
import logging
from typing import Dict
import urllib

import azure.functions as func
import requests

def encode_url(url: str, use_base64: bool = True) -> str:
    """
    Wrap the given URL into a form that can be used as a path
    component in another URL.

    Using simple URL encoding does not work on Azure as it
    partially undoes the %2F encoding, producing a URL
    that cannot be decoded.
    """
    if use_base64:
        b64 = binascii.b2a_base64(bytes(url, 'utf-8'), newline=False)
        return str(b64, 'utf-8')
    return urllib.parse.quote(url, safe='')

def decode_url(url: str) -> str:
    """
    Undo the output of encode_url function
    """
    if url.startswith(r'http%3A%2F%2F'):
        return urllib.parse.unquote(url)
    return str(binascii.a2b_base64(url), 'utf-8')

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
    origin_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc,
        parts.path, query, parts.fragment))
    logging.debug("Request %s", origin_url)
    return requests.get(origin_url, headers=headers)

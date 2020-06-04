"""
Utility function to make an HTTP request to origin
"""
import logging
from typing import Dict
import urllib

import azure.functions as func
import requests

ESCAPE_TABLE = [
    ('!', '!!'),
    (':', '!0'),
    ('/', '!1'),
    ('#', '!2'),
    ('~', '!3'),
    ('?', '!4'),
]

def encode_url(url: str) -> str:
    """
    Wrap the given URL into a form that can be used as a path
    component in another URL.

    Using simple URL encoding does not work on Azure as it
    partially undoes the %2F encoding, producing a URL
    that cannot be decoded. This function uses its own
    escaping mechanism using ! as the escape character.
    """
    for in_chr, out_str in ESCAPE_TABLE:
        url = url.replace(in_chr, out_str)
    return url

def decode_url(url: str) -> str:
    """
    Undo the output of encode_url function
    """
    for in_chr, out_str in reversed(ESCAPE_TABLE):
        url = url.replace(out_str, in_chr)
    return url

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
        # We can't use the normal URL encoding of CGI parameters because some
        # CDNs (such as Akamai) don't correctly undo the escaping of CGI
        # parameters
        params = [f'{key}={value}' for key, value in req.params.items()]
        query = '&'.join(params)
    headers['host'] = parts.hostname
    origin_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc,
        parts.path, query, parts.fragment))
    logging.debug("Request %s", origin_url)
    return requests.get(origin_url, headers=headers)

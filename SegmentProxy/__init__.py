"""
Lambda function that patches the PIFF UUID sample encryption box.
It converts it into a "free" box, which is an ISO BMFF defined
box that has no defined content.
"""

import binascii
import logging
from typing import Dict, Optional
import urllib

import azure.functions as func

# pylint: disable=relative-beyond-top-level
from ..shared_code.constants import PIFF_UUID, FREE_UUID
from ..shared_code.request import fetch, decode_url

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    An httpTrigger lambda that will remove the PIFF box in DASH
    media segments by translating them into "free" boxes.
    """
    logging.info('Processing media request %s %s',
        req.route_params.get('origin'), req.route_params.get('path'))
    logging.debug("url=%s", req.url)

    # extract the original BaseURL from the URL that triggered this
    # function and then append the segment path, to create a URL
    # to fetch from origin.
    base_url = decode_url(req.route_params.get('origin'))
    origin_url = urllib.parse.urljoin(base_url, req.route_params.get('path'))

    origin = fetch(origin_url, req.headers, req.params)
    try:
        mimetype = origin.headers['Content-Type']
    except KeyError:
        mimetype = 'application/octet-stream'
    body: Optional[bytes] = origin.content
    if origin.status_code == 200 and 'text' not in mimetype:
        # replace PIFF_UUID with FREE_UUID
        pos = body.find(PIFF_UUID)
        if pos > 0:
            body = body[:pos] + FREE_UUID + body[pos+len(PIFF_UUID):]
    return func.HttpResponse(body=body, status_code=origin.status_code,
         mimetype=mimetype, headers=origin.headers)

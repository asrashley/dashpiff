"""
Lambda function that proxies manifest request.
It replaces the BaseURL from the origin with BASE_URL, which points
to the SegmentProxy lambda.
"""

import binascii
import logging
from typing import Dict, Optional, Union
import urllib

import azure.functions as func

import requests

# pylint: disable=relative-beyond-top-level
from ..shared_code import constants
from ..shared_code.request import make_request

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.debug('Processing manifest request %s', req.route_params.get('manifest'))

    origin = make_request(req, constants.MANIFEST_HOST, constants.MANIFEST_PATH, 'manifest')
    
    try:
        mimetype = origin.headers['Content-Type']
    except KeyError:
        mimetype = 'text/dash+xml'
    body: Optional[Union[bytes, str]] = None
    if 'text' in mimetype or 'dash+xml' in mimetype:
        body = origin.text
    else:
        body = origin.content
    headers = {}
    for key, value in origin.headers.items():
        if key.lower() not in constants.EXCLUDED_HTTP_HEADERS:
            headers[key] = value
    if 'Connection' in headers:
        del headers['Connection']
    if origin.status_code == 200 and mimetype == 'application/dash+xml':
        # replace the original BaseURL with a URL that points to the 
        # SegmentProxy lambda
        parts = urllib.parse.urlparse(req.url)
        media_url = parts.hostname
        if parts.port and parts.port != 80:
            media_url += f':{parts.port}'
        media_url += '/api/media'
        origin_base_url = '/'.join([constants.MEDIA_HOST, constants.MEDIA_PATH])
        logging.debug('Replacing "%s" with "%s"', origin_base_url, media_url)
        body = body.replace(origin_base_url, media_url)
    return func.HttpResponse(body=body, status_code=origin.status_code,
         mimetype=mimetype, headers=headers)

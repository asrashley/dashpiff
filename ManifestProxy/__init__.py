"""
Lambda function that proxies manifest request.
It replaces the BaseURL from the origin with BASE_URL, which points
to the SegmentProxy lambda.
"""

import binascii
import logging
import re
from typing import Dict, Optional, Union
import urllib

import azure.functions as func

import requests

baseurl_re = re.compile(r'<BaseURL>(?P<url>[^<]+)</BaseURL>')

# pylint: disable=relative-beyond-top-level
from ..shared_code import constants
from ..shared_code.request import fetch

def url_replacer(media_url, match) -> str:
    """
    Used in the regexp replacer function to wrap BaseURL
    elements to point to the SegmentProxy lambda.
    
    For example <BaseURL>http://example.site/foo</BaseURL> becomes
    <BaseURL>http://my.lambda/api/media/http%3A%2F%2Fexample.site%2Ffoo/</BaseURL>
    """
    return ''.join(media_url + [
        urllib.parse.quote(match.group('url'), safe=''),
        r'/</BaseURL>'])

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    An httpTrigger lambda that will wrap the BaseURL fields in the
    manifest so that all requsts for media segments will be directed
    to the SegmentProxy lambda.
    """

    logging.debug('Processing manifest request %s', req.route_params.get('manifest'))

    manifest_url = urllib.parse.unquote(req.route_params.get('manifest'))
    origin = fetch(req, manifest_url)
    
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
        media_url = ['<BaseURL>', 'http://', parts.hostname]
        if parts.port and parts.port != 80:
            media_url.append(f':{parts.port}')
        media_url.append('/api/media/')

        # modify all BaseURL elements to point to the SegmentProxy lambda,
        # with a URL that wraps the original origin URL
        body = baseurl_re.sub(lambda match: url_replacer(media_url, match), body)
    return func.HttpResponse(body=body, status_code=origin.status_code,
         mimetype=mimetype, headers=headers)

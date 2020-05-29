"""
Lambda function that patches the PIFF UUID sample encryption box.
It converts it into a "free" box, which is an ISO BMFF defined
box that has no defined content.
"""

import binascii
import logging
from typing import Dict, Optional

import azure.functions as func

# pylint: disable=relative-beyond-top-level
from ..shared_code.constants import MEDIA_HOST, MEDIA_PATH
from ..shared_code.request import make_request

PIFF_UUID = binascii.a2b_hex("a2394f525a9b4f14a2446c427c648df4")

# The "free" box type in UUID form. See section 11.1 of ISO 14496-12
FREE_UUID = binascii.a2b_hex("6672656500110010800000AA00389B71")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.debug('Processing media request %s', req.route_params.get('path'))

    # TODO: use streamed mode to save having to wait for whole segment
    # to be fetched from origin
    origin = make_request(req, MEDIA_HOST, MEDIA_PATH, 'path')
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

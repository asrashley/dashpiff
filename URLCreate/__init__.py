"""
A lambda to encode a manifest URL so that it points to the 
"ManifestProxy" lambda. The "ManifestProxy" lambda is able
to extract the original URL and fetch it from the origin.
"""

import json
import logging
import urllib

import azure.functions as func

def extract_url_from_request(req: func.HttpRequest) -> str:
    """
    Check the request for a "url" field.
    It searches for a CGI parameter, an application/x-www-form-urlencoded
    form or an application/json payload.
    """
    url = req.params.get('url')
    if url:
        return url
    content_type = req.headers.get('Content-Type', '')
    logging.debug('content type: %s', content_type)
    if 'json' in content_type:
        req_body = req.get_json()
        return req_body.get('url')
    if 'x-www-form-urlencoded' in content_type:
        form = urllib.parse.parse_qs(req.get_body())
        if b'url' in form:
            return str(form[b'url'][0], 'utf-8')
        return form["url"]
    raise ValueError("Unknown payload type")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('URLCreate HTTP trigger function processed a request. %s',
        req.method)

    if req.method == 'POST' or req.params.get('url'):
        try:
            url = extract_url_from_request(req)
        except (ValueError, KeyError) as err:
            logging.error("Failed to extract URL field: %s %s", type(err), err)
            url = None
        if not url:
            return func.HttpResponse(
                'Field "url" is required either in the query string or in the request body',
                status_code=400
            )
        parts = urllib.parse.urlparse(req.url)
        manifest_url = ['http://', parts.hostname]
        if parts.port and parts.port != 80:
            manifest_url.append(f':{parts.port}')
        manifest_url.append('/api/dash/')
        manifest_url.append(urllib.parse.quote(url))
        result = dict(url=''.join(manifest_url))
        return func.HttpResponse(body=json.dumps(result), mimetype="application/json",
            status_code=200)
    body = """<!doctype html><html lang="en">
    <head><title>Manifest URL generator</title></head>
    <body>
    <form method="POST">
    <label for="url">Manifest URL:</label>
    <input type="text" name="url" placeholder="DASH manifest URL..." />
    <button type="submit">Generate URL</button>
    </form>
    </body></html>
    """
    return func.HttpResponse(body=body, mimetype='text/html', status_code=200)

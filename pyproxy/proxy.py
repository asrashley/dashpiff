"""
An HTTP proxy that can make upstream origin requests and modify responses
before returning them to the requesting client.
"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
import re
from socketserver import ThreadingMixIn
import threading
import time
from typing import Dict, List, Optional, Union
import urllib
from xml.sax.saxutils import unescape

import requests

# pylint: disable=relative-beyond-top-level
from shared_code.constants import PIFF_UUID, FREE_UUID
from shared_code.request import fetch, decode_url, encode_url

class ProxyAddAuthentication(BaseHTTPRequestHandler):
    """
    An HTTP handler that will either respond directly or forward the 
    request to an origin server.
    """
    excluded_headers = ['content-encoding', 'transfer-encoding',
        'content-length', 'content-type', 'date', 'connection',
        'if-modified-since']
    baseurl_re = re.compile(r'<BaseURL>(?P<url>[^<]+)</BaseURL>')

    MANIFEST_PATH = '/mpd/'
    MEDIA_PATH = '/media/'

    # pylint: disable=invalid-name
    def do_GET(self):
        """
        handles GET requests.
        Forwards request to origin after unwrapping the original URL from
        the path
        """
        path = self.path
        query: Optional[Dict] = None
        if '?' in path:
            path, qry = path.split('?', 1)
            query = {key:value for key, value in urllib.parse.parse_qsl(qry)}
        if path.startswith('/create'):
            self.create_url(path, query)
        elif path.startswith(self.MANIFEST_PATH):
            self.serve_manifest(path[len(self.MANIFEST_PATH):], query)
        elif path.startswith(self.MEDIA_PATH):
            self.serve_media(path[len(self.MEDIA_PATH):], query)
        else:
            self.send_error(404, f'File not found: {path}')

    # pylint: disable=invalid-name
    def do_POST(self):
        """
        handles POST requests.
        """
        content_len = self.headers['content-length']
        if content_len is not None:
           content_len = int(content_len)
        body = self.rfile.read(content_len)
        return self.create_url(self.path, None, body)

    def create_url(self, path: str, query: Dict, body: Optional[bytes] = None) -> None:
        """
        Encodes a manifest URL so that it points to the
        ManifestProxy service. The "ManifestProxy" is able
        to extract the original URL and fetch it from the origin.
        """
        if self.command == 'POST' or query is not None:
            try:
                url = self.extract_url_from_request(query, body)
            except (ValueError, KeyError) as err:
                logging.error("Failed to extract URL field: %s %s", type(err), err)
                url = None
            if not url:
                self.send_error(400, 
                    'Field "url" is required either in the query string or in the request body')
                return
            req_url = self.request_url()
            logging.debug("Request url = %s", req_url)
            parts = urllib.parse.urlparse(req_url)
            manifest_url = ['http://', parts.hostname]
            if parts.port and parts.port != 80:
                manifest_url.append(f':{parts.port}')
            manifest_url.append(self.MANIFEST_PATH)
            manifest_url.append(encode_url(url))
            result = dict(url=''.join(manifest_url))
            self.respond(body=json.dumps(result), mimetype="application/json",
                status_code=200)
            return
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
        self.respond(status_code=200, body=body, mimetype='text/html')

    def serve_manifest(self, path: str, query: Optional[Dict]) -> None:
        """
        Fetches manifest from origin and wraps the BaseURL fields in the
        manifest so that all requsts for media segments will be directed
        to the SegmentProxy lambda.
        """
        logging.debug('Processing manifest request %s', path)
        manifest_url = decode_url(path)
        logging.debug('Manifest origin URL: %s', manifest_url)
        origin = fetch(manifest_url, self.headers, query)
    
        try:
            mimetype = origin.headers['Content-Type']
        except KeyError:
            mimetype = 'text/dash+xml'
        body: Optional[Union[bytes, str]] = None
        if 'text' in mimetype or 'dash+xml' in mimetype:
            body = origin.text
        else:
            body = origin.content
        if origin.status_code == 200 and mimetype == 'application/dash+xml':
            # replace the original BaseURL with a URL that points to the 
            # SegmentProxy lambda
            parts = urllib.parse.urlparse(self.request_url())
            media_url = ['<BaseURL>', 'http://', parts.hostname]
            if parts.port and parts.port != 80:
                media_url.append(f':{parts.port}')
            media_url.append(self.MEDIA_PATH)

            # modify all BaseURL elements to point to the SegmentProxy lambda,
            # with a URL that wraps the original origin URL
            body = self.baseurl_re.sub(lambda match: self.url_replacer(media_url, match), body)
        self.respond(status_code=origin.status_code, mimetype=mimetype, headers=origin.headers,
                    body=body)

    def serve_media(self, path: str, query: Optional[Dict]) -> None:
        """
        Fetch DASH media segment from origin and remove the PIFF box
        by translating them into "free" boxes.
        """
        enc_base_url = path.split('/')[0]
        path = path[1 + len(enc_base_url):]
        logging.info('Processing media request %s  %s', enc_base_url, path)

        # extract the original BaseURL from the URL that triggered this
        # function and then append the segment path, to create a URL
        # to fetch from origin.
        base_url = decode_url(enc_base_url)
        origin_url = urllib.parse.urljoin(base_url, path)
        origin = fetch(origin_url, self.headers, query)
        logging.debug("Origin response: %d", origin.status_code)
        try:
            mimetype = origin.headers['Content-Type']
        except KeyError:
            mimetype = 'application/octet-stream'
        body: Optional[bytes] = origin.content
        if origin.status_code == 200 and 'text' not in mimetype:
            # replace PIFF_UUID with FREE_UUID
            pos = body.find(PIFF_UUID)
            logging.info("pos=%d", pos)
            if pos > 0:
                body = body[:pos] + FREE_UUID + body[pos+len(PIFF_UUID):]
        self.respond(body=body, status_code=origin.status_code,
            mimetype=mimetype, headers=origin.headers)

    def respond(self, status_code: int, body: Union[bytes, str], mimetype: str,
                headers: Optional[Dict] = None) -> None:
        """
        Respond with the given HTTP status code and payload
        """
        if isinstance(body, str):
            body = bytes(body, 'utf-8')
        self.send_response(200)
        self.send_header('Content-Type', mimetype)
        self.send_header('Content-Length', len(body))
        if headers is not None:
            for key, value in headers.items():
                if key.lower() not in self.excluded_headers:
                    self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def request_url(self) -> str:
        """
        Get the absolute URL used for this request
        """
        try:
           return ''.join(['http://', self.headers['Host'], '/', self.path])
        except KeyError:
            pass
        host = self.server.server_name
        if self.server.server_port == 80:
            return ''.join(['http://', host, '/', self.path])
        return ''.join(['http://', host, ':', str(self.server.server_port), '/', self.path])

    def extract_url_from_request(self, query: Optional[Dict], body: Optional[bytes]) -> str:
        """
        Check the request for a "url" field.
        It searches for a CGI parameter, an application/x-www-form-urlencoded
        form or an application/json payload.
        """
        if query is not None:
            url = query.get('url')
            if url:
                return url
        content_type = self.headers.get('Content-Type', '')
        logging.debug('content type: %s', content_type)
        if 'json' in content_type:
            req_body = json.loads(body)
            return req_body.get('url')
        if 'x-www-form-urlencoded' in content_type:
            form = urllib.parse.parse_qs(body)
            if b'url' in form:
                return str(form[b'url'][0], 'utf-8')
            return form["url"]
        raise ValueError("Unknown payload type")

    def url_replacer(self, media_url: List[str], match: re.match) -> str:
        """
        Used in the regexp replacer function to wrap BaseURL
        elements to point to the SegmentProxy lambda.
    
        For example <BaseURL>http://example.site/foo</BaseURL> becomes
        <BaseURL>http://my.lambda/api/media/http%3A%2F%2Fexample.site%2Ffoo/</BaseURL>
        """
        origin_url = unescape(match.group('url'))
        origin_url = encode_url(origin_url)
        return ''.join(media_url + [origin_url, r'/</BaseURL>'])

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class ProxyDaemon:
    """
    An HTTP proxy that can make upstream origin requests and modify responses
    before returning them to the requesting client.
    """
    def __init__(self, options, env):
        if env is None:
            env = os.environ
        self.env = env
        self.options = options
        self.proxy_thread = None
        self.httpd = None

    def start(self):
        """
        start HTTP serving threads
        """
        self.proxy_thread = threading.Thread(target=self.run)
        self.proxy_thread.daemon = True
        self.proxy_thread.start()

    def run(self):
        """
        Handle HTTP requests.
        This function is called from the thread that is started
        to handle HTTP requests
        """
        server_address = (self.options.bind, self.options.port)

        self.httpd = ThreadedHTTPServer(server_address, ProxyAddAuthentication)
        # pylint: disable=attribute-defined-outside-init
        self.httpd.options = self.options
        self.httpd.serve_forever()

    def stop(self):
        """
        stop HTTP serve threads
        """
        if self.proxy_thread and self.proxy_thread.is_alive():
            self.httpd.shutdown()
            self.proxy_thread.join()
            self.proxy_thread = None


def main():
    """
    functon that is called when proxy.py is called from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--bind", dest="bind", default="127.0.0.1",
                        action="store", type=str,
                        help="IP address to bind to [%(default)s]")
    parser.add_argument("-v", "--verbose", dest="verbosity", default=0,
                        action="count", help="Increase verbosity")
    parser.add_argument("-p", "--port", dest="port", default=8001,
                        action="store", type=int,
                        help="Run HTTP proxy on port [%(default)s]")
    parser.add_argument("--pid-file", dest="pid_file", help="save PID of process to this file")
    options = parser.parse_args()
    if options.pid_file:
        with open(options.pid_file, 'wt') as pidfile:
            pidfile.write(str(os.getpid()) + "\n")
    env = os.environ.copy()
    log_level = logging.INFO
    if options.verbosity:
        log_level = logging.DEBUG
    logging.basicConfig(format='%(name)s-%(thread)05d: %(levelname)-8s %(message)s',
                        level=log_level)
    prxy = ProxyDaemon(options, env)
    prxy.start()
    logging.info('Proxy running on http://%s:%d/', options.bind, options.port)
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        logging.info('Stopping proxy')
        prxy.stop()
    if options.pid_file:
        os.remove(options.pid_file)

if __name__ == "__main__":
    main()

"""
Global constants
"""

# The host and path where the manifest is hosted
MANIFEST_HOST = "manifest.prod.boltdns.net"
MANIFEST_PATH = "manifest/v1/dash/live-baseurl/bccenc/5840105192001/d6f2fddd-35db-44d8-a5c8-9852cdcde647/6s"

# The host and path where the media is hosted
MEDIA_HOST = "house-fastly-signed-eu-west-1-prod.brightcovecdn.com"
MEDIA_PATH = "media/v1/dash/live/cenc/5840105192001/d6f2fddd-35db-44d8-a5c8-9852cdcde647/ccc0cf98-7905-4f0e-b30f-ac494d213899"

# HTTP headers to not copy from origin response
EXCLUDED_HTTP_HEADERS = set({'content-length', 'connection'})


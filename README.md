# dashpiff
Services that allow the removal of PIFF sample encryption data from a
DASH stream, to work around clients that are not able to handle these
UUID boxes appearing in the stream.

The DASH CENC specification (ICO/IEC DIS 23001-7) defines a
sample auxiliary information "cenc" box that contains information
about how to decrypt each sample in a DASH segment. The Protected
Interoperable File Format (PIFF) specification defines an alternative
method to carry this sample encryption information. This alternative
form is carried in a box that uses the "uuid" signalling method using
the UUID "a2394f525a9b4f14a2446c427c648df4".

Unfortunately, some DASH clients are unable to either handle boxes that
use a UUID box type or incorrectly process this PIFF data.

These services can work-around the second case (failure to process PIFF
data) but not the first case (inability to handle UUID box types).

There are three services:

* URLCreate     - generates a URL that points to ManifestProxy. It is
                  used to translate a URL that points to a DASH manifest
                  into an MPD URL that points to ManifestProxy.
* ManifestProxy - patches Manifest requests to make the BaseURL point
                  to the SegmentProxy lambda
* SegmentProxy  - patches media segments to remove any PIFF sample
                  encryption boxes

The URLCreate function is given the URL of a DASH manifest and will
return a new URL that wraps the original URL and points to the
ManifestProxy service.

The URL can be:

* passed as a CGI parameter in a GET request
* passed as a "url" parameter of a x-www-form-urlencoded form
* passed as a "url" property of a JSON object

If none of the above are provided, a HTML page will be returned
that contains an HTML form that can be used to submit the URL of the
DASH manifest.

URLCreate will return a JSON object with a "url" property that is the
wrapped URL.

The ManifestProxy service acts as a reverse proxy that will make a
request to the origin for the DASH manifest and then search for
BaseURL elements in the manifest. It will replace them with a URL that
points to the SegmentProxy, with the original BaseURL value wrapped in
a manner that the SegmentProxy can undo.

The SegmentProxy service acts as a reverse proxy that will make a request
to the origin for the requested segment and then search for a PIFF sample
encryption box. If found, it will be patched to become a "free" box
that will safely be ignored by DASH clients.
	
These services can be deployed as Lambdas in Azure, but not in AWS
because lambdas in AWS do not support returning binary payloads. See
[Azure deployment](doc/azure.md) for details.

These services can be deployed as an origin service using the
[pyproxy/proxy.py](pyproxy/proxy.py) server. This could be used
as a custom origin behind a CDN, for example in AWS CloudFront. See
[AWS deployment](doc/aws.md) for details.

The pyproxy server is an alternate implementation that combines the
logic from the lambdas into one Python class that provides a
reverse proxy service. It uses a multi-threaded basic HTTP server
to handle HTTP requests and make upstream requests to origin. The pyproxy
server provides the following URL routes:

    /create
    /mpd/{manifest}
    /media/{origin}/{*path}

where:

    {manifest} is an encoded version of the origin manifest URL
    {origin} is an encoded version of a BaseURL from the origin manifest
    {*path} is any other path components that need to be combined with the BaseURL

# dashpiff
Lambda that removes PIFF sample encryption data from a DASH stream,
to work around clients that are not able to handle these UUID boxes
appearing in the stream.

There are two lambdas:

* ManifestProxy - patches Manifest requests to make the BaseURL point
                  to the SegmentProxy lambda
* SegmentProxy  - patches media segments to remove any PIFF sample
                  encryption boxes
				  
It is hard coded to one media asset, which is configured in:

    shared_code/constants.py

	
The lambdas use Azure functions, but the actual useful parts should
be portable to other cloud environments.
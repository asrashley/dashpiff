This repository contains three lambdas as Azure functions:

* URLCreate
* ManifestProxy
* SegmentProxy

The lambdas use the following URL routes:

    /api/create
    /api/dash/{manifest}
    /media/{origin}/{*path}

where:

    {manifest} is an encoded version of the origin manifest URL
    {origin} is an encoded version of a BaseURL from the origin manifest
    {*path} is any other path components that need to be combined with the BaseURL

You can deploy these lambdas directly from Visual Studio Code by installing the
Azure extensions into code and using the "Deploy to Function App..." tool in the
Azure tab.

See [https://docs.microsoft.com/en-us/azure/azure-functions/functions-develop-vs-code]

An alternative method is to fork this repository and then use the deployment center to
automatically deploy the functions from a github repository.

The deployment template used for testing this service 
[is available here](azure-template.json)

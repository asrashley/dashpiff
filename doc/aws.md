The lambdas in this repository are not suitable for use in AWS, as the
SegmentProxy lambda has to return a binary payload. Currently
lambda@edge and the API Gateway make the assumption that the reponses
are not binary files, but objects such as JSON objects. When deployed
as an AWS lambda, the SegmentProxy will return a base64 encoded
media fragment!

An alternative method for AWS based deployments is to use EC2 or
ECS instances running pyproxy that can be configured as a custom origin
behind cloudfront. Cloudfront will need to be pointed to a load balancer
that is publically accessible.

For example, deploying EC2 instances in each availability zone:

Public Internet         |                VPC
                                                     +--> EC2 instance
                                                     |
CloundFront --> Internet Gateway --> Load balancer --+--> EC2 instance
                                                     | 
                                                     +--> EC2 instance

Each EC2 instance will be running the pyproxy service. In the example
CodeDeploy scripts in this repository, nginx is used as the "front
of house" HTTP server on port 80, which proxies the pyproxy service
that is running on port 8001.

Inside each EC2 instance:

  port 80         port 8001
  --------> nginx ----> pyproxy


The EC2 / ECS instances will need a security group that allows inbound
traffic from the VPC on port 80. Port 8001 does *not* need to be
available from outside of the EC2 / ECS instance.

An Application Load Balancer is probably the best choice for the
load balancer, however your mileage may vary.

The settings on CloudFront will probably need to include the query
string in the caching logic, as some DASH content provides use the
query string as part of their access control system. For example:

      "distd8myg6nn186locloudfrontnet": {
        "Type": "AWS::CloudFront::Distribution",
        "Properties": {
          "DistributionConfig": {
            "Enabled": true,
            "PriceClass": "PriceClass_100",
            "DefaultCacheBehavior": {
              "TargetOriginId": "ELB-dashpiff-1-1234023456",
              "ViewerProtocolPolicy": "allow-all",
              "MinTTL": 0,
              "AllowedMethods": [
                "HEAD",
                "GET"
              ],
              "CachedMethods": [
                "HEAD",
                "GET"
              ],
              "ForwardedValues": {
                "QueryString": true,
                "Cookies": {
                  "Forward": "none"
                }
              }
            },
            "Origins": [
              {
                "DomainName": "dashpiff-1-1234023456.eu-west-1.elb.amazonaws.com",
                "Id": "ELB-dashpiff-1-1234023456",
                "S3OriginConfig": {
                  "HTTPPort": "80",
                  "HTTPSPort": "443",
                  "OriginProtocolPolicy": "http-only"
                }
              }
            ],
            "Restrictions": {
              "GeoRestriction": {
                "RestrictionType": "none",
                "Locations": [
  
                ]
              }
            },
            "ViewerCertificate": {
              "CloudFrontDefaultCertificate": "true",
              "MinimumProtocolVersion": "TLSv1"
            }
          }
        }
      }

This reposity contains the CodeDeploy scripts to allow automated deployment to
EC2 or ECS instances. It does *not* contain a full CloudFormation template to
create the entire service. To use CodeDeploy, fork this repository and then
create a CodeDeploy Application to auto-deploy from the forked repository.
Pushes to the forked repository will cause the target EC2 / ECS instances to
have the pyproxy service installed and started.

When using the URLCreate service to generate URLs, requests need to go to the
load balancer.

The ManifestProxy and SegmentProxy services use cloud formation as their
endpoint. This allows the CDN to cache converted fragments, reducing the need
to convert them again when another client makes a request.

#!/bin/bash

cd /var/www/app/ && python3 -m pyproxy.proxy $*

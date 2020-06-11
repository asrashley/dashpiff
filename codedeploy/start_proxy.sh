#!/bin/bash

cd /var/www/app/ && python -m pyproxy.proxy $*

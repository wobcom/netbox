#!/usr/bin/env bash

cp /opt/netbox/scripts/package_scripts/netbox-manage /usr/bin/netbox-manage

chmod 700 /usr/bin/netbox-manage

chown netbox:netbox /usr/bin/netbox-manage
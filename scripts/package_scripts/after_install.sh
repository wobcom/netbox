#!/usr/bin/env bash

echo "Netbox after install"

cp /opt/netbox/scripts/package_scripts/netbox-manage.sh /usr/bin/netbox-manage

chmod 770 /usr/bin/netbox-manage
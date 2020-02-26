#!/usr/bin/env bash

cp /opt/netbox/scripts/package_scripts/netbox-manage /usr/bin/netbox-manage

chmod 700 /usr/bin/netbox-manage

chown netbox:netbox /usr/bin/netbox-manage

# generate secret key
if [[ ( "$(netbox-manage check 2>&1 | grep "SECRET_KEY" -c)" > 0 ) ]] ; then
    echo "Generate secret key setting"
    SECRET_KEY=$(/opt/netbox/venv/bin/python /opt/netbox/netbox/genrate_secret_key.py)
    sed -i "s/SECRET_KEY = ''/SECRET_KEY = '${SECRET_KEY}'/g" /opt/netbox/netbox/netbox/configuration.py
fi
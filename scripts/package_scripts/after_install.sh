#!/usr/bin/env bash

cp /opt/netbox/scripts/package_scripts/netbox-manage /usr/bin/netbox-manage

chmod 700 /usr/bin/netbox-manage

chown netbox:netbox /usr/bin/netbox-manage

cp /opt/netbox/netbox.service /etc/systemd/system/netbox.service

systemctl daemon-reload

echo "Ensure PostgreSQL database is initialized"
/usr/pgsql-9.6/bin/postgresql96-setup initdb

echo "Ensure Netbox, PostgreSQL and Redis services are started and enabled"
systemctl enable postgresql-9.6.service
systemctl start postgresql-9.6.service
systemctl enable redis.service
systemctl start redis.service
systemctl enable netbox.service
systemctl start netbox.service


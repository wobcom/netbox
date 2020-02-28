#!/usr/bin/env bash

cp /opt/netbox/scripts/package_scripts/netbox-manage /usr/bin/netbox-manage

chmod 700 /usr/bin/netbox-manage

chown netbox:netbox /usr/bin/netbox-manage

cp /opt/netbox/netbox.service /etc/systemd/system/netbox.service

systemctl daemon-reload

echo "Ensure PostgreSQL database is initialized"
export PGSETUP_INITDB_OPTIONS="--auth-host='md5'"
/usr/pgsql-9.6/bin/postgresql96-setup initdb

echo "Ensure PostgreSQL and Redis services are started and enabled"
systemctl enable postgresql-9.6.service
systemctl start postgresql-9.6.service
systemctl enable redis.service
systemctl start redis.service

sed -i "s/ALLOWED_HOSTS =.*/ALLOWED_HOSTS = \['\*'\]/g" /opt/netbox/netbox/netbox/configuration.py

# generate secret key
if [[ ( "$(netbox-manage check 2>&1 | grep "SECRET_KEY" -c)" > 0 ) ]] ; then
    echo "Generate secret key setting"
    SECRET_KEY="$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)"
    sed -i "s/SECRET_KEY = ''/SECRET_KEY = '${SECRET_KEY}'/g" /opt/netbox/netbox/netbox/configuration.py
fi

#generate database

if [[ ( "$(su - postgres -c "psql -l -P format=unaligned" | grep -c "^netbox")" > 0 ) ]] ; then
    echo "Netbox database already exist, please configure manually and them execute 'netbox-manage migrate'"
else
    echo "Creating database for netbox"
    DB_NAME="netbox"
    DB_USER="netbox"
    DB_PASSWORD="$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)"
    su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';\""
    su - postgres -c "createdb --owner ${DB_USER} ${DB_NAME}"
    sed -E -i "s/( +'USER':)[^#]*# PostgreSQL username.*/\1 '${DB_USER}',/g" /opt/netbox/netbox/netbox/configuration.py
    sed -E -i "s/( +'NAME':)[^#]*# Database name.*/\1 '${DB_NAME}',/g" /opt/netbox/netbox/netbox/configuration.py
    sed -E -i "s/( +'PASSWORD':)[^#]*# PostgreSQL password.*/\1 '${DB_PASSWORD}',/g" /opt/netbox/netbox/netbox/configuration.py

    echo "Migrating database"

    netbox-manage migrate

fi

echo "Ensure Netbox service is enabled and started"

systemctl enable netbox.service
systemctl start netbox.service

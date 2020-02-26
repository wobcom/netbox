#!/usr/bin/env bash

cp /opt/netbox/scripts/package_scripts/netbox-manage /usr/bin/netbox-manage

chmod 700 /usr/bin/netbox-manage

chown netbox:netbox /usr/bin/netbox-manage

echo "Ensure PostgreSQL database is initialized"
/usr/pgsql-9.6/bin/postgresql96-setup initdb

echo "Ensure PostgreSQL and Redis services are started and enabled"
systemctl enable postgresql-9.6.service
systemctl start postgresql-9.6.service
systemctl enable redis.service
systemctl start redis.service

# generate secret key
if [[ ( "$(netbox-manage check 2>&1 | grep "SECRET_KEY" -c)" > 0 ) ]] ; then
    echo "Generate secret key setting"
    SECRET_KEY="$(/opt/netbox/venv/bin/python /opt/netbox/netbox/generate_secret_key.py)"
    sed -i "s/SECRET_KEY = ''/SECRET_KEY = '${SECRET_KEY}'/g" /opt/netbox/netbox/netbox/configuration.py
fi

#generate database

if [[ ( "$(su - postgres -c "psql -l -P format=unaligned" | grep -c "^netbox")" > 0 ) ]] ; then
    echo "Netbox database already exist, please configure manually"
else
    echo "Creating database for netbox"
    DB_NAME="netbox"
    DB_USER="netbox"
    DB_PASSWORD="$(/opt/netbox/venv/bin/python /opt/netbox/netbox/generate_secret_key.py)"
    su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';\""
    sed -iE "s/( +'USER':)[^#]*# PostgreSQL username.*/\1 '${DB_USER}'/g" /opt/netbox/netbox/netbox/configuration.py
    sed -iE "s/( +'NAME':)[^#]*# Database name.*/\1 '${DB_NAME}'/g" /opt/netbox/netbox/netbox/configuration.py
    sed -iE "s/( +'PASSWORD':)[^#]*# PostgreSQL password.*/\1 '${DB_PASSWORD}'/g" /opt/netbox/netbox/netbox/configuration.py
fi

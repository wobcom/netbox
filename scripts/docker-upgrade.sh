#!/usr/bin/env bash

set -e

SCRIPT_PATH=$(readlink -f $0)
REPO_PATH=$(dirname ${SCRIPT_PATH})

cd ${REPO_PATH}/..
echo "Pulling new docker images."
docker-compose pull

systemctl list-units netbox.service --plain --no-pager | grep 'netbox.service'
SYSTEMD_SERVICE=$?

if [ $SYSTEMD_SERVICE == '0' ]; then
  echo "Stopping NetBox"
  systemctl stop netbox.service
  echo "Starting NetBox"
  systemctl start netbox.service
else
  echo "Stopping NetBox"
  docker-compose down
  echo "Starting NetBox"
  docker-compose up -d
fi

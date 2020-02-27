#!/usr/bin/env bash


id -u name
USER_EXISTS=$?

if [[ ( "$USER_EXISTS" > 0 ) ]] ; then
    adduser -d /opt/netbox -U netbox
fi

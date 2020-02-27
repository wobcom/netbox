#!/usr/bin/env bash


id -u name

if [[ "$?" > 0 ]] ; then
    adduser -d /opt/netbox -U netbox
fi

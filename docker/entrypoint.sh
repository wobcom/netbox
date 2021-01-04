#!/bin/bash
# Runs on every start of the Netbox Docker container

# Stop when an error occures
set -e

/opt/netbox/prepare_netbox.sh

# Launch whatever is passed by docker
# (i.e. the RUN instruction in the Dockerfile)
#
# shellcheck disable=SC2068
exec "$@"

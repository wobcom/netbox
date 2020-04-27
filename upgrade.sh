#!/bin/bash
# This script will prepare NetBox to run after the code has been upgraded to
# its most recent release.

cd "$(dirname "$0")"
VIRTUALENV="$(pwd -P)/venv"

# Remove the existing virtual environment (if any)
if [ -d "$VIRTUALENV" ]; then
  COMMAND="rm -rf ${VIRTUALENV}"
  echo "Removing old virtual environment..."
  eval $COMMAND
else
  WARN_MISSING_VENV=1
fi

# Create a new virtual environment
COMMAND="/usr/bin/python3 -m venv ${VIRTUALENV}"
echo "Creating a new virtual environment at ${VIRTUALENV}..."
eval $COMMAND || {
  echo "--------------------------------------------------------------------"
  echo "ERROR: Failed to create the virtual environment. Check that you have"
  echo "the required system packages installed and the following path is"
  echo "writable: ${VIRTUALENV}"
  echo "--------------------------------------------------------------------"
  exit 1
}

# Activate the virtual environment
source "${VIRTUALENV}/bin/activate"

# Install necessary system packages
COMMAND="pip3 install wheel"
echo "Installing Python system packages ($COMMAND)..."
eval $COMMAND || exit 1

# Install required Python packages
COMMAND="pip3 install -r requirements.txt"
echo "Installing core dependencies ($COMMAND)..."
eval $COMMAND || exit 1

# Install optional packages (if any)
if [ -f "local_requirements.txt" ]
then
  COMMAND="pip3 install -r local_requirements.txt"
  echo "Installing local dependencies ($COMMAND)..."
  eval $COMMAND || exit 1
else
  echo "Skipping local dependencies (local_requirements.txt not found)"
fi

# Apply any database migrations
COMMAND="python3 netbox/manage.py migrate"
echo "Applying database migrations ($COMMAND)..."
eval $COMMAND || exit 1

# Collect static files
COMMAND="python3 netbox/manage.py collectstatic --no-input"
echo "Collecting static files ($COMMAND)..."
eval $COMMAND || exit 1

# Delete any stale content types
COMMAND="python3 netbox/manage.py remove_stale_contenttypes --no-input"
echo "Removing stale content types ($COMMAND)..."
eval $COMMAND || exit 1

# Delete any expired user sessions
COMMAND="python3 netbox/manage.py clearsessions"
echo "Removing expired user sessions ($COMMAND)..."
eval $COMMAND || exit 1

# Clear all cached data
COMMAND="python3 netbox/manage.py invalidate all"
echo "Clearing cache data ($COMMAND)..."
eval $COMMAND || exit 1

if [ -v WARN_MISSING_VENV ]; then
  echo "--------------------------------------------------------------------"
  echo "WARNING: No existing virtual environment was detected. A new one has"
  echo "been created. Update your systemd service files to reflect the new"
  echo "Python and gunicorn executables."
  echo ""
  echo "netbox.service ExecStart:"
  echo "  ${VIRTUALENV}/bin/gunicorn"
  echo ""
  echo "netbox-rq.service ExecStart:"
  echo "  ${VIRTUALENV}/bin/python"
  echo ""
  echo "After modifying these files, reload the systemctl daemon:"
  echo "  > systemctl daemon-reload"
  echo "--------------------------------------------------------------------"
fi

echo "Upgrade complete! Don't forget to restart the NetBox services:"
echo "  > sudo systemctl restart netbox netbox-rq"

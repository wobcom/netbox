#! /usr/bin/env bash -x
set -e

branch=${1}

cd /opt/netbox/netbox

# method proposed by https://stackoverflow.com/a/44702187
# git config --global credential.helper store --file=/var/tmp/autodeploy/.git-credentials

eval $(ssh-agent -s)
ssh-add ~/.ssh/ci\@gitlab.service.wobcom.de

# checkout repository
# @branch not working
git checkout ${branch}

git pull

cd /opt/netbox

## update dependencies, do DB migrations, and collect static files
venv/bin/pip install -Ur requirements.txt
venv/bin/python netbox/manage.py migrate
venv/bin/python netbox/manage.py collectstatic --noinput

supervisorctl restart all

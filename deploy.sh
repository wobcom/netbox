#! /usr/bin/env bash -x
set -e

cd /opt/netbox/netbox

# method proposed by https://stackoverflow.com/a/44702187
git config --global credential.helper store --file=/var/tmp/autodeploy/.git-credentials

# checkout repository
# @branch not working
# git pull http://gitlab+deploy-token-3:UhhtBKPa9FL-aBKUe-Ax@gitlab.service.wobcom.de/infrastructure/netbox.git@changes
git checkout changes

git pull

## do DB migrations
venv/bin/python netbox/manage.py migrate

supervisorctl restart all 

#docker login -u mimir_mvp -p R-SUsvUJBQinAzCH6gPp registry.gitlab.com
#docker-compose down --remove-orphans || /bin/true
# clean 
#docker system prune -a -f
#docker rm mimir || /bin/true
#docker pull registry.gitlab.com/wobcom/mimir:latest
#docker-compose up
#docker run -p 80:80 -p 443:443 --name mimir -d registry.gitlab.com/wobcom/mimir:latest
#docker-compose up -d 

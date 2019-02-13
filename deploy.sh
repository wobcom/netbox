#! /usr/bin/env bash -x
set -e

cd /opt/netbox/netbox

git pull http://gitlab+deploy-token-3:UhhtBKPa9FL-aBKUe-Ax@gitlab.service.wobcom.de/infrastructure/netbox.git@changes
#git pull https://gitlab-ci-token:<YOUR_TOKEN>@<GITLAB_INSTANCE_URL>/<USERNAME_OR_GROUPNAME/<REPO_NAME>.git
#http://gitlab.service.wobcom.de/infrastructure/netbox.git

supervisorctl restart all 

#docker login -u mimir_mvp -p R-SUsvUJBQinAzCH6gPp registry.gitlab.com

#docker-compose down --remove-orphans || /bin/true

# clean 
#docker system prune -a -f

#docker rm mimir || /bin/true

#docker pull registry.gitlab.com/wobcom/mimir:latest

#docker-compose up
#docker run -p 80:80 -p 443:443 --name mimir -d registry.gitlab.com/wobcom/mimir:latest
#   docker-compose up -d 


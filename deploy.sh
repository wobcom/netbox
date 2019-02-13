#! /usr/bin/env bash -x
set -e

cd /opt/netbox/netbox

git pull

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


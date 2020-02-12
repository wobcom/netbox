#!/bin/bash

source .env

echo "Obtaining shared gitlab runner token from gitlab"
GITLAB_SHARED_RUNNER_TOKEN=$(docker exec -it $(docker inspect --format="{{.Id}}" "netbox_gitlab") /opt/gitlab/bin/gitlab-psql -qtAX -d "gitlabhq_production" -c "SELECT runners_registration_token FROM application_settings ORDER BY id
DESC LIMIT 1")

echo "Registering gitlab runner with gitlab"

docker exec -it $(docker inspect --format="{{.Id}}" "netbox_gitlab_runner") /usr/bin/gitlab-runner register \
      --non-interactive \
      --url "$GITLAB_URL" \
      --registration-token "$GITLAB_SHARED_RUNNER_TOKEN" \
      --executor "docker" \
      --docker-image "williamyeh/ansible:alpine3" \
      --description "gitlab-runner" \
      --tag-list "docker,changes" \
      --run-untagged \
      --locked="false" \
      --docker-network-mode "netbox_gitlab-network"

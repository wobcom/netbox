#!/bin/bash

echo ">> Creating virtual environment"
python3 -m venv --copies venv
echo ">> Installing requirements to virtual environment"
venv/bin/pip install -r requirements.txt
echo ">> Copy temporary configuration"
cp netbox/netbox/configuration.example.py netbox/netbox/configuration.py
echo ">> Set temporary SECRET_KEY"
sed -i "s/SECRET_KEY = ''/SECRET_KEY = 'sample_key_do_not_use_in_production'/g" netbox/netbox/configuration.py
echo ">> Collect statics"
venv/bin/python netbox/manage.py collectstatic
echo ">> Copy final default configuration"
cp netbox/netbox/configuration.example.py netbox/netbox/configuration.py
echo ">> Rewrite venv egg-links"
for LINK_FILE in venv/lib/python3.6/site-packages/*.egg-link ; do
    sed -iEr "s/^.*\/venv(.*)/\/opt\/netbox\/venv\1/g" ${LINK_FILE}
done

LATEST_GIT_TAG=$(git describe --abbrev=0 --tags)
VERSION=$(echo "${LATEST_GIT_TAG}" | tr - _ | sed -En "s/v(.*)/\\1/p" )
ITERATION=$(git rev-list "${LATEST_GIT_TAG}..HEAD" --count)

echo ">> Build package based on ${LATEST_GIT_TAG}, with version ${VERSION} and iteration ${ITERATION}"

fpm --input-type dir \
    --output-type rpm \
    --prefix /opt/netbox/ \
    --name netbox \
    --version "${VERSION}_${ITERATION}" \
    --depends postgresql96 \
    --depends postgresql96-server \
    --depends redis \
    --depends python3 \
    --config-files netbox/netbox/configuration.py \
    --directories /opt/netbox \
    --after-install scripts/package_scripts/after_install.sh \
    --before-install scripts/package_scripts/before_install.sh \
    --rpm-user netbox \
    --rpm-group netbox \
    ./

FROM python:alpine as builder

RUN apk add --no-cache \
      bash \
      build-base \
      ca-certificates \
      cyrus-sasl-dev \
      graphviz \
      jpeg-dev \
      libevent-dev \
      libffi-dev \
      libxslt-dev \
      openldap-dev \
      postgresql-dev \
      libsasl \
      libldap \
      util-linux

WORKDIR /install

RUN pip install --prefix="/install" --no-warn-script-location daphne

COPY ./requirements.txt /
RUN pip install --prefix="/install" --no-warn-script-location -r /requirements.txt

###
# Main stage
###

FROM builder as main

RUN apk add --no-cache \
      bash \
      ca-certificates \
      graphviz \
      libevent \
      libffi \
      libjpeg-turbo \
      libressl \
      libxslt \
      postgresql-libs \
      ttf-ubuntu-font-family

WORKDIR /opt

COPY --from=builder /install /usr/local

COPY netbox/ /opt/netbox

COPY docker/entrypoint.sh /opt/netbox/docker-entrypoint.sh
COPY docker/nginx.conf /etc/netbox-nginx/nginx.conf

COPY docker/configuration.py /opt/netbox/netbox/configuration.py
COPY docker/ldap_config.py /opt/netbox/netbox/ldap_config.py

COPY docker/config_hook.py /etc/netbox/config/configuration.py
COPY docker/ldap_hook.py /etc/netbox/config/ldap_config.py

WORKDIR /opt/netbox

# Must set permissions for '/opt/netbox/netbox/static' directory
# to g+w so that `./manage.py collectstatic` can be executed during
# container startup.
# Must set permissions for '/opt/netbox/netbox/media' directory
# to g+w so that pictures can be uploaded to netbox.
RUN mkdir static && chmod -R g+w static media

ENTRYPOINT [ "/opt/netbox/docker-entrypoint.sh" ]

CMD ["daphne", "-s netbox", "-b 0.0.0.0", "-p 8002", "netbox.asgi:application"]

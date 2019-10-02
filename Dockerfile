FROM ubuntu:18.04


# TODO: this is tempory to work around the topdesk package not being available
## BEGIN TMP SECTION
RUN set -ex \
    && apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y openssh-client

# Add credentials on build

RUN mkdir /root/.ssh/

# remember to use a temporary variable for this

# make sure your domain is accepted

RUN touch /root/.ssh/known_hosts

RUN ssh-keyscan gitlab.com >> /root/.ssh/known_hosts

## END TMP SECTION

# Copy in your requirements file
ADD requirements.txt /requirements.txt

# OR, if you’re using a directory for your requirements, copy everything (comment out the above and uncomment this if so):
# ADD requirements /requirements

# Install build deps, then run `pip install`, then remove unneeded build deps all in a single step. Correct the path to your production requirements file, if needed.
RUN set -ex \
    && apt update \
    && DEBIAN_FRONTEND=noninteractive apt install -y \
            git \
            postgresql \
            python3 \
            python3-dev \
            python3-pip \
            build-essential \
            libxml2-dev \
            libxslt1-dev \
            libffi-dev \
            graphviz \
            libpq-dev \
            libssl-dev \
            zlib1g-dev \
    && pip3 install virtualenv \
    && virtualenv /venv \
    && /venv/bin/pip install -U pip \
    && /venv/bin/pip install uwsgi \
    && /venv/bin/pip install --no-cache-dir -r /requirements.txt

# Copy your application code to the container (make sure you create a .dockerignore file if any large files or directories should be excluded)
RUN mkdir /code
ADD . /code
WORKDIR /code/

# uWSGI will listen on this port
EXPOSE 8000

# uWSGI configuration (customize as needed):
ENV UWSGI_VIRTUALENV=/venv UWSGI_WSGI_FILE=netbox/wsgi.py UWSGI_HTTP=:8000 UWSGI_MASTER=1 UWSGI_WORKERS=2 UWSGI_THREADS=8 UWSGI_UID=1000 UWSGI_GID=2000 UWSGI_LAZY_APPS=1 UWSGI_WSGI_ENV_BEHAVIOR=holy

# Call collectstatic (customize the following line with the minimal environment variables needed for manage.py to run):
RUN DATABASE_URL=none /venv/bin/python netbox/manage.py collectstatic --noinput

ENTRYPOINT ["/code/docker-entrypoint.sh"]

# Start uWSGI
CMD ["/venv/bin/uwsgi", "--http-auto-chunked", "--http-keepalive", "--py-autoreload", "1", "--static-map", "/static=/code/netbox/static"]
#CMD ["/venv/bin/python", "/code/netbox/manage.py", "runserver", "0.0.0.0:8000"]

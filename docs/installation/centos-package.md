# Installing Netbox from CentOS package

For Wobcom we packaged Netbox for CentOS, currently a unstable repo is available with per-commit-builds of Netbox.
For the near future a stable repository is planned.\
Our repositories mirrors all dependencies of Netbox so you don't need to install `epel-release` or `pgdg` repos as well.

## Install repos

To configure our repos there is a meta package available, which installs the repository
and GPG key. Just install this meta package:

**Unstable**

    yum install http://rpm.service.wobcom.de/meta-packages/repo-wobcom-unstable.rpm
    

## Install Netbox

Now install Netbox like any other `yum` package:

    yum install netbox
    
Now Netbox is installed and the systemd service `netbox` is already started.

## Configure Netbox

During package installation a basic configuration is performed as well,
the package configures a PostgreSQL user and database and generates a unique random `SECRET_KEY`.
Additionally the allowed host will be set to `['*']`.
To change any of this or other settings please follow the [configuration instructions](../configuration/index.md).

## Configure a webserver for Netbox

By default Netbox only listens on `localhost` for HTTP connections.
To provide Netbox as service it's recommended to setup a webserver as proxy.

### NGNIX

For NGINX a sample config is included to netbox, just copy it to NGINX configuration folder and start.

    cp /opt/netbox/exmaples/nginx_netbox.conf /etc/nginx/conf.d/netbox.conf

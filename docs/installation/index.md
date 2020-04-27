# Installation

The following sections detail how to set up a new instance of NetBox:

1. [PostgreSQL database](1-postgresql.md)
1. [Redis](2-redis.md)
3. [NetBox components](3-netbox.md)
4. [HTTP daemon](4-http-daemon.md)
5. [LDAP authentication](5-ldap.md) (optional)

Below is a simplified overview of the NetBox application stack for reference:

![NetBox UI as seen by a non-authenticated user](../media/installation/netbox_application_stack.png)

## CentOS package (Wobcom)

* [Installing CentOS package](centos-package.md)

## Upgrading

If you are upgrading from an existing installation, please consult the [upgrading guide](upgrading.md).

Netbox v2.5.9 and later moved to using systemd instead of supervisord.  Please see the instructions for [migrating to systemd](migrating-to-systemd.md) if you are still using supervisord.

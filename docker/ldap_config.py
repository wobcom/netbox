import ldap
import os
import json
from functools import reduce

from django_auth_ldap.config import LDAPSearch, LDAPGroupQuery
from importlib import import_module

# Read secret from file
def read_secret(secret_name):
    try:
        f = open('/run/secrets/' + secret_name, 'r', encoding='utf-8')
    except EnvironmentError:
        return ''
    else:
        with f:
            return f.readline().strip()

# Import and return the group type based on string name
def import_group_type(group_type_name, arg1, arg2):
    mod = import_module('django_auth_ldap.config')
    if arg1 and arg2:
        return getattr(mod, group_type_name)(arg1, arg2)
    elif arg1:
        return getattr(mod, group_type_name)(arg1)
    else:
        return getattr(mod, group_type_name)()

# Space separted list of server URIs
AUTH_LDAP_SERVER_URI = os.environ.get('AUTH_LDAP_SERVER_URI', '')

# The following may be needed if you are binding to Active Directory.
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}

# Set the DN and password for the NetBox service account.
AUTH_LDAP_BIND_DN = os.environ.get('AUTH_LDAP_BIND_DN', '')
AUTH_LDAP_BIND_PASSWORD = os.environ.get('AUTH_LDAP_BIND_PASSWORD', read_secret('auth_ldap_bind_password'))

# Set a string template that describes any user’s distinguished name based on the username.
AUTH_LDAP_USER_DN_TEMPLATE = os.environ.get('AUTH_LDAP_USER_DN_TEMPLATE', None)

# Enable STARTTLS for ldap authentication.
AUTH_LDAP_START_TLS = os.environ.get('AUTH_LDAP_START_TLS', 'False').lower() == 'true'

# Include this setting if you want to ignore certificate errors. This might be needed to accept a self-signed cert.
# Note that this is a NetBox-specific setting which sets:
#     ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
LDAP_IGNORE_CERT_ERRORS = os.environ.get('LDAP_IGNORE_CERT_ERRORS', 'False').lower() == 'true'

AUTH_LDAP_USER_SEARCH_BASEDN = os.environ.get('AUTH_LDAP_USER_SEARCH_BASEDN', '')
AUTH_LDAP_USER_SEARCH_ATTR = os.environ.get('AUTH_LDAP_USER_SEARCH_ATTR', 'sAMAccountName')
AUTH_LDAP_USER_SEARCH = LDAPSearch(AUTH_LDAP_USER_SEARCH_BASEDN,
                                   ldap.SCOPE_SUBTREE,
                                   "(" + AUTH_LDAP_USER_SEARCH_ATTR + "=%(user)s)")

# This search ought to return all groups to which the user belongs. django_auth_ldap uses this to determine group
# heirarchy.
AUTH_LDAP_GROUP_SEARCH_BASEDN = os.environ.get('AUTH_LDAP_GROUP_SEARCH_BASEDN', '')
AUTH_LDAP_GROUP_SEARCH_CLASS = os.environ.get('AUTH_LDAP_GROUP_SEARCH_CLASS', 'group')
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(AUTH_LDAP_GROUP_SEARCH_BASEDN, ldap.SCOPE_SUBTREE,
                                    "(objectClass=" + AUTH_LDAP_GROUP_SEARCH_CLASS + ")")

# Specify the class name according to
# https://django-auth-ldap.readthedocs.io/en/latest/reference.html#django_auth_ldap.config.LDAPGroupType
# If the constructor requires additional arguments, use AUTH_LDAP_GROUP_TYPE_ARG_1 and _2 to specify them
# accordingly. Keep them unset if they are not required.
arg1 = os.environ.get('AUTH_LDAP_GROUP_TYPE_ARG_1')
arg2 = os.environ.get('AUTH_LDAP_GROUP_TYPE_ARG_2')
AUTH_LDAP_GROUP_TYPE = import_group_type(os.environ.get('AUTH_LDAP_GROUP_TYPE', 'GroupOfNamesType'), arg1, arg2)

g = os.environ.get('AUTH_LDAP_REQUIRE_GROUP', '[]')
l = json.loads(g)
l_ = map(LDAPGroupQuery, l)
AUTH_LDAP_REQUIRE_GROUP = reduce(lambda s, e: e | s, l_)


# Define special user types using groups. Exercise great caution when assigning superuser status.
d = {
    "is_active": os.environ.get('AUTH_LDAP_REQUIRE_GROUP_DN', None),
    "is_staff": os.environ.get('AUTH_LDAP_IS_ADMIN_DN', None),
    "is_superuser": os.environ.get('AUTH_LDAP_IS_SUPERUSER_DN', None)
}

AUTH_LDAP_USER_FLAGS_BY_GROUP = dict((a, b) for (a, b) in d.items() if b is not None)

# For more granular permissions, we can map LDAP groups to Django groups.
AUTH_LDAP_FIND_GROUP_PERMS = os.environ.get('AUTH_LDAP_FIND_GROUP_PERMS', 'True').lower() == 'true'

# Cache groups for one hour to reduce LDAP traffic
AUTH_LDAP_CACHE_TIMEOUT = int(os.environ.get('AUTH_LDAP_CACHE_TIMEOUT', 3600))

# Populate the Django user from the LDAP directory.
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": os.environ.get('AUTH_LDAP_ATTR_FIRSTNAME', 'givenName'),
    "last_name": os.environ.get('AUTH_LDAP_ATTR_LASTNAME', 'sn'),
    "email": os.environ.get('AUTH_LDAP_ATTR_MAIL', 'mail')
}

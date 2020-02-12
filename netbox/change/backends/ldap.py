from django_auth_ldap.backend import LDAPBackend
from . import perm_available


class ProxyBackend(LDAPBackend):
    """
    Proxy class wrapped around LDAPBackend to deny permissions
    based on actual change state.
    """

    def has_perm(self, user_obj, perm, obj=None):
        if perm_available(user_obj, perm):
            return super(ProxyBackend, self).has_perm(user_obj, perm, obj=obj)
        return False

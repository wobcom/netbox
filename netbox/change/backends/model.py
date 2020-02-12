from utilities.auth_backends import ViewExemptModelBackend
from . import perm_available


class ProxyBackend(ViewExemptModelBackend):
    """
    Proxy class wrapped around ModelBackend to deny permissions
    based on actual change state.
    """

    def has_perm(self, user_obj, perm, obj=None):
        if perm_available(user_obj, perm):
            return super(ProxyBackend, self).has_perm(user_obj, perm, obj=obj)
        return False

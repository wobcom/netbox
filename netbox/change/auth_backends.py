from .models import ChangeSet, OWN_CHANGE
from django.conf import settings
from django.utils.module_loading import import_string


def perm_available(user, perm):
    """
    Check if perm is available in actual change state, for given user
    :param user: user to check perm availability for
    :param perm: perm to check
    :return: boolean representation of perm availability
    """
    if not user.is_authenticated:
        return False
    change_state = ChangeSet.change_state(user)

    if change_state != OWN_CHANGE \
            and settings.NEED_CHANGE_FOR_WRITE \
            and not perm.split('.')[-1].startswith('view')\
            and not perm.split('.')[0] == 'change':
        return False
    return True


def proxy_backend_factory(backend_string):

    class ProxyBackend(import_string(backend_string)):
        def has_perm(self, user_obj, perm, obj=None):
            if perm_available(user_obj, perm):
                return super(ProxyBackend, self).has_perm(user_obj, perm, obj=obj)
            return False

    return ProxyBackend


ModelProxyBackend = proxy_backend_factory('utilities.auth_backends.ViewExemptModelBackend')
LDAPProxyBackend = proxy_backend_factory('django_auth_ldap.backend.LDAPBackend')
RemoteAuthProxyBackend = proxy_backend_factory(settings.REMOTE_AUTH_BACKEND)

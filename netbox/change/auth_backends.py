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
    change_state = ChangeSet.change_state(user)

    inside_change = change_state == OWN_CHANGE
    perm_split = perm.split('.')
    is_view = perm_split[-1].startswith('view')
    is_change = perm_split[0] == 'change'
    is_rollback = perm_split[-1].startswith('rollback')

    return inside_change \
        or not settings.NEED_CHANGE_FOR_WRITE \
        or is_view \
        or (is_change and not is_rollback)


def proxy_backend_factory(backend):
    class ProxyBackend(backend):
        def has_perm(self, user_obj, perm, obj=None):
            if perm_available(user_obj, perm):
                return super(ProxyBackend, self).has_perm(user_obj, perm, obj=obj)
            return False

    return ProxyBackend


# Must be explicit class definitions, pickling fails otherwise,
# see (https://gitlab.service.wobcom.de/infrastructure/netbox/issues/90)
class ModelProxyBackend(proxy_backend_factory(import_string('netbox.authentication.ObjectPermissionBackend'))):
    pass


class RemoteAuthProxyBackend(proxy_backend_factory(import_string(settings.REMOTE_AUTH_BACKEND))):
    pass

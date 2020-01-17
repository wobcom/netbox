from ..models import ChangeSet, OWN_CHANGE, FOREIGN_CHANGE
from netbox.settings import configuration


def perm_available(user, perm):
    """
    Check if perm is available in actual change state, for given user
    :param user: user to check perm availability for
    :param perm: perm to check
    :return: boolean representation of perm availability
    """
    change_state = ChangeSet.change_state(user)

    if change_state != OWN_CHANGE \
            and configuration.NEED_CHANGE_FOR_WRITE \
            and not perm.split('.')[-1].startswith('view'):
        return False
    return True

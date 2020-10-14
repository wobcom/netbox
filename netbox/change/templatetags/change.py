from django import template
from django.conf import ImproperlyConfigured

from ..models import ProvisionSet

register = template.Library()


@register.filter()
def can_rollback(provision_set, user):
    return provision_set.can_rollback(user)

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

default_app_config = 'slack_integration.apps.SlackConfig'

# check that django-rq is installed
if settings.SLACK_ENABLED:
    try:
        import django_rq
    except ImportError:
        raise ImproperlyConfigured(
            "django-rq is not installed! You must install this package per "
            "the documentation to use the slack integration."
        )

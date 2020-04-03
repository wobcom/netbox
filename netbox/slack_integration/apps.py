from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class SlackConfig(AppConfig):
    name = 'slack_integration'

    verbose_name = 'Slack'

    def ready(self):

        # Check that we can connect to the configured Redis database if webhooks are enabled.
        if settings.SLACK_ENABLED:
            try:
                import redis
            except ImportError:
                raise ImproperlyConfigured(
                    "SLACK_ENABLED is True but the redis Python package is not installed. (Try 'pip install "
                    "redis'.)"
                )
            try:
                rs = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DATABASE,
                    password=settings.REDIS_PASSWORD or None,
                    ssl=settings.REDIS_SSL,
                )
                rs.ping()
            except redis.exceptions.ConnectionError:
                raise ImproperlyConfigured(
                    "Unable to connect to the Redis database. Check that the Redis configuration has been defined in "
                    "configuration.py."
                )

            from .signals import update_message_receivers, install_message_model_receivers
            install_message_model_receivers()
            update_message_receivers()

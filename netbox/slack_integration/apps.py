import logging

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ProgrammingError

logger = logging.getLogger()


class SlackConfig(AppConfig):
    name = 'slack_integration'

    verbose_name = 'Slack'

    def ready(self):

        # Check that we can connect to the configured Redis database if webhooks are enabled.
        if settings.SLACK_ENABLED:
            try:
                from .signals import update_message_receivers, install_message_model_receivers
                install_message_model_receivers()
                update_message_receivers()
            except ProgrammingError:
                logger.critical('Migration missing')

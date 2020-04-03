from slack import WebClient

from django_rq import job
from django.template import Template, Context
from django.conf import settings

from slack_integration.models import SlackMessage


@job('default')
def handle_slack_message(message, obj):
    """
    Compiles message template and send slack message
    :type message: SlackMessage
    :param message: slack message object
    :param obj:
    """
    if settings.SLACK_ENABLED:
        message.refresh_from_db()
        context = Context({'object': obj})
        template = Template(message.template)
        rendered_message = template.render(context)
        if rendered_message.strip() == '':
            return

        slack_client = WebClient(token=settings.SLACK_TOKEN)

        for channel in message.slack_channels.all():
            slack_client.chat_postMessage(
                channel=channel.name,
                text=rendered_message,
            )

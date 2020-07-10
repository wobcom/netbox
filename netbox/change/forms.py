from topdesk import Topdesk, NotFound
from urllib.parse import quote

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from utilities.forms import BootstrapMixin
from change.models import ChangeInformation


def topdesk_number_validator(value):
    if not settings.TOPDESK_URL:
        return

    if not value:
        raise ValidationError({
            'topdesk_change_number': "Cannot leave TOPdesk change number empty unless it’s an emergency."
        })

    topdesk = Topdesk(settings.TOPDESK_URL,
                      verify=settings.TOPDESK_SSL_VERIFICATION,
                      app_creds=(settings.TOPDESK_USER, settings.TOPDESK_TOKEN))
    try:
        topdesk.operator_change(id_=quote(value))
    except NotFound:
        raise ValidationError({
            'topdesk_change_number': "{} is not an existing Topdesk ticket number.".format(value)
        })


class ChangeInformationForm(BootstrapMixin, forms.ModelForm):
    topdesk_change_number = forms.CharField(
        label='TOPdesk Change',
        help_text='Follows the scheme CHXXXX-XXXX',
        required=False
    )

    class Meta:
        model = ChangeInformation
        fields = '__all__'

    def clean(self):
        topdesk_number = self.cleaned_data.get("topdesk_change_number")
        is_emergency = self.cleaned_data.get("is_emergency")

        if not is_emergency:
            topdesk_number_validator(topdesk_number)

        if is_emergency and topdesk_number:
            raise ValidationError({
                'topdesk_change_number': "Cannot set TOPdesk change number on emergency change"
            })

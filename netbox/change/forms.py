from topdesk import Topdesk, HttpException
from urllib.parse import quote

from django import forms
from django.core.exceptions import ValidationError

from utilities.forms import BootstrapMixin
from change.models import ChangeInformation
from netbox import configuration


def topdesk_number_validator(value):
    if not configuration.TOPDESK_URL:
        return
    topdesk = Topdesk(configuration.TOPDESK_URL,
                      verify=configuration.TOPDESK_SSL_VERIFICATION,
                      app_creds=(configuration.TOPDESK_USER, configuration.TOPDESK_TOKEN))
    try:
        topdesk.operator_change(id_=quote(value))
    except HttpException:
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

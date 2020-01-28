from topdesk import Topdesk, HttpException
from urllib.parse import quote

from django import forms
from django.core.exceptions import ValidationError

from utilities.forms import BootstrapMixin
from change.models import ChangeInformation
from netbox import configuration


def topdesk_number_validator(value):
    topdesk = Topdesk(configuration.TOPDESK_URL,
                      verify=configuration.TOPDESK_SSL_VERIFICATION,
                      app_creds=(configuration.TOPDESK_USER, configuration.TOPDESK_TOKEN))
    try:
        topdesk.operator_change(id_=quote(value))
    except HttpException:
        raise ValidationError("%(value)s is not an existing Topdesk ticket number.",
                              params={'value': value})


class ChangeInformationForm(BootstrapMixin, forms.ModelForm):
    topdesk_change_number = forms.CharField(validators=(topdesk_number_validator,))

    class Meta:
        model = ChangeInformation
        fields = '__all__'


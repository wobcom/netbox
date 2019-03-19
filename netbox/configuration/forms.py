from django import forms
from utilities.forms import BootstrapMixin

from .models import BGPConfiguration

class BGPForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = BGPConfiguration
        fields = ['neighbor', 'remote_as']
        labels = {
            'neighbor': 'BGP neighbor',
            'remote_as': 'Remote AS',
        }


class BGPCSVForm(forms.ModelForm):
    class Meta:
        model = BGPConfiguration
        fields = BGPConfiguration.csv_headers
        help_texts = {
            'neighbor': 'BGP neighbor',
            'remote_as': 'Remote AS',
        }


class BGPFilterForm(BootstrapMixin, forms.Form):
    model = BGPConfiguration
    q = forms.CharField(
        required=False,
        label='Search'
    )

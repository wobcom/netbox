from django import forms
from utilities.forms import BootstrapMixin, FilterChoiceField

from .models import BGPConfiguration

from dcim.models import Device

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
    devices = FilterChoiceField(
        queryset=Device.objects,
        null_label='-- None --'
    )
    neighbor = forms.CharField(
        label='Neighbor IP',
        required=False,
    )
    remote_as = forms.IntegerField(
        label='Remote AS',
        required=False,
    )

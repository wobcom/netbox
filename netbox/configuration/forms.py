from django import forms
from utilities.forms import BootstrapMixin, FilterChoiceField

from .models import BGPSession, BGPCommunity

from dcim.models import Device

class BGPForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = BGPSession
        fields = ['neighbor', 'remote_as', 'community', 'description']
        labels = {
            'neighbor': 'BGP neighbor',
            'remote_as': 'Remote AS',
            'description': 'Neighbor Description',
            'community': 'BGP Community',
        }


class BGPCSVForm(forms.ModelForm):
    class Meta:
        model = BGPSession
        fields = BGPSession.csv_headers
        help_texts = {
            'neighbor': 'BGP neighbor',
            'remote_as': 'Remote AS',
            'description': 'Neighbor Description',
        }


class BGPFilterForm(BootstrapMixin, forms.Form):
    model = BGPSession
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
    community = FilterChoiceField(
        queryset=BGPCommunity.objects,
        null_label='-- None --'
    )


class CommunityForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = BGPCommunity
        fields = ['name', 'description']
        labels = {
            'name': 'BGP Community Name',
            'description': 'BGP Description',
        }


class CommunityCSVForm(forms.ModelForm):
    class Meta:
        model = BGPCommunity
        fields = BGPCommunity.csv_headers
        help_texts = {
            'name': 'BGP Community Name',
            'description': 'BGP Description',
        }


class CommunityFilterForm(BootstrapMixin, forms.Form):
    model = BGPCommunity
    q = forms.CharField(
        required=False,
        label='Search'
    )
    name = forms.CharField(
        label='Community Name',
        required=False,
    )

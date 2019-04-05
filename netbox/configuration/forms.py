from django import forms
from utilities.forms import BootstrapMixin, FilterChoiceField

from .models import BGPSession, BGPCommunity, BGP_INTERNAL, BGP_EXTERNAL

from extras.forms import CustomFieldForm
from dcim.models import Device

class BGPExternalForm(BootstrapMixin, CustomFieldForm):
    tag = forms.IntegerField(
        widget=forms.HiddenInput(), initial=BGP_EXTERNAL,
    )

    def __init__(self, *args, **kwargs):
        kwargs.update({
            'initial': {**(kwargs.get('initial', {})), 'tag': BGP_EXTERNAL}
        })
        super().__init__(*args, **kwargs)

    class Meta:
        model = BGPSession
        fields = [
            'tag', 'neighbor', 'remote_as', 'communities', 'description', 'vrf'
        ]
        labels = {
            'neighbor': 'BGP neighbor',
            'remote_as': 'Remote AS',
            'description': 'Neighbor Description',
            'communities': 'BGP Communities',
            'vrf': 'The VRF this session relates to',
        }


class BGPInternalForm(BootstrapMixin, CustomFieldForm):
    tag = forms.IntegerField(
        widget=forms.HiddenInput(), initial=BGP_INTERNAL,
    )
    class Meta:
        model = BGPSession
        fields = [
            'tag', 'device_a', 'device_a_as', 'device_b', 'device_b_as',
            'communities', 'description', 'vrf',
        ]
        labels = {
            'device_a': 'Device A',
            'device_a_as': 'Device A AS',
            'device_b': 'Device B',
            'device_b_as': 'Device B AS',
            'description': 'Neighbor Description',
            'communities': 'BGP Communities',
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
        fields = ['name', 'community', 'description']
        labels = {
            'name': 'BGP Community Name',
            'community': 'BGP Community',
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

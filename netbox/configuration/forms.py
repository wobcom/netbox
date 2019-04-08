from django import forms
from django.db.models import Count, Q
from django.forms.models import ModelChoiceIterator, ModelChoiceField

from .models import BGPSession, BGPCommunity, BGP_INTERNAL, BGP_EXTERNAL

from extras.forms import CustomFieldForm
from dcim.models import Device, Interface
from ipam.models import IPAddress
from utilities.forms import BootstrapMixin, FilterChoiceField

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


# nb: we could make this generic, but because of multiple indirection this
# wouldn’t add a ton of value. should tis pattern ever arise again, making this
# generic shouldn't be too much work.
class GroupedIPByDeviceIterator(ModelChoiceIterator):
    def __init__(self, field):
        super().__init__(field)

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        # sadly we cant do this via queryset, the modelchoice will not validate
        query = Interface.objects.prefetch_related(
            'device',
            'ip_addresses'
        )
        query = query.filter(ip_addresses__isnull=False).distinct()
        for elem in query.order_by('device__name'):
            yield ("{} - {}".format(elem.device, elem),
                   [self.choice(ip) for ip in elem.ip_addresses.all()])


class GroupedIPByDeviceField(ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.iterator = GroupedIPByDeviceIterator
        super().__init__(*args, **kwargs)


class BGPInternalForm(BootstrapMixin, CustomFieldForm):
    tag = forms.IntegerField(
        widget=forms.HiddenInput(), initial=BGP_INTERNAL,
    )
    neighbor_a = GroupedIPByDeviceField(
        queryset=IPAddress.objects.all(),
        label="Neighbor A"
    )
    neighbor_b = GroupedIPByDeviceField(
        queryset=IPAddress.objects.all(),
        label="Neighbor B"
    )
    class Meta:
        model = BGPSession
        fields = [
            'tag', 'neighbor_a', 'neighbor_a_as', 'neighbor_b', 'neighbor_b_as',
            'communities', 'description', 'vrf',
        ]
        labels = {
            'neighbor_a': 'Neighbor A',
            'neighbor_a_as': 'Neighbor A AS',
            'neighbor_b': 'Neighbor B',
            'neighbor_b_as': 'Neighbor B AS',
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

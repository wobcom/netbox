from codemirror2.widgets import CodeMirrorEditor
from django import forms
from django.forms.models import ModelChoiceIterator, ModelChoiceField

from .models import (
    BGPCommunity, BGPCommunityList, RouteMap, BGPASN, BGPNeighbor, BGPDeviceASN
)

from extras.forms import CustomFieldForm
from dcim.models import Interface, Device
from ipam.models import IPAddress
from utilities.forms import (
    ChainedModelChoiceField, APISelect, BootstrapMixin, FilterChoiceField,
    SlugField
)

# nb: we could make this generic, but because of multiple indirection this
# wouldn’t add a ton of value. should tis pattern ever arise again, making this
# generic shouldn't be too much work.
class GroupedInterfaceByDeviceIterator(ModelChoiceIterator):
    def __init__(self, field):
        super().__init__(field)

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        # sadly we cant do this via queryset, the modelchoice will not validate
        query = Device.objects.prefetch_related(
            'interfaces',
        )
        for elem in query.all():
            yield ("{}".format(elem),
                   [self.choice(i) for i in elem.interfaces.all()])


class GroupedInterfaceByDeviceField(ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self.iterator = GroupedInterfaceByDeviceIterator
        super().__init__(*args, **kwargs)


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


class CommunityListForm(BootstrapMixin, forms.ModelForm):
    name = SlugField
    class Meta:
        model = BGPCommunityList
        fields = ['name']
        labels = {
            'name': 'Community List Name',
        }


class CommunityListCSVForm(forms.ModelForm):
    class Meta:
        model = BGPCommunityList
        fields = BGPCommunityList.csv_headers
        help_texts = {
            'name': 'BGP Community Name',
            'communities': 'Communities',
        }


class CommunityListFilterForm(BootstrapMixin, forms.Form):
    model = BGPCommunityList
    name = forms.CharField(
        label='List Name',
        required=False,
    )


class RouteMapForm(BootstrapMixin, forms.ModelForm):
    configuration = forms.CharField(
        widget=CodeMirrorEditor(options={'mode': 'yaml', 'lineNumbers': True}, script_template='configuration/codemirror.html')
    )

    class Meta:
        model = RouteMap
        fields = ['name', 'configuration']
        labels = {
            'name': 'BGP Routemap Name',
        }


class RouteMapCSVForm(forms.ModelForm):
    class Meta:
        model = RouteMap
        fields = RouteMap.csv_headers
        help_texts = {
            'name': 'BGP Routemap Name',
            'configuration': 'Routemap Configuration',
        }


class RouteMapFilterForm(BootstrapMixin, forms.Form):
    model = RouteMap
    q = forms.CharField(
        required=False,
        label='Search'
    )
    name = forms.CharField(
        label='Routemap Name',
        required=False,
    )


class BGPASNForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = BGPASN
        fields = ['asn', 'networks', 'redistribute_connected']
        labels = {
            'asn': 'AS Number',
            'networks': 'Networks to expose',
        }


class BGPASNCSVForm(forms.ModelForm):
    class Meta:
        model = BGPASN
        fields = BGPASN.csv_headers
        help_texts = {
            'asn': 'AS Number',
            'networks': 'Networks to expose',
        }


class BGPNeighborForm(BootstrapMixin, forms.ModelForm):
    internal_neighbor_ip = ChainedModelChoiceField(
        queryset=IPAddress.objects.filter(),
        chains={
            'interface_device': 'internal_neighbor_device',
        },
        widget=APISelect(
            api_url='/api/ipam/ip-addresses/?device_id={{internal_neighbor_device}}',
            display_field='address',
        ),
        label='Internal Neighbor IP',
        required=False,
    )

    # this field is the one displayed, but it doesn't get sent (see also
    # deviceasn)
    deviceasn_dummy = FilterChoiceField(
        queryset=BGPDeviceASN.objects.all(),
        widget=forms.Select(attrs={'disabled': True}),
        label='Device ASN link',
    )

    def __init__(self, *args, initial=None, instance=None, **kwargs):
        super().__init__(*args, initial=initial, instance=instance, **kwargs)

        if initial and 'deviceasn' in initial:
            deviceasn = BGPDeviceASN.objects.get(pk=initial['deviceasn'])
            self.fields['source_interface'].queryset = Interface.objects.filter(
                device=deviceasn.device
            )
        if instance and instance.deviceasn_id:
            self.fields['source_interface'].queryset = Interface.objects.filter(
                device=instance.deviceasn.device
            )

    def clean(self):
        if self.cleaned_data['neighbor_type'] == 'internal':
            if self.cleaned_data['internal_neighbor_device'] is None :
                self._errors['internal_neighbor_device'] = self.error_class(['Must be set on Neighbor Type: Internal'])
            if 'internal_neighbor_ip' not in self.cleaned_data or self.cleaned_data['internal_neighbor_ip'] is None:
                self._errors['internal_neighbor_ip'] = self.error_class(['Must be set on Neighbor Type: Internal'])
        elif self.cleaned_data['neighbor_type'] == 'external':
            if self.cleaned_data.get('external_neighbor', None) is '':
                self._errors['external_neighbor'] = self.error_class(['Must be set on Neighbor Type: External'])

    class Meta:
        model = BGPNeighbor
        fields = [
            'deviceasn', 'deviceasn_dummy', 'neighbor_type',
            'internal_neighbor_device', 'internal_neighbor_ip',
            'external_neighbor', 'status', 'routemap_in', 'routemap_out',
            'remote_asn', 'source_interface', 'next_hop_self', 'remove_private_as',
            'send_community', 'soft_reconfiguration', 'description',
        ]
        labels = {
            'neighbor_type': 'Neighbor Type',
            'internal_neighbor_device': 'Internal Neighbor Device',
            'internal_neighbor_ip': 'Internal Neighbor IP',
            'external_neighbor': 'External Neighbor',
            'routemap_in': 'Routemap ingress',
            'routemap_out': 'Routemap egress',
            'remote_asn': 'Remote ASN',
            'source_interface': 'Source Interface',
            'remove_private_as': 'Remove private AS',
        }
        widgets = {
            'deviceasn': forms.HiddenInput(),
            'internal_neighbor_device': forms.Select(attrs={'filter-for': 'internal_neighbor_ip'})
        }


class BGPDeviceASNForm(BootstrapMixin, forms.ModelForm):

    class Meta:
        model = BGPDeviceASN

        fields = ['device', 'asn', 'excluded_prefixes', 'additional_prefixes', 'redistribute_connected']

        labels = {
            'asn': 'ASN',
            'excluded_prefixes': 'Excluded Prefixes',
            'additional_prefixes': 'Additional Prefixes',
            'redistribute_connected': 'Redistribute Connected',
        }

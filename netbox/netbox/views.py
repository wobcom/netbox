from collections import OrderedDict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, F
from django.shortcuts import render
from django.views.generic import View
from packaging import version
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from circuits.filters import CircuitFilterSet, ProviderFilterSet
from circuits.models import Circuit, Provider
from circuits.tables import CircuitTable, ProviderTable
from dcim.filters import (
    CableFilterSet, DeviceFilterSet, DeviceTypeFilterSet, PowerFeedFilterSet, RackFilterSet, RackGroupFilterSet,
    SiteFilterSet, VirtualChassisFilterSet, InterfaceFilterSet,
)
from dcim.models import (
    Cable, ConsolePort, Device, DeviceType, Interface, PowerPanel, PowerFeed, PowerPort, Rack, RackGroup, Site,
    VirtualChassis,
)
from dcim.tables import (
    CableTable, DeviceTable, DeviceTypeTable, PowerFeedTable, RackTable, RackGroupTable, SiteTable,
    VirtualChassisTable, InterfaceTable,
)
from extras.choices import JobResultStatusChoices
from extras.models import ObjectChange, JobResult, Tag
from extras.filters import TagFilterSet
from extras.tables import BaseTagTable
from ipam.filters import AggregateFilterSet, IPAddressFilterSet, PrefixFilterSet, VLANFilterSet, VRFFilterSet
from ipam.models import Aggregate, IPAddress, Prefix, VLAN, VRF
from ipam.tables import AggregateTable, IPAddressTable, PrefixTable, VLANTable, VRFTable
from netbox.releases import get_latest_release
from secrets.filters import SecretFilterSet
from secrets.models import Secret
from secrets.tables import SecretTable
from tenancy.filters import TenantFilterSet
from tenancy.models import Tenant
from tenancy.tables import TenantTable
from utilities.utils import get_subquery
from virtualization.filters import ClusterFilterSet, VirtualMachineFilterSet
from virtualization.models import Cluster, VirtualMachine
from virtualization.tables import ClusterTable, VirtualMachineDetailTable
from .forms import SearchForm

SEARCH_MAX_RESULTS = 15
SEARCH_TYPES = OrderedDict((
    # Circuits
    ('provider', {
        'queryset': Provider.objects.annotate(
            count_circuits=Count('circuits')
        ).order_by(*Provider._meta.ordering),
        'filterset': ProviderFilterSet,
        'table': ProviderTable,
        'url': 'circuits:provider_list',
    }),
    ('circuit', {
        'queryset': Circuit.objects.prefetch_related(
            'type', 'provider', 'tenant', 'terminations__site'
        ).annotate_sites(),
        'filterset': CircuitFilterSet,
        'table': CircuitTable,
        'url': 'circuits:circuit_list',
    }),
    # DCIM
    ('site', {
        'queryset': Site.objects.prefetch_related('region', 'tenant'),
        'filterset': SiteFilterSet,
        'table': SiteTable,
        'url': 'dcim:site_list',
    }),
    ('rack', {
        'queryset': Rack.objects.prefetch_related('site', 'group', 'tenant', 'role'),
        'filterset': RackFilterSet,
        'table': RackTable,
        'url': 'dcim:rack_list',
    }),
    ('rackgroup', {
        'queryset': RackGroup.objects.prefetch_related('site').annotate(
            rack_count=Count('racks')
        ).order_by(*RackGroup._meta.ordering),
        'filterset': RackGroupFilterSet,
        'table': RackGroupTable,
        'url': 'dcim:rackgroup_list',
    }),
    ('devicetype', {
        'queryset': DeviceType.objects.prefetch_related('manufacturer').annotate(
            instance_count=Count('instances')
        ).order_by(*DeviceType._meta.ordering),
        'filterset': DeviceTypeFilterSet,
        'table': DeviceTypeTable,
        'url': 'dcim:devicetype_list',
    }),
    ('device', {
        'queryset': Device.objects.prefetch_related(
            'device_type__manufacturer', 'device_role', 'tenant', 'site', 'rack', 'primary_ip4', 'primary_ip6',
        ),
        'filterset': DeviceFilterSet,
        'table': DeviceTable,
        'url': 'dcim:device_list',
    }),
    ('interface', {
        'permission': 'dcim.view_interface',
        'queryset': Interface.objects.prefetch_related('device'),
        'filterset': InterfaceFilterSet,
        'table': InterfaceTable,
        'url': 'dcim:interface_list',
    }),
    ('virtualchassis', {
        'queryset': VirtualChassis.objects.prefetch_related('master').annotate(
            member_count=Count('members', distinct=True)
        ).order_by(*VirtualChassis._meta.ordering),
        'filterset': VirtualChassisFilterSet,
        'table': VirtualChassisTable,
        'url': 'dcim:virtualchassis_list',
    }),
    ('cable', {
        'queryset': Cable.objects.all(),
        'filterset': CableFilterSet,
        'table': CableTable,
        'url': 'dcim:cable_list',
    }),
    ('powerfeed', {
        'queryset': PowerFeed.objects.all(),
        'filterset': PowerFeedFilterSet,
        'table': PowerFeedTable,
        'url': 'dcim:powerfeed_list',
    }),
    # Virtualization
    ('cluster', {
        'queryset': Cluster.objects.prefetch_related('type', 'group').annotate(
            device_count=get_subquery(Device, 'cluster'),
            vm_count=get_subquery(VirtualMachine, 'cluster')
        ),
        'filterset': ClusterFilterSet,
        'table': ClusterTable,
        'url': 'virtualization:cluster_list',
    }),
    ('virtualmachine', {
        'queryset': VirtualMachine.objects.prefetch_related(
            'cluster', 'tenant', 'platform', 'primary_ip4', 'primary_ip6',
        ),
        'filterset': VirtualMachineFilterSet,
        'table': VirtualMachineDetailTable,
        'url': 'virtualization:virtualmachine_list',
    }),
    # IPAM
    ('vrf', {
        'queryset': VRF.objects.prefetch_related('tenant'),
        'filterset': VRFFilterSet,
        'table': VRFTable,
        'url': 'ipam:vrf_list',
    }),
    ('aggregate', {
        'queryset': Aggregate.objects.prefetch_related('rir'),
        'filterset': AggregateFilterSet,
        'table': AggregateTable,
        'url': 'ipam:aggregate_list',
    }),
    ('prefix', {
        'queryset': Prefix.objects.prefetch_related('site', 'vrf__tenant', 'tenant', 'vlan', 'role'),
        'filterset': PrefixFilterSet,
        'table': PrefixTable,
        'url': 'ipam:prefix_list',
    }),
    ('ipaddress', {
        'queryset': IPAddress.objects.prefetch_related('vrf__tenant', 'tenant'),
        'filterset': IPAddressFilterSet,
        'table': IPAddressTable,
        'url': 'ipam:ipaddress_list',
    }),
    ('vlan', {
        'queryset': VLAN.objects.prefetch_related('site', 'group', 'tenant', 'role'),
        'filterset': VLANFilterSet,
        'table': VLANTable,
        'url': 'ipam:vlan_list',
    }),
    # Secrets
    ('secret', {
        'queryset': Secret.objects.prefetch_related('role', 'device'),
        'filterset': SecretFilterSet,
        'table': SecretTable,
        'url': 'secrets:secret_list',
    }),
    # Tenancy
    ('tenant', {
        'queryset': Tenant.objects.prefetch_related('group'),
        'filterset': TenantFilterSet,
        'table': TenantTable,
        'url': 'tenancy:tenant_list',
    }),
    # Tags
    ('tags', {
        'permission': 'tags.view_tags',
        'queryset': Tag.objects.annotate(
            items=Count('extras_taggeditem_items', distinct=True)
        ),
        'filterset': TagFilterSet,
        'table': BaseTagTable,
        'url': 'extras:tag_list',
    })
))


class HomeView(View):
    template_name = 'home.html'

    def get(self, request):

        connected_consoleports = ConsolePort.objects.restrict(request.user, 'view').filter(
            connected_endpoint__isnull=False
        )
        connected_powerports = PowerPort.objects.restrict(request.user, 'view').filter(
            _connected_poweroutlet__isnull=False
        )
        connected_interfaces = Interface.objects.restrict(request.user, 'view').filter(
            _connected_interface__isnull=False,
            pk__lt=F('_connected_interface')
        )

        # Report Results
        report_content_type = ContentType.objects.get(app_label='extras', model='report')
        report_results = JobResult.objects.filter(
            obj_type=report_content_type,
            status__in=JobResultStatusChoices.TERMINAL_STATE_CHOICES
        ).defer('data')[:10]

        stats = {

            # Organization
            'site_count': Site.objects.restrict(request.user, 'view').count(),
            'tenant_count': Tenant.objects.restrict(request.user, 'view').count(),

            # DCIM
            'rack_count': Rack.objects.restrict(request.user, 'view').count(),
            'devicetype_count': DeviceType.objects.restrict(request.user, 'view').count(),
            'device_count': Device.objects.restrict(request.user, 'view').count(),
            'interface_count': Interface.objects.count(),
            'interface_connections_count': connected_interfaces.count(),
            'cable_count': Cable.objects.restrict(request.user, 'view').count(),
            'console_connections_count': connected_consoleports.count(),
            'power_connections_count': connected_powerports.count(),
            'powerpanel_count': PowerPanel.objects.restrict(request.user, 'view').count(),
            'powerfeed_count': PowerFeed.objects.restrict(request.user, 'view').count(),

            # IPAM
            'vrf_count': VRF.objects.restrict(request.user, 'view').count(),
            'aggregate_count': Aggregate.objects.restrict(request.user, 'view').count(),
            'prefix_count': Prefix.objects.restrict(request.user, 'view').count(),
            'ipaddress_count': IPAddress.objects.restrict(request.user, 'view').count(),
            'vlan_count': VLAN.objects.restrict(request.user, 'view').count(),

            # Circuits
            'provider_count': Provider.objects.restrict(request.user, 'view').count(),
            'circuit_count': Circuit.objects.restrict(request.user, 'view').count(),

            # Secrets
            'secret_count': Secret.objects.restrict(request.user, 'view').count(),

            # Virtualization
            'cluster_count': Cluster.objects.restrict(request.user, 'view').count(),
            'virtualmachine_count': VirtualMachine.objects.restrict(request.user, 'view').count(),

        }

        changelog = ObjectChange.objects.restrict(request.user, 'view').prefetch_related('user', 'changed_object_type')

        # Check whether a new release is available. (Only for staff/superusers.)
        new_release = None
        if request.user.is_staff or request.user.is_superuser:
            latest_release, release_url = get_latest_release()
            if isinstance(latest_release, version.Version):
                current_version = version.parse(settings.VERSION)
                if latest_release > current_version:
                    new_release = {
                        'version': str(latest_release),
                        'url': release_url,
                    }

        return render(request, self.template_name, {
            'search_form': SearchForm(),
            'stats': stats,
            'report_results': report_results,
            'changelog': changelog[:15],
            'new_release': new_release,
        })


class SearchView(View):

    def get(self, request):

        # No query
        if 'q' not in request.GET:
            return render(request, 'search.html', {
                'form': SearchForm(),
            })

        form = SearchForm(request.GET)
        results = []

        if form.is_valid():

            if form.cleaned_data['obj_type']:
                # Searching for a single type of object
                obj_types = [form.cleaned_data['obj_type']]
            else:
                # Searching all object types
                obj_types = SEARCH_TYPES.keys()

            for obj_type in obj_types:

                queryset = SEARCH_TYPES[obj_type]['queryset'].restrict(request.user, 'view')
                filterset = SEARCH_TYPES[obj_type]['filterset']
                table = SEARCH_TYPES[obj_type]['table']
                url = SEARCH_TYPES[obj_type]['url']

                # Construct the results table for this object type
                filtered_queryset = filterset({'q': form.cleaned_data['q']}, queryset=queryset).qs
                table = table(filtered_queryset, orderable=False)
                table.paginate(per_page=SEARCH_MAX_RESULTS)

                if table.page:
                    results.append({
                        'name': queryset.model._meta.verbose_name_plural,
                        'table': table,
                        'url': '{}?q={}'.format(reverse(url), form.cleaned_data['q'])
                    })

        return render(request, 'search.html', {
            'form': form,
            'results': results,
        })


class StaticMediaFailureView(View):
    """
    Display a user-friendly error message with troubleshooting tips when a static media file fails to load.
    """
    def get(self, request):
        return render(request, 'media_failure.html', {
            'filename': request.GET.get('filename')
        })


class APIRootView(APIView):
    _ignore_model_permissions = True
    exclude_from_schema = True
    swagger_schema = None

    def get_view_name(self):
        return "API Root"

    def get(self, request, format=None):

        return Response(OrderedDict((
            ('circuits', reverse('circuits-api:api-root', request=request, format=format)),
            ('dcim', reverse('dcim-api:api-root', request=request, format=format)),
            ('extras', reverse('extras-api:api-root', request=request, format=format)),
            ('ipam', reverse('ipam-api:api-root', request=request, format=format)),
            ('plugins', reverse('plugins-api:api-root', request=request, format=format)),
            ('secrets', reverse('secrets-api:api-root', request=request, format=format)),
            ('tenancy', reverse('tenancy-api:api-root', request=request, format=format)),
            ('users', reverse('users-api:api-root', request=request, format=format)),
            ('virtualization', reverse('virtualization-api:api-root', request=request, format=format)),
        )))

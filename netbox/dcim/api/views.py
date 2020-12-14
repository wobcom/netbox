import socket
from collections import OrderedDict

from django.conf import settings
from django.db.models import F
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.openapi import Parameter
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.viewsets import GenericViewSet, ViewSet

from circuits.models import Circuit
from dcim import filters
from dcim.models import (
    Cable, ConsolePort, ConsolePortTemplate, ConsoleServerPort, ConsoleServerPortTemplate, Device, DeviceBay,
    DeviceBayTemplate, DeviceRole, DeviceType, FrontPort, FrontPortTemplate, Interface, InterfaceTemplate,
    Manufacturer, InventoryItem, Platform, PowerFeed, PowerOutlet, PowerOutletTemplate, PowerPanel, PowerPort,
    PowerPortTemplate, Rack, RackGroup, RackReservation, RackRole, RearPort, RearPortTemplate, Region, Site,
    VirtualChassis,
)
from extras.api.serializers import RenderedGraphSerializer
from extras.api.views import ConfigContextQuerySetMixin, CustomFieldModelViewSet
from extras.models import Graph
from ipam.models import Prefix, VLAN
from utilities.api import (
    get_serializer_for_model, IsAuthenticatedOrLoginNotRequired, ModelViewSet, ServiceUnavailable,
)
from utilities.utils import get_subquery
from utilities.metadata import ContentTypeMetadata
from virtualization.models import VirtualMachine
from . import serializers
from .exceptions import MissingFilterException


class DCIMRootView(APIRootView):
    """
    DCIM API root view
    """
    def get_view_name(self):
        return 'DCIM'


# Mixins

class CableTraceMixin(object):

    @action(detail=True, url_path='trace')
    def trace(self, request, pk):
        """
        Trace a complete cable path and return each segment as a three-tuple of (termination, cable, termination).
        """
        obj = get_object_or_404(self.queryset, pk=pk)

        # Initialize the path array
        path = []

        for near_end, cable, far_end in obj.trace()[0]:

            # Serialize each object
            serializer_a = get_serializer_for_model(near_end, prefix='Nested')
            x = serializer_a(near_end, context={'request': request}).data
            if cable is not None:
                y = serializers.TracedCableSerializer(cable, context={'request': request}).data
            else:
                y = None
            if far_end is not None:
                serializer_b = get_serializer_for_model(far_end, prefix='Nested')
                z = serializer_b(far_end, context={'request': request}).data
            else:
                z = None

            path.append((x, y, z))

        return Response(path)


#
# Regions
#

class RegionViewSet(ModelViewSet):
    queryset = Region.objects.add_related_count(
        Region.objects.all(),
        Site,
        'region',
        'site_count',
        cumulative=True
    )
    serializer_class = serializers.RegionSerializer
    filterset_class = filters.RegionFilterSet


#
# Sites
#

class SiteViewSet(CustomFieldModelViewSet):
    queryset = Site.objects.prefetch_related(
        'region', 'tenant', 'tags'
    ).annotate(
        device_count=get_subquery(Device, 'site'),
        rack_count=get_subquery(Rack, 'site'),
        prefix_count=get_subquery(Prefix, 'site'),
        vlan_count=get_subquery(VLAN, 'site'),
        circuit_count=get_subquery(Circuit, 'terminations__site'),
        virtualmachine_count=get_subquery(VirtualMachine, 'cluster__site'),
    )
    serializer_class = serializers.SiteSerializer
    filterset_class = filters.SiteFilterSet

    @action(detail=True)
    def graphs(self, request, pk):
        """
        A convenience method for rendering graphs for a particular site.
        """
        site = get_object_or_404(self.queryset, pk=pk)
        queryset = Graph.objects.restrict(request.user).filter(type__model='site')
        serializer = RenderedGraphSerializer(queryset, many=True, context={'graphed_object': site})
        return Response(serializer.data)


#
# Rack groups
#

class RackGroupViewSet(ModelViewSet):
    queryset = RackGroup.objects.add_related_count(
        RackGroup.objects.all(),
        Rack,
        'group',
        'rack_count',
        cumulative=True
    ).prefetch_related('site')
    serializer_class = serializers.RackGroupSerializer
    filterset_class = filters.RackGroupFilterSet


#
# Rack roles
#

class RackRoleViewSet(ModelViewSet):
    queryset = RackRole.objects.annotate(
        rack_count=get_subquery(Rack, 'role')
    )
    serializer_class = serializers.RackRoleSerializer
    filterset_class = filters.RackRoleFilterSet


#
# Racks
#

class RackViewSet(CustomFieldModelViewSet):
    queryset = Rack.objects.prefetch_related(
        'site', 'group__site', 'role', 'tenant', 'tags'
    ).annotate(
        device_count=get_subquery(Device, 'rack'),
        powerfeed_count=get_subquery(PowerFeed, 'rack')
    )
    serializer_class = serializers.RackSerializer
    filterset_class = filters.RackFilterSet

    @swagger_auto_schema(
        responses={200: serializers.RackUnitSerializer(many=True)},
        query_serializer=serializers.RackElevationDetailFilterSerializer
    )
    @action(detail=True)
    def elevation(self, request, pk=None):
        """
        Rack elevation representing the list of rack units. Also supports rendering the elevation as an SVG.
        """
        rack = get_object_or_404(self.queryset, pk=pk)
        serializer = serializers.RackElevationDetailFilterSerializer(data=request.GET)
        if not serializer.is_valid():
            return Response(serializer.errors, 400)
        data = serializer.validated_data

        if data['render'] == 'svg':
            # Render and return the elevation as an SVG drawing with the correct content type
            drawing = rack.get_elevation_svg(
                face=data['face'],
                user=request.user,
                unit_width=data['unit_width'],
                unit_height=data['unit_height'],
                legend_width=data['legend_width'],
                include_images=data['include_images'],
                base_url=request.build_absolute_uri('/')
            )
            return HttpResponse(drawing.tostring(), content_type='image/svg+xml')

        else:
            # Return a JSON representation of the rack units in the elevation
            elevation = rack.get_rack_units(
                face=data['face'],
                user=request.user,
                exclude=data['exclude'],
                expand_devices=data['expand_devices']
            )

            # Enable filtering rack units by ID
            q = data['q']
            if q:
                elevation = [u for u in elevation if q in str(u['id']) or q in str(u['name'])]

            page = self.paginate_queryset(elevation)
            if page is not None:
                rack_units = serializers.RackUnitSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(rack_units.data)


#
# Rack reservations
#

class RackReservationViewSet(ModelViewSet):
    queryset = RackReservation.objects.prefetch_related('rack', 'user', 'tenant')
    serializer_class = serializers.RackReservationSerializer
    filterset_class = filters.RackReservationFilterSet

    # Assign user from request
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


#
# Manufacturers
#

class ManufacturerViewSet(ModelViewSet):
    queryset = Manufacturer.objects.annotate(
        devicetype_count=get_subquery(DeviceType, 'manufacturer'),
        inventoryitem_count=get_subquery(InventoryItem, 'manufacturer'),
        platform_count=get_subquery(Platform, 'manufacturer')
    )
    serializer_class = serializers.ManufacturerSerializer
    filterset_class = filters.ManufacturerFilterSet


#
# Device types
#

class DeviceTypeViewSet(CustomFieldModelViewSet):
    queryset = DeviceType.objects.prefetch_related('manufacturer', 'tags').annotate(
        device_count=get_subquery(Device, 'device_type')
    )
    serializer_class = serializers.DeviceTypeSerializer
    filterset_class = filters.DeviceTypeFilterSet


#
# Device type components
#

class ConsolePortTemplateViewSet(ModelViewSet):
    queryset = ConsolePortTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.ConsolePortTemplateSerializer
    filterset_class = filters.ConsolePortTemplateFilterSet


class ConsoleServerPortTemplateViewSet(ModelViewSet):
    queryset = ConsoleServerPortTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.ConsoleServerPortTemplateSerializer
    filterset_class = filters.ConsoleServerPortTemplateFilterSet


class PowerPortTemplateViewSet(ModelViewSet):
    queryset = PowerPortTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.PowerPortTemplateSerializer
    filterset_class = filters.PowerPortTemplateFilterSet


class PowerOutletTemplateViewSet(ModelViewSet):
    queryset = PowerOutletTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.PowerOutletTemplateSerializer
    filterset_class = filters.PowerOutletTemplateFilterSet


class InterfaceTemplateViewSet(ModelViewSet):
    queryset = InterfaceTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.InterfaceTemplateSerializer
    filterset_class = filters.InterfaceTemplateFilterSet


class FrontPortTemplateViewSet(ModelViewSet):
    queryset = FrontPortTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.FrontPortTemplateSerializer
    filterset_class = filters.FrontPortTemplateFilterSet


class RearPortTemplateViewSet(ModelViewSet):
    queryset = RearPortTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.RearPortTemplateSerializer
    filterset_class = filters.RearPortTemplateFilterSet


class DeviceBayTemplateViewSet(ModelViewSet):
    queryset = DeviceBayTemplate.objects.prefetch_related('device_type__manufacturer')
    serializer_class = serializers.DeviceBayTemplateSerializer
    filterset_class = filters.DeviceBayTemplateFilterSet


#
# Device roles
#

class DeviceRoleViewSet(ModelViewSet):
    queryset = DeviceRole.objects.annotate(
        device_count=get_subquery(Device, 'device_role'),
        virtualmachine_count=get_subquery(VirtualMachine, 'role')
    )
    serializer_class = serializers.DeviceRoleSerializer
    filterset_class = filters.DeviceRoleFilterSet


#
# Platforms
#

class PlatformViewSet(ModelViewSet):
    queryset = Platform.objects.annotate(
        device_count=get_subquery(Device, 'platform'),
        virtualmachine_count=get_subquery(VirtualMachine, 'platform')
    )
    serializer_class = serializers.PlatformSerializer
    filterset_class = filters.PlatformFilterSet


#
# Devices
#

class DeviceViewSet(CustomFieldModelViewSet, ConfigContextQuerySetMixin):
    queryset = Device.objects.prefetch_related(
        'device_type__manufacturer', 'device_role', 'tenant', 'platform', 'site', 'rack', 'parent_bay',
        'virtual_chassis__master', 'primary_ip4__nat_outside', 'primary_ip6__nat_outside', 'tags',
    )
    filterset_class = filters.DeviceFilterSet

    def get_serializer_class(self):
        """
        Select the specific serializer based on the request context.

        If the `brief` query param equates to True, return the NestedDeviceSerializer

        If the `exclude` query param includes `config_context` as a value, return the DeviceSerializer

        Else, return the DeviceWithConfigContextSerializer
        """

        request = self.get_serializer_context()['request']
        if request.query_params.get('brief', False):
            return serializers.NestedDeviceSerializer

        elif 'config_context' in request.query_params.get('exclude', []):
            return serializers.DeviceSerializer

        return serializers.DeviceWithConfigContextSerializer

    @action(detail=True)
    def graphs(self, request, pk):
        """
        A convenience method for rendering graphs for a particular Device.
        """
        device = get_object_or_404(self.queryset, pk=pk)
        queryset = Graph.objects.restrict(request.user).filter(type__model='device')
        serializer = RenderedGraphSerializer(queryset, many=True, context={'graphed_object': device})

        return Response(serializer.data)

    @swagger_auto_schema(
        manual_parameters=[
            Parameter(
                name='method',
                in_='query',
                required=True,
                type=openapi.TYPE_STRING
            )
        ],
        responses={'200': serializers.DeviceNAPALMSerializer}
    )
    @action(detail=True, url_path='napalm')
    def napalm(self, request, pk):
        """
        Execute a NAPALM method on a Device
        """
        device = get_object_or_404(self.queryset, pk=pk)
        if not device.primary_ip:
            raise ServiceUnavailable("This device does not have a primary IP address configured.")
        if device.platform is None:
            raise ServiceUnavailable("No platform is configured for this device.")
        if not device.platform.napalm_driver:
            raise ServiceUnavailable(f"No NAPALM driver is configured for this device's platform: {device.platform}.")

        # Check for primary IP address from NetBox object
        if device.primary_ip:
            host = str(device.primary_ip.address.ip)
        else:
            # Raise exception for no IP address and no Name if device.name does not exist
            if not device.name:
                raise ServiceUnavailable(
                    "This device does not have a primary IP address or device name to lookup configured."
                )
            try:
                # Attempt to complete a DNS name resolution if no primary_ip is set
                host = socket.gethostbyname(device.name)
            except socket.gaierror:
                # Name lookup failure
                raise ServiceUnavailable(
                    f"Name lookup failure, unable to resolve IP address for {device.name}. Please set Primary IP or "
                    f"setup name resolution.")

        # Check that NAPALM is installed
        try:
            import napalm
            from napalm.base.exceptions import ModuleImportError
        except ModuleNotFoundError as e:
            if getattr(e, 'name') == 'napalm':
                raise ServiceUnavailable("NAPALM is not installed. Please see the documentation for instructions.")
            raise e

        # Validate the configured driver
        try:
            driver = napalm.get_network_driver(device.platform.napalm_driver)
        except ModuleImportError:
            raise ServiceUnavailable("NAPALM driver for platform {} not found: {}.".format(
                device.platform, device.platform.napalm_driver
            ))

        # Verify user permission
        if not request.user.has_perm('dcim.napalm_read_device'):
            return HttpResponseForbidden()

        napalm_methods = request.GET.getlist('method')
        response = OrderedDict([(m, None) for m in napalm_methods])
        username = settings.NAPALM_USERNAME
        password = settings.NAPALM_PASSWORD
        optional_args = settings.NAPALM_ARGS.copy()
        if device.platform.napalm_args is not None:
            optional_args.update(device.platform.napalm_args)

        # Update NAPALM parameters according to the request headers
        for header in request.headers:
            if header[:9].lower() != 'x-napalm-':
                continue

            key = header[9:]
            if key.lower() == 'username':
                username = request.headers[header]
            elif key.lower() == 'password':
                password = request.headers[header]
            elif key:
                optional_args[key.lower()] = request.headers[header]

        # Connect to the device
        d = driver(
            hostname=host,
            username=username,
            password=password,
            timeout=settings.NAPALM_TIMEOUT,
            optional_args=optional_args
        )
        try:
            d.open()
        except Exception as e:
            raise ServiceUnavailable("Error connecting to the device at {}: {}".format(host, e))

        # Validate and execute each specified NAPALM method
        for method in napalm_methods:
            if not hasattr(driver, method):
                response[method] = {'error': 'Unknown NAPALM method'}
                continue
            if not method.startswith('get_'):
                response[method] = {'error': 'Only get_* NAPALM methods are supported'}
                continue
            try:
                response[method] = getattr(d, method)()
            except NotImplementedError:
                response[method] = {'error': 'Method {} not implemented for NAPALM driver {}'.format(method, driver)}
            except Exception as e:
                response[method] = {'error': 'Method {} failed: {}'.format(method, e)}
        d.close()

        return Response(response)


#
# Device components
#

class ConsolePortViewSet(CableTraceMixin, ModelViewSet):
    queryset = ConsolePort.objects.prefetch_related('device', 'connected_endpoint__device', 'cable', 'tags')
    serializer_class = serializers.ConsolePortSerializer
    filterset_class = filters.ConsolePortFilterSet


class ConsoleServerPortViewSet(CableTraceMixin, ModelViewSet):
    queryset = ConsoleServerPort.objects.prefetch_related('device', 'connected_endpoint__device', 'cable', 'tags')
    serializer_class = serializers.ConsoleServerPortSerializer
    filterset_class = filters.ConsoleServerPortFilterSet


class PowerPortViewSet(CableTraceMixin, ModelViewSet):
    queryset = PowerPort.objects.prefetch_related(
        'device', '_connected_poweroutlet__device', '_connected_powerfeed', 'cable', 'tags'
    )
    serializer_class = serializers.PowerPortSerializer
    filterset_class = filters.PowerPortFilterSet


class PowerOutletViewSet(CableTraceMixin, ModelViewSet):
    queryset = PowerOutlet.objects.prefetch_related('device', 'connected_endpoint__device', 'cable', 'tags')
    serializer_class = serializers.PowerOutletSerializer
    filterset_class = filters.PowerOutletFilterSet


class InterfaceViewSet(CableTraceMixin, ModelViewSet):
    queryset = Interface.objects.prefetch_related(
        'device', '_connected_interface', '_connected_circuittermination', 'cable', 'ip_addresses', 'tags'
    ).filter(
        device__isnull=False
    )
    serializer_class = serializers.InterfaceSerializer
    filterset_class = filters.InterfaceFilterSet

    @action(detail=True)
    def graphs(self, request, pk):
        """
        A convenience method for rendering graphs for a particular interface.
        """
        interface = get_object_or_404(self.queryset, pk=pk)
        queryset = Graph.objects.restrict(request.user).filter(type__model='interface')
        serializer = RenderedGraphSerializer(queryset, many=True, context={'graphed_object': interface})
        return Response(serializer.data)


class FrontPortViewSet(CableTraceMixin, ModelViewSet):
    queryset = FrontPort.objects.prefetch_related('device__device_type__manufacturer', 'rear_port', 'cable', 'tags')
    serializer_class = serializers.FrontPortSerializer
    filterset_class = filters.FrontPortFilterSet


class RearPortViewSet(CableTraceMixin, ModelViewSet):
    queryset = RearPort.objects.prefetch_related('device__device_type__manufacturer', 'cable', 'tags')
    serializer_class = serializers.RearPortSerializer
    filterset_class = filters.RearPortFilterSet


class DeviceBayViewSet(ModelViewSet):
    queryset = DeviceBay.objects.prefetch_related('installed_device').prefetch_related('tags')
    serializer_class = serializers.DeviceBaySerializer
    filterset_class = filters.DeviceBayFilterSet


class InventoryItemViewSet(ModelViewSet):
    queryset = InventoryItem.objects.prefetch_related('device', 'manufacturer').prefetch_related('tags')
    serializer_class = serializers.InventoryItemSerializer
    filterset_class = filters.InventoryItemFilterSet


#
# Connections
#

class ConsoleConnectionViewSet(ListModelMixin, GenericViewSet):
    queryset = ConsolePort.objects.prefetch_related(
        'device', 'connected_endpoint__device'
    ).filter(
        connected_endpoint__isnull=False
    )
    serializer_class = serializers.ConsolePortSerializer
    filterset_class = filters.ConsoleConnectionFilterSet


class PowerConnectionViewSet(ListModelMixin, GenericViewSet):
    queryset = PowerPort.objects.prefetch_related(
        'device', 'connected_endpoint__device'
    ).filter(
        _connected_poweroutlet__isnull=False
    )
    serializer_class = serializers.PowerPortSerializer
    filterset_class = filters.PowerConnectionFilterSet


class InterfaceConnectionViewSet(ListModelMixin, GenericViewSet):
    queryset = Interface.objects.prefetch_related(
        'device', '_connected_interface__device'
    ).filter(
        # Avoid duplicate connections by only selecting the lower PK in a connected pair
        _connected_interface__isnull=False,
        pk__lt=F('_connected_interface')
    )
    serializer_class = serializers.InterfaceConnectionSerializer
    filterset_class = filters.InterfaceConnectionFilterSet


#
# Cables
#

class CableViewSet(ModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = Cable.objects.prefetch_related(
        'termination_a', 'termination_b'
    )
    serializer_class = serializers.CableSerializer
    filterset_class = filters.CableFilterSet


#
# Virtual chassis
#

class VirtualChassisViewSet(ModelViewSet):
    queryset = VirtualChassis.objects.prefetch_related('tags').annotate(
        member_count=get_subquery(Device, 'virtual_chassis')
    )
    serializer_class = serializers.VirtualChassisSerializer
    filterset_class = filters.VirtualChassisFilterSet


#
# Power panels
#

class PowerPanelViewSet(ModelViewSet):
    queryset = PowerPanel.objects.prefetch_related(
        'site', 'rack_group'
    ).annotate(
        powerfeed_count=get_subquery(PowerFeed, 'power_panel')
    )
    serializer_class = serializers.PowerPanelSerializer
    filterset_class = filters.PowerPanelFilterSet


#
# Power feeds
#

class PowerFeedViewSet(CustomFieldModelViewSet):
    queryset = PowerFeed.objects.prefetch_related('power_panel', 'rack', 'tags')
    serializer_class = serializers.PowerFeedSerializer
    filterset_class = filters.PowerFeedFilterSet


#
# Miscellaneous
#

class ConnectedDeviceViewSet(ViewSet):
    """
    This endpoint allows a user to determine what device (if any) is connected to a given peer device and peer
    interface. This is useful in a situation where a device boots with no configuration, but can detect its neighbors
    via a protocol such as LLDP. Two query parameters must be included in the request:

    * `peer_device`: The name of the peer device
    * `peer_interface`: The name of the peer interface
    """
    permission_classes = [IsAuthenticatedOrLoginNotRequired]
    _device_param = Parameter(
        name='peer_device',
        in_='query',
        description='The name of the peer device',
        required=True,
        type=openapi.TYPE_STRING
    )
    _interface_param = Parameter(
        name='peer_interface',
        in_='query',
        description='The name of the peer interface',
        required=True,
        type=openapi.TYPE_STRING
    )

    def get_view_name(self):
        return "Connected Device Locator"

    @swagger_auto_schema(
        manual_parameters=[_device_param, _interface_param],
        responses={'200': serializers.DeviceSerializer}
    )
    def list(self, request):

        peer_device_name = request.query_params.get(self._device_param.name)
        peer_interface_name = request.query_params.get(self._interface_param.name)

        if not peer_device_name or not peer_interface_name:
            raise MissingFilterException(detail='Request must include "peer_device" and "peer_interface" filters.')

        # Determine local interface from peer interface's connection
        peer_interface = get_object_or_404(
            Interface.objects.all(),
            device__name=peer_device_name,
            name=peer_interface_name
        )
        local_interface = peer_interface._connected_interface

        if local_interface is None:
            return Response()

        return Response(serializers.DeviceSerializer(local_interface.device, context={'request': request}).data)

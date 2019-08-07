from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.core import validators

from dcim.models import Interface, Device
from ipam.models import IPAddress
from extras.models import CustomFieldModel
from ipam.models import VRF, IPAddress, Prefix


class RouteMap(models.Model):
    name = models.CharField(max_length=128)
    configuration = models.TextField()

    csv_headers = ['name', 'configuration']

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Routemap'


class BGPCommunity(models.Model):
    community = models.CharField(max_length=128)
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(max_length=255, blank=True, null=True)

    csv_headers = ['community', 'name', 'description']

    def __str__(self):
        return '{} ({})'.format(self.name, self.community)

    class Meta:
        verbose_name = 'BGP Community'
        verbose_name_plural = 'BGP Communities'


class BGPCommunityList(models.Model):
    name = models.CharField(max_length=128, unique=True)
    communities = models.ManyToManyField(to=BGPCommunity, through='BGPCommunityListMember')

    csv_headers = ['communities', 'name']

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'BGP Community List'


class BGPCommunityListMember(models.Model):
    list = models.ForeignKey(to=BGPCommunityList, on_delete=models.CASCADE)
    community = models.ForeignKey(to=BGPCommunity, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=(('permit', 'Permit'), ('deny', 'Deny')))


class BGPASN(models.Model):
    asn = models.BigIntegerField(
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(2**32)
        ]
    )
    networks = models.ManyToManyField(
        Prefix,
        related_name='sessions',
        blank=True,
    )
    redistribute_connected = models.BooleanField(default=False)
    devices = models.ManyToManyField(to=Device, through='BGPDeviceASN', related_name='asns')

    csv_headers = ['asn', 'networks']

    def __str__(self):
        return str(self.asn)

    class Meta:
        verbose_name = 'BGP ASN'


class BGPDeviceASN(models.Model):
    device = models.ForeignKey(to=Device, on_delete=models.CASCADE)
    asn = models.ForeignKey(to=BGPASN, on_delete=models.CASCADE)
    excluded_prefixes = models.ManyToManyField(to=Prefix, related_name='disabled_prefixes', blank=True)
    additional_prefixes = models.ManyToManyField(to=Prefix, related_name='additional_prefixes', blank=True)
    redistribute_connected = models.BooleanField(default=False)

    def get_exposed_prefixes(self):
        prefix_union = self.asn.networks.all().union(self.additional_prefixes.all())
        prefix_excluded_difference = prefix_union.difference(self.excluded_prefixes.all())
        return prefix_excluded_difference.values_list('prefix', flat=True)

    def __str__(self):
        return "{} <-> {}".format(str(self.device), str(self.asn))

    class Meta:
        verbose_name = 'Device ASN link'


class BGPNeighbor(models.Model):
    description = models.TextField(verbose_name='Description', max_length=255, blank=True, null=True)
    deviceasn = models.ForeignKey(to=BGPDeviceASN, on_delete=models.CASCADE, related_name='neighbors')
    neighbor_type = models.CharField(max_length=50, choices=[('internal', 'Internal'), ('external', 'External')])
    internal_neighbor_device = models.ForeignKey(to=Device, on_delete=models.CASCADE,
                                                 related_name='neighbors', null=True, blank=True)
    internal_neighbor_ip = models.ForeignKey(to=IPAddress, on_delete=models.CASCADE, null=True, blank=True)
    external_neighbor = models.GenericIPAddressField(null=True, blank=True)

    status = models.CharField(max_length=50, choices=[('active', 'Active'), ('disabled', 'Disabled')])

    routemap_in = models.ForeignKey(
        RouteMap, null=True, blank=True, related_name='sessions_in', on_delete=models.PROTECT
    )
    routemap_out = models.ForeignKey(
        RouteMap, null=True, blank=True, related_name='sessions_out', on_delete=models.PROTECT
    )

    remote_asn = models.BigIntegerField(
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(2 ** 32)
        ]
    )

    source_interface = models.ForeignKey(to=Interface, on_delete=models.PROTECT, null=True, blank=True)
    next_hop_self = models.BooleanField(default=False)
    remove_private_as = models.BooleanField(default=False)
    send_community = models.CharField(max_length=50, default='both', null=True, blank=True, choices=[
        ('normal', 'Normal'),
        ('extended', 'Extended'),
        ('both', 'Both'),
    ])
    soft_reconfiguration = models.CharField(max_length=50, null=True, blank=True, choices=[
        ('normal', 'Normal'),
        ('inbound', 'Inbound'),
    ])

    csv_headers = ['description', 'device', 'internal_neighbor']

    def __str__(self):
        if self.neighbor_type == 'internal':
            return "{} ({})".format(str(self.internal_neighbor_device), str(self.internal_neighbor_ip))
        else:
            return "External ({})".format(self.external_neighbor)

    def is_internal_neighbor_complete(self):
        """
        Checks if internal BGP-Session is configured on both devices
        :return: True if session is configured on both devices or neighbor_type is external, otherwise False
        """
        if self.neighbor_type == 'internal':
            return self.internal_neighbor_device.bgpdeviceasn_set.filter(
                    asn__asn=self.remote_asn,
                    neighbors__internal_neighbor_device=self.deviceasn.device,
                    neighbors__remote_asn=self.deviceasn.asn.asn).exists()
        return True

    class Meta:
        verbose_name = 'BGP Neighbor'

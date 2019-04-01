from django.db import models
from django.core import validators

from dcim.models import Device
from ipam.fields import IPAddressField


class BGPCommunity(models.Model):
    community = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    description = models.TextField(max_length=255, blank=True, null=True)

    csv_headers = [
        'community', 'name', 'description'
    ]

    def __str__(self):
        return '{} ({})'.format(self.name, self.community)

    class Meta:
        verbose_name = 'BGP Community'
        verbose_name_plural = 'BGP Communities'


BGP_INTERNAL = 0
BGP_EXTERNAL = 1


class BGPSession(models.Model):
    tag = models.PositiveSmallIntegerField(
        choices=(
            (BGP_INTERNAL, 'Internal Session'),
            (BGP_EXTERNAL, 'External Session'),
        ),
        default=BGP_INTERNAL,
    )
    neighbor = IPAddressField(
        help_text='IPv4 or IPv6 address (with mask)',
        blank=True,
        null=True,
    )
    remote_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)],
        blank=True,
        null=True,
    )
    device_a = models.ForeignKey(
        Device,
        related_name='bgp_sessions_a',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    device_a_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)],
        blank=True,
        null=True,
    )
    device_b = models.ForeignKey(
        Device,
        related_name='bgp_sessions_b',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    device_b_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)],
        blank=True,
        null=True,
    )
    description = models.TextField(max_length=255, blank=True, null=True)
    devices = models.ManyToManyField(Device, related_name='bgp_sessions')
    communities = models.ManyToManyField(BGPCommunity, related_name='sessions')

    csv_headers = [
        'tag', 'neighbor', 'remote_as', 'description', 'communities'
    ]

    def __str__(self):
        return 'neighbor {}, remote AS {}'.format(self.neighbor, self.remote_as)

    class Meta:
        verbose_name = 'BGP Session'

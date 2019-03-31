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


class BGPSession(models.Model):
    neighbor = IPAddressField(
        help_text='IPv4 or IPv6 address (with mask)'
    )
    remote_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)]
    )
    description = models.TextField(max_length=255, blank=True, null=True)
    devices = models.ManyToManyField(Device, related_name='bgp_sessions')
    community = models.ForeignKey(BGPCommunity, blank=True, null=True, on_delete=models.SET_NULL)

    csv_headers = [
        'neighbor', 'remote_as', 'description', 'community'
    ]

    def __str__(self):
        return 'neighbor {}, remote AS {}'.format(self.neighbor, self.remote_as)

    class Meta:
        verbose_name = 'BGP Session'

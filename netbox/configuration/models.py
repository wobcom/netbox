from django.db import models
from django.core import validators

from dcim.models import Device
from ipam.fields import IPAddressField


class BGPCommunity(models.Model):
    community = models.PositiveIntegerField()
    name = models.CharField(max_length=128)
    description = models.TextField(max_length=255, blank=True, null=True)

    csv_headers = [
        'community', 'name', 'description'
    ]


class BGPSession(models.Model):
    neighbor = IPAddressField(
        help_text='IPv4 or IPv6 address (with mask)'
    )
    remote_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)]
    )
    description = models.TextField(max_length=255, blank=True, null=True)
    devices = models.ManyToManyField(Device)
    community = models.ForeignKey(BGPCommunity, blank=True, null=True, on_delete=models.SET_NULL)

    csv_headers = [
        'neighbor', 'remote_as', 'description', 'community'
    ]

    def __str__(self):
        return 'neighbor {}, remote AS {}'.format(self.neighbor, self.remote_as)

    class Meta:
        verbose_name = 'BGP Session'

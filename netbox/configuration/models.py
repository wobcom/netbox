from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.core import validators

from dcim.models import Device
from extras.models import CustomFieldModel
from ipam.fields import IPAddressField
from ipam.models import IPAddress, VRF


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


class BGPSession(CustomFieldModel):
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
    neighbor_a = models.ForeignKey(
        IPAddress,
        related_name='bgp_sessions_a',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    neighbor_a_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)],
        blank=True,
        null=True,
    )
    neighbor_b = models.ForeignKey(
        IPAddress,
        related_name='bgp_sessions_b',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    neighbor_b_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)],
        blank=True,
        null=True,
    )
    description = models.TextField(max_length=255, blank=True, null=True)
    devices = models.ManyToManyField(Device, related_name='bgp_sessions')
    communities = models.ManyToManyField(BGPCommunity, related_name='sessions')
    vrf = models.ForeignKey(
        VRF,
        related_name='bgp_sessions',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='VRF'
    )
    custom_field_values = GenericRelation(
        to='extras.CustomFieldValue',
        content_type_field='obj_type',
        object_id_field='obj_id'
    )

    csv_headers = [
        'tag', 'neighbor', 'remote_as', 'description', 'communities', 'vrf'
    ]

    def __str__(self):
        if self.tag == BGP_EXTERNAL:
            return 'neighbor {}, remote AS {}'.format(
                self.neighbor,
                self.remote_as
            )
        elif self.tag == BGP_INTERNAL:
            return '{} ({})<->{} ({})'.format(
                self.neighbor_a,
                self.neighbor_a_as,
                self.neighbor_b,
                self.neighbor_b_as,
            )

    class Meta:
        verbose_name = 'BGP Session'

from django.db import models
from django.core import validators

from ipam.fields import IPAddressField

class BGPConfiguration(models.Model):
    neighbor = IPAddressField(
        help_text='IPv4 or IPv6 address (with mask)'
    )
    remote_as = models.PositiveIntegerField(
        validators=[validators.MaxValueValidator(65536)]
    )

    csv_headers = [
        'neighbor', 'remote_as',
    ]

    def __str__(self):
        return 'neighbor {}, remote AS {}'.format(self.neighbor, self.remote_as)

    class Meta:
        verbose_name = 'BGP Configuration'

from django import template
from dcim.models import Device
from configuration.models import BGPASN, BGPDeviceASN

register = template.Library()


@register.filter
def unconfigured_asns(device):
    """
    Returns list of ASNs configured as remote_asn in neighbor configurations
    with this device on other devices.
    :param device:
    :return: list of tuples (int or BGPASN, boolean) the boolean is true if BGPASN exists.
    """
    if isinstance(device, Device):
        for asn in set(device.neighbors.values_list('remote_asn', flat=True)) - \
                   set(device.asns.values_list('asn', flat=True)):
            try:
                yield BGPASN.objects.get(asn=asn), True
            except BGPASN.DoesNotExist:
                yield asn, False


@register.filter
def unconfigured_neighbors_exists(bgpdeviceasn):
    """
    Returns whether unconfigured neighbors exists
    :param bgpdeviceasn:
    :return: boolean
    """
    if isinstance(bgpdeviceasn, BGPDeviceASN):
        return bgpdeviceasn.device.neighbors.filter(remote_asn=bgpdeviceasn.asn.asn).count() > 0

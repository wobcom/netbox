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
    if not isinstance(device, Device):
        return
    configured_asns = device.asns.values_list('asn', flat=True)
    unconfigured_neighbors = device.neighbors.exclude(remote_asn__in=configured_asns)
    for asn in unconfigured_neighbors.values_list('remote_asn', flat=True):
        try:
            yield BGPASN.objects.get(asn=asn), True
        except BGPASN.DoesNotExist:
            yield asn.remote_asn, False


@register.filter
def unconfigured_neighbors_exists(bgpdeviceasn):
    """
    Returns whether unconfigured neighbors exists
    :param bgpdeviceasn:
    :return: boolean
    """
    if not isinstance(bgpdeviceasn, BGPDeviceASN):
        return
    return bgpdeviceasn.device.neighbors.filter(remote_asn=bgpdeviceasn.asn.asn).exists()

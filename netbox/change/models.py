import io
import pickle
import yaml
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.shortcuts import redirect
from django.utils import timezone

from netbox import configuration
from dcim.models import Device, Interface
from ipam.models import IPADDRESS_ROLE_LOOPBACK

from change.utilities import Markdownify


class ChangeInformation(models.Model):
    """Meta information about a change."""
    is_emergency = models.BooleanField(verbose_name="Is an emergency change")
    is_extensive = models.BooleanField(verbose_name="Is an extensive change")
    affects_customer = models.BooleanField(verbose_name="Customers are affected")
    change_implications = models.TextField()
    ignore_implications = models.TextField()

    def executive_summary(self, no_markdown=True):
        md = Markdownify(no_markdown=no_markdown)
        res = io.StringIO()
        if self.is_emergency:
            res.write(md.bold('This change is an emergency change.'))
            res.write('\n\n')

        res.write(md.h3('Implications if this change is accepted:'))
        res.write('\n{}\n\n'.format(self.change_implications))
        res.write(md.h3('Implications if this change is rejected:'))
        res.write('\n{}\n\n'.format(self.ignore_implications))

        if self.affects_customer:
            res.write(md.h3('This change affects customers'))
            res.write('\nThe following customers are affected:\n')
            for change in self.affectedcustomer_set.all():
                res.write('- {}'.format(change.name))
                if change.is_business:
                    res.write(md.bold(' (Business Customer)'))
                res.write(": {}\n".format(change.products_affected))
        return res.getvalue()


class AffectedCustomer(models.Model):
    """Customers affected by a change"""
    information = models.ForeignKey(
        to=ChangeInformation,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=128, verbose_name="Customer Name")
    is_business = models.BooleanField(verbose_name="Is a business customer")
    products_affected = models.CharField(max_length=128,
                                         verbose_name="Affected Products")


# These are the states that a change set can be in
DRAFT = 1
IN_REVIEW = 2
ACCEPTED = 3
IMPLEMENTED = 4
REJECTED = 5


class ChangeSet(models.Model):
    """
    A change set always refers to a ticket, has a set of changes, and can be
    serialized to YAML.
    """
    ticket_id = models.UUIDField(null=True)
    active = models.BooleanField(default=False)
    change_information = models.ForeignKey(
        to=ChangeInformation,
        on_delete=models.CASCADE,
        related_name='information',
        null=True
    )
    started = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    updated = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )

    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    status = models.SmallIntegerField(
        default=DRAFT,
        choices=(
            (DRAFT, 'Draft'),
            (IN_REVIEW, 'Under Review'),
            (ACCEPTED, 'Accepted'),
            (IMPLEMENTED, 'Implemented'),
            (REJECTED, 'Rejected'),
        )
    )

    def yamlify_extra_fields(self, instance):
        res = {}
        for field in instance.custom_field_values.all():
            res[field.field.name] = field.value
        return res

    def yamlify_device_type(self, device_type):
        if device_type:
            return {
                'manufacturer': device_type.manufacturer.name
                                if device_type.manufacturer else None,
                'model': device_type.model,
                'part_number': device_type.part_number,
                **self.yamlify_extra_fields(device_type)
            }

    def yamlify_vlan(self, vlan):
        if vlan:
            return {
                'vid': vlan.vid,
                'vxlan_prefix': vlan.tenant.vxlan_prefix
            }

    def get_clag_mac(self, primary, secondary):
        # N.B. We assume that we are only wiring up exactly two interfaces at
        # the moment. There is a small chance of collision, since the mac
        # address is based on the IDs % 255, so if the modulus value is the same
        # for BOTH clagged mac addresses, we will collide. Tough world we live
        # in.
        # This is the address range specified by Cumulus in:
        # https://support.cumulusnetworks.com/hc/en-us/articles/203837076
        return '44:38:39:ff:{:02X}:{:02X}'.format(primary.id, secondary.id)

    def get_peerlink(self, interface):
        children = Interface.objects.filter(lag=interface)
        peer_lag = None
        for child in children:
            if not child.cable:
                raise ValueError(
                    'Peerlink child {} has no connection'.format(child.id)
                )
            peer_interface = child.trace()[0][2]
            this_peer_lag = peer_interface.lag
            if not this_peer_lag:
                raise ValueError(
                    'Peerlink child {} does not belong to a LAG'.format(peer_interface.id)
                )
            if this_peer_lag.name != 'peerlink':
                raise ValueError(
                    'LAG {} was expected to be a peer link'.format(this_peer_lag.id)
                )
            if peer_lag and not peer_lag.id == this_peer_lag.id:
                raise ValueError(
                    'Not all bond slaves of interface {} belong to the same peer link'.format(interface.id)
                )
            peer_lag = this_peer_lag
        return peer_lag


    def yamlify_peerlink(self, interface):
        peer_interface = self.get_peerlink(interface)
        if interface.id < peer_interface.id:
            peer_ip = '169.254.1.1'
            addr = '169.254.1.2/30'
            primary = interface
            secondary = peer_interface
        else:
            peer_ip = '169.254.1.2'
            addr = '169.254.1.1/30'
            primary = peer_interface
            secondary = interface
        return {
            'clagd_sys_mac': self.get_clag_mac(primary, secondary),
            'vid': 4094,
            'clagd_peer_ip': peer_ip,
            'address': addr,
            'priority': 1000,
            'child_interfaces': self.child_interfaces(interface),
            'clagd_backup_ip': self.get_loopback_for_device(
                                    peer_interface.device
                               ),
        }

    def child_interfaces(self, interface):
        return list(
            Interface.objects.filter(lag=interface).values_list('name',
                                                                flat=True)
        )

    def yamlify_interface(self, interface):
        if interface:
            res = {
                'name': interface.name,
                'child_interfaces': self.child_interfaces(interface),
                'enabled': interface.enabled,
                'mac_address': interface.mac_address,
                'mtu': interface.mtu,
                'mgmnt_only': interface.mgmt_only,
                'mode': interface.get_mode_display(),
                'untagged_vlan': self.yamlify_vlan(interface.untagged_vlan),
                'tags': list(interface.tags.names()),
                'description': interface.description,
                'tagged_vlans': [self.yamlify_vlan(v)
                                            for v
                                            in interface.tagged_vlans.all()]
            }
            addresses = []
            for ip_addr in interface.ip_addresses.all():
                addresses.append({
                    'address': str(ip_addr.address.ip),
                    'prefix_length': str(ip_addr.address.prefixlen),
                })
            res["ip_addresses"] = addresses
            return res

    def vxlan_from_vlan(self, loopback, prefix, vlan):
        return {
            'name': 'vxlan{}_{}'.format(prefix, vlan.vid),
            'vid': vlan.vid,
            'prefix': prefix,
            'vxlan_local_tunnelip': loopback,
            'bridge_learning': False,
        }

    def get_loopback_for_device(self, device):
        ins = device.interfaces
        i = ins.filter(ip_addresses__role=IPADDRESS_ROLE_LOOPBACK).first()
        if i:
            return str(
                i.ip_addresses.filter(role=IPADDRESS_ROLE_LOOPBACK)
                              .first()
                              .address
                              .ip
            )

    def get_device_vxlans(self, device):
        vxlans = []
        loopback = self.get_loopback_for_device(device)
        if not device.tenant:
            return vxlans
        prefix = device.tenant.vxlan_prefix
        for interface in device.interfaces.all():
            if interface.untagged_vlan:
                vxlans.append(self.vxlan_from_vlan(loopback,
                                                   prefix,
                                                   interface.untagged_vlan))
            vxlans.extend([self.vxlan_from_vlan(loopback, prefix, v)
                                    for v
                                    in interface.tagged_vlans.all()])
        return vxlans

    def is_leaf(self, device):
        return device.device_role.name == "leaf"

    def yamlify_device(self, device):
        res = {
            'type': self.yamlify_device_type(device.device_type),
            'role': device.device_role.name if device.device_role else None,
            'platform': device.platform.name if device.platform else None,
            'name': device.name,
            'serial': device.serial,
            'asset_tag': device.asset_tag,
            'status': device.get_status_display(),
            'loopback': self.get_loopback_for_device(device),
            'management_ip4': {
                'address': str(device.primary_ip4.address.ip),
                'prefix_length': str(device.primary_ip4.address.prefixlen),
            } if device.primary_ip4 else None,
            'management_ip6': {
                'address': str(device.primary_ip6.address.ip),
                'prefix_length': str(device.primary_ip6.address.prefixlen),
            } if device.primary_ip6 else None,
            'tags': list(device.tags.names()),
            **self.yamlify_extra_fields(device)
        }
        interfaces = []
        for interface in device.interfaces.all():
            if interface.name == 'peerlink':
                res['peerlink'] = self.yamlify_peerlink(interface)
            else:
                interfaces.append(self.yamlify_interface(interface))
        res['interfaces'] = interfaces
        res['vteps'] = self.get_device_vxlans(device)
        # TODO multiple bridges
        res['bridges'] = []
        if self.is_leaf(device):
            res['bridges'].append({
                'vids': [v['vid'] for v in res['vteps']] if res['vteps'] else [],
                'bridge_stp': True,
                # just one per device allowed!
                'bridge_vlan_aware': True,
                # for multiple bridges: counter
                'name': 'bridge0',
                'child_interfaces': [v['name'] for v in res['vteps']] +
                    list(
                        device.interfaces.exclude(mgmt_only=True)
                                     .exclude(lag__isnull=False)
                                     .exclude(tags__name__in=['evpn'])
                                     .exclude(name="lo")
                                     .values_list("name", flat=True)
                    )
            })
        return yaml.dump(res, explicit_start=True, default_flow_style=False)

    def to_actions(self):
        """Creates Gitlab actions for all devices"""
        actions = []
        self.apply()

        for device in Device.objects.all():
            actions.append({
                'file_path': 'host_vars/{}/main.yaml'.format(device.name),
                'content': self.yamlify_device(device)
            })
        self.revert()
        return actions

    def executive_summary(self, no_markdown=False):
        return self.change_information.executive_summary(no_markdown=no_markdown)

    def apply(self):
        for change in self.changedfield_set.all():
            change.apply()
        for change in self.changedobject_set.all():
            change.apply()

    def revert(self):
        for change in self.changedfield_set.all():
            change.revert()
        for change in self.changedobject_set.all():
            change.revert()

    def in_use(self):
        threshold = timedelta(minutes=configuration.CHANGE_SESSION_TIMEOUT)
        before = timezone.now() - threshold

        return self.updated > before


class ChangedField(models.Model):
    """
    A changed field refers to a field of any model that has changed. It records
    the old and new values, refers to a changeset, has a time, and a generic
    foreign key relation to the model it refers to. These are kind of clunky,
    but sadly necessary.

    It can be reverted by calling revert(), which will check whether the values
    are as we expect them (otherwise something terrible happened), and reverts
    it to the old value.
    """
    changeset = models.ForeignKey(
        ChangeSet,
        null=True,
        on_delete=models.SET_NULL
    )
    time = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    changed_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name='+'
    )
    changed_object_id = models.PositiveIntegerField()
    changed_object = GenericForeignKey(
        ct_field='changed_object_type',
        fk_field='changed_object_id'
    )
    field = models.CharField(
        max_length=40
    )
    old_value = models.BinaryField(null=True)
    new_value = models.BinaryField(null=True)
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    def __str__(self):
        old = pickle.loads(self.old_value)
        new = pickle.loads(self.new_value)
        tpl = "Field {} of {} was changed from '{}' to '{}'."
        return tpl.format(self.field, self.changed_object_type, old, new)

    def apply(self):
        # TODO: what happens otherwise?
        old = pickle.loads(self.old_value)
        new = pickle.loads(self.new_value)
        if getattr(self.changed_object, self.field) == old:
            setattr(self.changed_object, self.field, new)
            self.changed_object.save()

    def revert(self):
        # TODO: what happens otherwise?
        old = pickle.loads(self.old_value)
        new = pickle.loads(self.new_value)
        if getattr(self.changed_object, self.field) == new:
            setattr(self.changed_object, self.field, old)
            self.changed_object.save()


class ChangedObject(models.Model):
    """
    A changed object is similar to a changed field, but it refers to the whole
    object. This is necessary if there was no object before (i.e. it was newly
    created).

    It can be reverted by calling revert(), which will simply delete the object.
    """
    changeset = models.ForeignKey(
        ChangeSet,
        null=True,
        on_delete=models.SET_NULL
    )
    time = models.DateTimeField(
        auto_now_add=True,
        editable=False
    )
    changed_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name='+'
    )
    changed_object_id = models.PositiveIntegerField()
    changed_object = GenericForeignKey(
        ct_field='changed_object_type',
        fk_field='changed_object_id'
    )
    changed_object_data = models.BinaryField()
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    def __str__(self):
        return "{} #{} was added.".format(self.changed_object_type,
                                          self.changed_object_id)

    def apply(self):
        # we have to save twice because we don't want to update but need a
        # specific ID
        obj = pickle.loads(self.changed_object_data)
        id_ = obj.id
        obj.id = None
        obj.save()
        obj.id = id_
        obj.save()

    def revert(self):
        if self.changed_object:
            self.changed_object.delete()

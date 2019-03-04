import io
import pickle
import yaml
import graphviz
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.shortcuts import redirect
from django.utils import timezone

from netbox import configuration
from dcim.models import Device, Interface
from dcim.constants import *
from ipam.models import IPADDRESS_ROLE_LOOPBACK

from change.utilities import Markdownify
from dcim.constants import *

DEVICE_ROLE_TOPOLOGY_WHITELIST = ['leaf', 'spine', 'superspine']

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
FAILED = 6


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

    provision_log = JSONField(
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
            (FAILED, 'Failed'),
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
                'name': vlan.name,
                'vid': vlan.vid,
                'role': vlan.role.name if vlan.role else None
            }

    def convert_form_factor(self, form_factor):
        m = {
            IFACE_FF_VIRTUAL: 'virtual',
            IFACE_FF_BRIDGE: 'bridge',
            IFACE_FF_LAG: 'lag'
        }
        return m.get(form_factor, 'default')

    def concat_vxlan_vlan(self, vxlan_prefix, vlan_id):
        return str(int(vxlan_prefix) * 4096 + int(vlan_id))

    def child_interfaces(self, interface):
        res = []
        for child_interface in Interface.objects.filter(lag=interface):
            if child_interface.form_factor == IFACE_FF_ONTEP:
                if not child_interface.overlay_network:
                    continue
                # expand ONTEP to VTEPs
                for vlan in child_interface.overlay_network.vlans.all():
                    res.append(child_interface.name + '_' + self.concat_vxlan_vlan(child_interface.overlay_network.vxlan_prefix, vlan.vid))
            else:
                res.append(child_interface.name)
        return res

    def yamlify_ontep_interface(self, interface):
        res = []
        if not interface.overlay_network:
            return res
        for vlan in interface.overlay_network.vlans.all():
            res.append({
                'name': interface.name + '_' + self.concat_vxlan_vlan(interface.overlay_network.vxlan_prefix, vlan.vid),
                'enabled': True,
                'untagged_vlan': self.yamlify_vlan(vlan),
                'description': 'VTEP (VxLAN prefix="{}" VLAN="{}")'.format(interface.overlay_network.vxlan_prefix, vlan.vid),
                'form_factor': 'VTEP',
                'vxlan_id': self.concat_vxlan_vlan(interface.overlay_network.vxlan_prefix, vlan.vid),
                'ip_addresses': [self.yamlify_ip_address(address)
                                    for address
                                    in interface.ip_addresses.all()]
            })
        return res
 
    def yamlify_ip_address(self, ip_address):
        return {
            'address': str(ip_address.address.ip),
            'prefix_length': str(ip_address.address.prefixlen),
            'tags': list(ip_address.tags.names()),
            'primary': ip_address.is_primary
        }

    def yamlify_bridge_interface(self, interface):
        res = {
            'name': interface.name,
            'child_interfaces': self.child_interfaces(interface),
            'form_factor': 'bridge',
            'enabled': interface.enabled,
            'mtu': interface.mtu,
            'untagged_vlan': self.yamlify_vlan(interface.untagged_vlan),
            }
        tagged_vlans = set()
        for child_interface in Interface.objects.filter(lag=interface):
            if child_interface.form_factor == IFACE_FF_ONTEP:
                tagged_vlans |= set(child_interface.overlay_network.vlans.all())
            else:
                tagged_vlans |= set(child_interface.tagged_vlans.all())
        res['tagged_vlans'] = [self.yamlify_vlan(v) for v in tagged_vlans]
        return [res]

    def yamlify_interface(self, interface):
        if interface.form_factor == IFACE_FF_ONTEP:
            return self.yamlify_ontep_interface(interface)
        elif interface.form_factor == IFACE_FF_BRIDGE:
            return self.yamlify_bridge_interface(interface)
        elif interface:
            return [{
                'name': interface.name,
                'child_interfaces': self.child_interfaces(interface),
                'clag_id': interface.clag_id,
                'enabled': interface.enabled,
                'mac_address': str(interface.mac_address),
                'mtu': interface.mtu,
                'mgmnt_only': interface.mgmt_only,
                'mode': interface.get_mode_display(),
                'untagged_vlan': self.yamlify_vlan(interface.untagged_vlan),
                #'overlay': self.yamlify_overlay(interface.overlay_network),
                'tags': list(interface.tags.names()),
                'description': interface.description,
                'tagged_vlans': [self.yamlify_vlan(v)
                                            for v
                                            in interface.tagged_vlans.all()],
                'form_factor': self.convert_form_factor(interface.form_factor),
                'ip_addresses': [self.yamlify_ip_address(address)
                                            for address
                                            in interface.ip_addresses.all()]
            }]

    def yamlify_device(self, device):
        res = {
            'type': self.yamlify_device_type(device.device_type),
            'role': device.device_role.name if device.device_role else None,
            'platform': device.platform.name if device.platform else None,
            'name': device.name,
            'serial': device.serial,
            'asset_tag': device.asset_tag,
            'status': device.get_status_display(),
            'tags': list(device.tags.names()),
            'interfaces': [],
            'primary_ip4': self.yamlify_ip_address(device.primary_ip4) if device.primary_ip4 else None,
            **self.yamlify_extra_fields(device)
        }
        for interface in device.interfaces.all():
            res['interfaces'] += self.yamlify_interface(interface)
        res = {'device': res}
        return yaml.dump(res, explicit_start=True, default_flow_style=False)

    def map_platform_to_vagrant_box(self, platform):
        default = "centos/7"
        m = {
            "cumulus" : "CumulusCommunity/cumulus-vx",
            "debian9" : "debian/stretch64"
        }
        if platform and platform.name:
            return m.get(platform.name, default)
        return default

    def to_action(self, fname, action, content):
        return {
            'file_path': fname,
            'content': content,
            'action': action
        }

    def create_topology_graph(self):
        """Creates a topology graph in dot syntax"""
        graph = graphviz.Graph(
            name="topology",
            comment="Autogenerated using Netbox"
        )
        seen_devices = []
        # TODO apply filtering
        for device in Device.objects.filter(status=DEVICE_STATUS_ACTIVE):
            if device.device_role.name not in DEVICE_ROLE_TOPOLOGY_WHITELIST:
                continue
            attributes = {
                "function": device.device_role.name,
                "os" : self.map_platform_to_vagrant_box(device.platform)
            }
            graph.node(device.name, **attributes)
            seen_devices.append(device)
            for interface in device.interfaces.all():
                if interface.form_factor in NONCONNECTABLE_IFACE_TYPES + AGGREGATABLE_IFACE_TYPES:
                    continue
                peer_interface = interface.trace()[0][2]
                if not peer_interface:
                    continue
                elif peer_interface.device in seen_devices:
                    continue
                elif peer_interface.device.status != DEVICE_STATUS_ACTIVE:
                    continue
                elif peer_interface.device.device_role.name not in DEVICE_ROLE_TOPOLOGY_WHITELIST:
                    continue
                graph.edge(
                    "{}:{}".format(device.name, interface.name),
                    "{}:{}".format(
                        peer_interface.device.name,
                        peer_interface.name
                    )
                )
        return self.to_action('topology.dot', 'update', graph.source)

    def create_inventory(self):
        res = io.StringIO()
        res.write("# Generated by netbox")
        groups = {}
        for device in Device.objects.filter(status=DEVICE_STATUS_ACTIVE,
                                            primary_ip4__isnull=False):
            res.write("\n{} ansible_host={}".format(device.name, str(device.primary_ip4.address.ip)))
            if device.device_role:
                if not device.device_role.name in groups:
                    groups[device.device_role.name] = []
                groups[device.device_role.name].append(device.name)
            res.write("\n")
        for group, entries in groups.items():
            res.write("\n\n[{}]".format(group))
            for entry in entries:
                res.write("\n{}".format(entry))
        return self.to_action('inventory.ini', 'update', res.getvalue())

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
        for change in self.changedobject_set.order_by("time").all():
            change.apply()
        for change in self.changedfield_set.order_by("time").all():
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
        obj = pickle.loads(self.changed_object_data)
        obj.save(force_insert=True)

    def revert(self):
        if self.changed_object:
            self.changed_object.delete()


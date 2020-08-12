import django_tables2 as tables
from django_tables2.utils import Accessor

from dcim.models import Interface
from tenancy.tables import COL_TENANT
from utilities.tables import BaseTable, ColoredLabelColumn, TagColumn, ToggleColumn
from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine

CLUSTERTYPE_ACTIONS = """
<a href="{% url 'virtualization:clustertype_changelog' slug=record.slug %}" class="btn btn-default btn-xs" title="Change log">
    <i class="fa fa-history"></i>
</a>
{% if perms.virtualization.change_clustertype %}
    <a href="{% url 'virtualization:clustertype_edit' slug=record.slug %}?return_url={{ request.path }}" class="btn btn-xs btn-warning"><i class="glyphicon glyphicon-pencil" aria-hidden="true"></i></a>
{% endif %}
"""

CLUSTERGROUP_ACTIONS = """
<a href="{% url 'virtualization:clustergroup_changelog' slug=record.slug %}" class="btn btn-default btn-xs" title="Change log">
    <i class="fa fa-history"></i>
</a>
{% if perms.virtualization.change_clustergroup %}
    <a href="{% url 'virtualization:clustergroup_edit' slug=record.slug %}?return_url={{ request.path }}" class="btn btn-xs btn-warning"><i class="glyphicon glyphicon-pencil" aria-hidden="true"></i></a>
{% endif %}
"""

VIRTUALMACHINE_STATUS = """
<span class="label label-{{ record.get_status_class }}">{{ record.get_status_display }}</span>
"""

VIRTUALMACHINE_PRIMARY_IP = """
{{ record.primary_ip6.address.ip|default:"" }}
{% if record.primary_ip6 and record.primary_ip4 %}<br />{% endif %}
{{ record.primary_ip4.address.ip|default:"" }}
"""

CLUSTER_DEVICE_COUNT = """
<a href="{% url 'dcim:device_list' %}?cluster_id={{ record.pk }}">{{ value|default:0 }}</a>
"""

CLUSTER_VM_COUNT = """
<a href="{% url 'virtualization:virtualmachine_list' %}?cluster_id={{ record.pk }}">{{ value|default:0 }}</a>
"""


#
# Cluster types
#

class ClusterTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    cluster_count = tables.Column(
        verbose_name='Clusters'
    )
    actions = tables.TemplateColumn(
        template_code=CLUSTERTYPE_ACTIONS,
        attrs={'td': {'class': 'text-right noprint'}},
        verbose_name=''
    )

    class Meta(BaseTable.Meta):
        model = ClusterType
        fields = ('pk', 'name', 'slug', 'cluster_count', 'description', 'actions')
        default_columns = ('pk', 'name', 'cluster_count', 'description', 'actions')


#
# Cluster groups
#

class ClusterGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    cluster_count = tables.Column(
        verbose_name='Clusters'
    )
    actions = tables.TemplateColumn(
        template_code=CLUSTERGROUP_ACTIONS,
        attrs={'td': {'class': 'text-right noprint'}},
        verbose_name=''
    )

    class Meta(BaseTable.Meta):
        model = ClusterGroup
        fields = ('pk', 'name', 'slug', 'cluster_count', 'description', 'actions')
        default_columns = ('pk', 'name', 'cluster_count', 'description', 'actions')


#
# Clusters
#

class ClusterTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    tenant = tables.LinkColumn(
        viewname='tenancy:tenant',
        args=[Accessor('tenant.slug')]
    )
    site = tables.LinkColumn(
        viewname='dcim:site',
        args=[Accessor('site.slug')]
    )
    device_count = tables.TemplateColumn(
        template_code=CLUSTER_DEVICE_COUNT,
        verbose_name='Devices'
    )
    vm_count = tables.TemplateColumn(
        template_code=CLUSTER_VM_COUNT,
        verbose_name='VMs'
    )
    tags = TagColumn(
        url_name='virtualization:cluster_list'
    )

    class Meta(BaseTable.Meta):
        model = Cluster
        fields = ('pk', 'name', 'type', 'group', 'tenant', 'site', 'device_count', 'vm_count', 'tags')
        default_columns = ('pk', 'name', 'type', 'group', 'tenant', 'site', 'device_count', 'vm_count')


#
# Virtual machines
#

class VirtualMachineTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    status = tables.TemplateColumn(
        template_code=VIRTUALMACHINE_STATUS
    )
    cluster = tables.LinkColumn(
        viewname='virtualization:cluster',
        args=[Accessor('cluster.pk')]
    )
    role = ColoredLabelColumn()
    tenant = tables.TemplateColumn(
        template_code=COL_TENANT
    )

    class Meta(BaseTable.Meta):
        model = VirtualMachine
        fields = ('pk', 'name', 'status', 'cluster', 'role', 'tenant', 'vcpus', 'memory', 'disk')


class VirtualMachineDetailTable(VirtualMachineTable):
    primary_ip4 = tables.LinkColumn(
        viewname='ipam:ipaddress',
        args=[Accessor('primary_ip4.pk')],
        verbose_name='IPv4 Address'
    )
    primary_ip6 = tables.LinkColumn(
        viewname='ipam:ipaddress',
        args=[Accessor('primary_ip6.pk')],
        verbose_name='IPv6 Address'
    )
    primary_ip = tables.TemplateColumn(
        orderable=False,
        verbose_name='IP Address',
        template_code=VIRTUALMACHINE_PRIMARY_IP
    )
    tags = TagColumn(
        url_name='virtualization:virtualmachine_list'
    )

    class Meta(BaseTable.Meta):
        model = VirtualMachine
        fields = (
            'pk', 'name', 'status', 'cluster', 'role', 'tenant', 'platform', 'vcpus', 'memory', 'disk', 'primary_ip4',
            'primary_ip6', 'primary_ip', 'tags',
        )
        default_columns = (
            'pk', 'name', 'status', 'cluster', 'role', 'tenant', 'vcpus', 'memory', 'disk', 'primary_ip',
        )


#
# VM components
#

class InterfaceTable(BaseTable):

    class Meta(BaseTable.Meta):
        model = Interface
        fields = ('name', 'enabled', 'description')

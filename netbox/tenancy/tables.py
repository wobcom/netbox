import django_tables2 as tables

from utilities.tables import BaseTable, ToggleColumn
from .models import Tenant, TenantGroup

MPTT_LINK = """
{% if record.get_children %}
    <span style="padding-left: {{ record.get_ancestors|length }}0px "><i class="fa fa-caret-right"></i>
{% else %}
    <span style="padding-left: {{ record.get_ancestors|length }}9px">
{% endif %}
    <a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
</span>
"""

TENANTGROUP_ACTIONS = """
<a href="{% url 'tenancy:tenantgroup_changelog' slug=record.slug %}" class="btn btn-default btn-xs" title="Change log">
    <i class="fa fa-history"></i>
</a>
{% if perms.tenancy.change_tenantgroup %}
    <a href="{% url 'tenancy:tenantgroup_edit' slug=record.slug %}?return_url={{ request.path }}" class="btn btn-xs btn-warning"><i class="glyphicon glyphicon-pencil" aria-hidden="true"></i></a>
{% endif %}
"""

COL_TENANT = """
{% if record.tenant %}
    <a href="{% url 'tenancy:tenant' slug=record.tenant.slug %}" title="{{ record.tenant.description }}">{{ record.tenant }}</a>
{% else %}
    &mdash;
{% endif %}
"""


#
# Tenant groups
#

class TenantGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(
        template_code=MPTT_LINK,
        orderable=False
    )
    tenant_count = tables.Column(
        verbose_name='Tenants'
    )
    slug = tables.Column()
    actions = tables.TemplateColumn(
        template_code=TENANTGROUP_ACTIONS,
        attrs={'td': {'class': 'text-right noprint'}},
        verbose_name=''
    )

    class Meta(BaseTable.Meta):
        model = TenantGroup
        fields = ('pk', 'name', 'tenant_count', 'description', 'slug', 'actions')


#
# Tenants
#

class TenantTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = Tenant
        fields = ('pk', 'name', 'group', 'description')

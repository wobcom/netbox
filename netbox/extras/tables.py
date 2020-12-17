import django_tables2 as tables
from django.conf import settings

from utilities.tables import BaseTable, BooleanColumn, ButtonsColumn, ChoiceFieldColumn, ColorColumn, ToggleColumn
from .models import ConfigContext, ObjectChange, Tag, TaggedItem

TAGGED_ITEM = """
{% if value.get_absolute_url %}
    <a href="{{ value.get_absolute_url }}">{{ value }}</a>
{% else %}
    {{ value }}
{% endif %}
"""

CONFIGCONTEXT_ACTIONS = """
{% if perms.extras.change_configcontext %}
    <a href="{% url 'extras:configcontext_edit' pk=record.pk %}" class="btn btn-xs btn-warning"><i class="mdi mdi-pencil" aria-hidden="true"></i></a>
{% endif %}
{% if perms.extras.delete_configcontext %}
    <a href="{% url 'extras:configcontext_delete' pk=record.pk %}" class="btn btn-xs btn-danger"><i class="mdi mdi-trash-can-outline" aria-hidden="true"></i></a>
{% endif %}
"""

OBJECTCHANGE_OBJECT = """
{% if record.changed_object.get_absolute_url %}
    <a href="{{ record.changed_object.get_absolute_url }}">{{ record.object_repr }}</a>
{% else %}
    {{ record.object_repr }}
{% endif %}
"""

OBJECTCHANGE_REQUEST_ID = """
<a href="{% url 'extras:objectchange_list' %}?request_id={{ value }}">{{ value }}</a>
"""


class BaseTagTable(BaseTable):
    pk = ToggleColumn()
    color = ColorColumn()

    class Meta(BaseTable.Meta):
        model = Tag
        fields = ('pk', 'name', 'items', 'slug', 'color', 'description')


class TagTable(BaseTagTable):
    actions = ButtonsColumn(Tag, pk_field='slug')

    class Meta(BaseTagTable.Meta):
        fields = (*BaseTagTable.Meta.fields, 'actions')


class TaggedItemTable(BaseTable):
    content_object = tables.TemplateColumn(
        template_code=TAGGED_ITEM,
        orderable=False,
        verbose_name='Object'
    )
    content_type = tables.Column(
        verbose_name='Type'
    )

    class Meta(BaseTable.Meta):
        model = TaggedItem
        fields = ('content_object', 'content_type')


class ConfigContextTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    is_active = BooleanColumn(
        verbose_name='Active'
    )

    class Meta(BaseTable.Meta):
        model = ConfigContext
        fields = (
            'pk', 'name', 'weight', 'is_active', 'description', 'regions', 'sites', 'roles', 'platforms',
            'cluster_groups', 'clusters', 'tenant_groups', 'tenants',
        )
        default_columns = ('pk', 'name', 'weight', 'is_active', 'description')


class ObjectChangeTable(BaseTable):
    time = tables.DateTimeColumn(
        linkify=True,
        format=settings.SHORT_DATETIME_FORMAT
    )
    action = ChoiceFieldColumn()
    changed_object_type = tables.Column(
        verbose_name='Type'
    )
    object_repr = tables.TemplateColumn(
        template_code=OBJECTCHANGE_OBJECT,
        verbose_name='Object'
    )
    request_id = tables.TemplateColumn(
        template_code=OBJECTCHANGE_REQUEST_ID,
        verbose_name='Request ID'
    )

    class Meta(BaseTable.Meta):
        model = ObjectChange
        fields = ('time', 'user_name', 'action', 'changed_object_type', 'object_repr', 'request_id')

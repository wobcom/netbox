import django_tables2 as tables

from utilities.tables import BaseTable
from .models import ChangeSet, ProvisionSet


UPDATED = "{{record.updated | timesince }}"

PROVISION_STATUS = "{% include 'change/inc/provision_set_label.html' with provision_set=record %}"

PROVISION_UPDATED = '<span title="{{ record.updated }}">{{ record.updated | timesince }} ago</span>'

PROVISION_CREATED = '<span title="{{ record.created }}">{{ record.created | timesince }} ago</span>'

PROVISION_CHANGE_COUNT = '<span>{{ record.changesets.count }}</span>'

PROVISION_ACTIONS = '''
{% load change %}
{% if record|can_rollback:request.user %}
    <a href="{% url 'change:rollback' record.pk %}" class="btn btn-warning btn-xs" title="Rollback to state of this provisioning.">
        <i class="fa fa-undo"></i>
    </a>
{% endif %}
'''

CHANGE_STATUS = '{{ record.get_status_display }}'

CHANGE_NAME = '{{ record.change_information.name }}'

CHANGE_AUTHOR = '{{ record.user.username }}'


class ChangeTable(BaseTable):
    pk = tables.LinkColumn('change:detail', args=[tables.A('pk')])
    changedfield_count = tables.Column(verbose_name='Changed Fields')
    changedobject_count = tables.Column(verbose_name='Changed Objects')
    updated = tables.TemplateColumn(template_code=UPDATED, verbose_name='Updated')

    class Meta(BaseTable.Meta):
        model = ChangeSet
        fields = (
            'pk',
            'status',
            'changedfield_count',
            'changedobject_count',
            'updated',
        )


class ProvisionTable(BaseTable):
    pk = tables.LinkColumn('change:provision_set',
                           verbose_name="ID",
                           args=[tables.A('pk')])
    status = tables.TemplateColumn(template_code=PROVISION_STATUS)
    user = tables.Column(verbose_name='Creator')
    changes = tables.TemplateColumn(template_code=PROVISION_CHANGE_COUNT, orderable=False)
    updated = tables.TemplateColumn(template_code=PROVISION_UPDATED)
    created = tables.TemplateColumn(template_code=PROVISION_CREATED)
    actions = tables.TemplateColumn(
        template_code=PROVISION_ACTIONS,
        attrs={
            'cell': {
                'style': 'text-align: right;',
            },
        },
        orderable=False,
    )

    class Meta(BaseTable.Meta):
        model = ProvisionSet
        fields = (
            'pk',
            'status',
            'user',
            'changes',
            'updated',
            'created',
        )


class ProvisioningChangesTable(BaseTable):
    pk = tables.LinkColumn('change:detail',
                           verbose_name='ID',
                           args=[tables.A('pk')])
    status = tables.TemplateColumn(template_code=CHANGE_STATUS,
                                   order_by='status')
    title = tables.TemplateColumn(template_code=CHANGE_NAME,
                                  order_by='change_information__name',
                                  verbose_name="Title")
    author = tables.TemplateColumn(template_code=CHANGE_AUTHOR,
                                   order_by='user')
    updated = tables.TemplateColumn(template_code=UPDATED)

    class Meta(BaseTable.Meta):
        model = ChangeSet
        fields = (
            'pk',
            'status',
            'title',
            'author',
            'updated',
        )

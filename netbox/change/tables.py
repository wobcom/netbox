import django_tables2 as tables

from utilities.tables import BaseTable
from .models import ChangeSet, ProvisionSet


UPDATED = "{{record.updated | timesince }}"

PROVISION_UPDATED = '<span title="{{ record.updated }}">{{ record.updated | timesince }}</span>'

PROVISION_CREATED = '<span title="{{ record.created }}">{{ record.created | timesince }}</span>'


class ChangeTable(BaseTable):
    pk = tables.LinkColumn('change:detail', args=[tables.A('pk')])
    status = tables.Column()
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
    pk = tables.LinkColumn('change:provisions', verbose_name="ID")
    user = tables.Column(verbose_name='Creator')
    updated = tables.TemplateColumn(template_code=PROVISION_UPDATED)
    created = tables.TemplateColumn(template_code=PROVISION_CREATED)

    class Meta(BaseTable.Meta):
        model = ProvisionSet
        fields = (
            'pk',
            'user',
            'updated',
            'created',
        )

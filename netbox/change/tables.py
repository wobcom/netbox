import django_tables2 as tables

from utilities.tables import BaseTable
from .models import ChangeSet


UPDATED = "{{record.updated | timesince }}"


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

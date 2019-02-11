import django_tables2 as tables

from utilities.tables import BaseTable
from .models import ChangeSet

class ChangeTable(BaseTable):
    pk = tables.LinkColumn('change:change_detail', args=[tables.A('pk')])
    status = tables.Column()
    changedfield_count = tables.Column(verbose_name='Changed Fields')
    changedobject_count = tables.Column(verbose_name='Changed Objects')

    class Meta(BaseTable.Meta):
        model = ChangeSet
        fields = ('pk', 'status', 'changedfield_count', 'changedobject_count')

import django_tables2 as tables
from utilities.tables import BaseTable, ToggleColumn

from .models import BGPConfiguration

class BGPTable(BaseTable):
    pk = ToggleColumn()
    neighbor = tables.Column(verbose_name='Neighbor')
    remote_as = tables.Column(verbose_name='Remote AS')

    class Meta(BaseTable.Meta):
        model = BGPConfiguration
        fields = ('pk', 'neighbor', 'remote_as')

import django_tables2 as tables
from utilities.tables import BaseTable, ToggleColumn

from .models import BGPSession

class BGPTable(BaseTable):
    pk = ToggleColumn()
    neighbor = tables.Column(verbose_name='Neighbor')
    remote_as = tables.Column(verbose_name='Remote AS')
    community = tables.Column(verbose_name='Community')

    class Meta(BaseTable.Meta):
        model = BGPSession
        fields = ('pk', 'neighbor', 'remote_as', 'community')

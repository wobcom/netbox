import django_tables2 as tables
from utilities.tables import BaseTable, ToggleColumn

from .models import BGPSession, BGPCommunity

class BGPInternalTable(BaseTable):
    pk = ToggleColumn()
    device_a = tables.Column(verbose_name='Device A')
    device_a_as = tables.Column(verbose_name='Device A AS')
    device_b = tables.Column(verbose_name='Device B')
    device_b_as = tables.Column(verbose_name='Device B AS')
    communities = tables.Column(verbose_name='Communities')

    def render_communities(self, record):
        return ', '.join(record.communities.values_list('community', flat=True))

    class Meta(BaseTable.Meta):
        model = BGPSession
        fields = (
            'pk', 'device_a', 'device_a_as', 'device_b_as', 'device_b_as',
            'communities'
        )


class BGPExternalTable(BaseTable):
    pk = ToggleColumn()
    neighbor = tables.Column(verbose_name='Neighbor')
    remote_as = tables.Column(verbose_name='Remote AS')
    communities = tables.Column(verbose_name='Communities')

    def render_communities(self, record):
        return ', '.join(record.communities.values_list('community', flat=True))

    class Meta(BaseTable.Meta):
        model = BGPSession
        fields = ('pk', 'neighbor', 'remote_as', 'communities')


class CommunityTable(BaseTable):
    pk = ToggleColumn()
    community = tables.Column(verbose_name='Community')
    name = tables.Column(verbose_name='Name')

    class Meta(BaseTable.Meta):
        model = BGPCommunity
        fields = ('pk', 'community', 'name')

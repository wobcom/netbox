import django_tables2 as tables
from django_tables2.utils import Accessor
from utilities.tables import BaseTable, ToggleColumn

from .models import BGPCommunity, BGPCommunityList, RouteMap, BGPASN, BGPDeviceASN


class CommunityTable(BaseTable):
    pk = ToggleColumn()
    community = tables.Column(verbose_name='Community')
    name = tables.Column(verbose_name='Name')

    class Meta(BaseTable.Meta):
        model = BGPCommunity
        fields = ('pk', 'community', 'name')


class CommunityListTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn('configuration:communitylist_detail', args=[Accessor('pk')])

    class Meta(BaseTable.Meta):
        model = BGPCommunityList
        fields = ('pk', 'name')


class RouteMapTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn('configuration:routemap_edit', args=[Accessor('pk')])

    class Meta(BaseTable.Meta):
        model = RouteMap
        fields = ('pk', 'name')


class BGPASNTable(BaseTable):
    pk = ToggleColumn()
    asn = tables.LinkColumn('configuration:asn_edit', args=[Accessor('pk')])

    class Meta(BaseTable.Meta):
        model = BGPASN
        fields = ('pk', 'asn')


class BGPDeviceASNTable(BaseTable):

    class Meta(BaseTable.Meta):
        model = BGPDeviceASN
        fields = ('pk', 'device', 'asn')

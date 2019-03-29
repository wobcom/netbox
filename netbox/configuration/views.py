from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render

from utilities.views import (
    BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView,
)
from . import filters, forms, tables
from .models import BGPSession, BGPCommunity

class BGPListView(ObjectListView):
    queryset = BGPSession.objects.all()
    filter = filters.BGPFilter
    filter_form = forms.BGPFilterForm
    table = tables.BGPTable
    template_name = 'configuration/bgp_list.html'


class BGPCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = BGPSession
    model_form = forms.BGPForm
    default_return_url = 'configuration:bgp_list'


class BGPAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.change_bgp'
    model = BGPSession
    default_return_url = 'configuration:bgp_list'
    def get(self, request, pk=None):
        table = tables.BGPTable(BGPSession.objects.all())
        table.columns.show('pk')
        return render(request, 'configuration/bgp_select.html', {
            'device': pk,
            'table': table,
        })


class BGPEditView(BGPCreateView):
    permission_required = 'configuration.change_bgp'


class BGPBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_bgp'
    model_form = forms.BGPCSVForm
    table = tables.BGPTable
    default_return_url = 'configuration:bgp_list'


class BGPBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgp'
    queryset = BGPSession.objects
    filter = filters.BGPFilter
    table = tables.BGPTable
    default_return_url = 'configuration:bgp_list'


class CommunityListView(ObjectListView):
    queryset = BGPCommunity.objects.all()
    filter = filters.CommunityFilter
    filter_form = forms.CommunityFilterForm
    table = tables.CommunityTable
    template_name = 'configuration/community_list.html'


class CommunityCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = BGPCommunity
    model_form = forms.CommunityForm
    default_return_url = 'configuration:community_list'


class CommunityEditView(CommunityCreateView):
    permission_required = 'configuration.change_bgp'


class CommunityBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_bgp'
    model_form = forms.CommunityCSVForm
    table = tables.CommunityTable
    default_return_url = 'configuration:community_list'


class CommunityBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgp'
    queryset = BGPCommunity.objects
    filter = filters.CommunityFilter
    table = tables.CommunityTable
    default_return_url = 'configuration:community_list'

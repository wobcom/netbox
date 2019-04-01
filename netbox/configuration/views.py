from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import render, redirect

from dcim.models import Device
from utilities.views import (
    BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView,
)
from . import filters, forms, tables
from .models import BGPSession, BGPCommunity, BGP_INTERNAL, BGP_EXTERNAL

class BGPListView(ObjectListView):
    queryset = BGPSession.objects.all()
    table_querysets = {
        'internal_table': BGPSession.objects.filter(tag=BGP_INTERNAL),
        'external_table': BGPSession.objects.filter(tag=BGP_EXTERNAL),
    }
    filter = filters.BGPFilter
    filter_form = forms.BGPFilterForm
    table = {
        'internal_table': tables.BGPInternalTable,
        'external_table': tables.BGPExternalTable,
    }
    template_name = 'configuration/bgp_list.html'


class BGPCreateInternalView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = BGPSession
    model_form = forms.BGPInternalForm
    default_return_url = 'configuration:bgp_list'


class BGPCreateExternalView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = BGPSession
    model_form = forms.BGPExternalForm
    default_return_url = 'configuration:bgp_list'


class BGPAddView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.change_bgp'
    model = BGPSession
    default_return_url = 'configuration:bgp_list'
    def get(self, request, pk=None):
        table = tables.BGPExternalTable(
            BGPSession.objects.filter(tag=BGP_EXTERNAL)
        )
        table.columns.show('pk')
        perm_base_name = '{}.{{}}_{}'.format(self.model._meta.app_label,
                                             self.model._meta.model_name)
        permissions = {
            p: request.user.has_perm(perm_base_name.format(p))
                for p in ['add', 'change', 'delete']
        }
        return render(request, 'configuration/bgp_select.html', {
            'device_id': pk,
            'permissions': permissions,
            'external_table': external_table,
        })

    def post(self, request, pk=None):
        sessions = request.POST.getlist('pk')
        d = Device.objects.get(pk=pk)
        d.bgp_sessions.add(*[int(pk) for pk in sessions])
        d.save()
        return redirect('dcim:device', pk=pk)


class BGPDeleteView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.change_bgp'
    model = BGPSession
    default_return_url = 'configuration:bgp_list'
    def post(self, request, pk=None):
        sessions = request.POST.getlist('pk')
        d = Device.objects.get(pk=pk)
        d.bgp_sessions.remove(*[int(pk) for pk in sessions])
        d.save()
        return redirect('dcim:device', pk=pk)


class BGPEditInternalView(BGPCreateInternalView):
    permission_required = 'configuration.change_bgp'


class BGPEditExternalView(BGPCreateExternalView):
    permission_required = 'configuration.change_bgp'


class BGPBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_bgp'
    model_form = forms.BGPCSVForm
    table = tables.BGPInternalTable
    default_return_url = 'configuration:bgp_list'


class BGPBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgp'
    queryset = BGPSession.objects
    filter = filters.BGPFilter
    table = tables.BGPInternalTable
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

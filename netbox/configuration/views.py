from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View

from dcim.models import Device, Interface
from utilities.views import (
    BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView, ObjectDeleteView
)
from . import filters, forms, tables
from .models import (
    BGPCommunity, BGPCommunityList, BGPCommunityListMember, RouteMap, BGPASN,
    BGPNeighbor, BGPDeviceASN
)


class BGPNeighborCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgpneighbor'
    model = BGPNeighbor
    model_form = forms.BGPNeighborForm


class BGPNeighborEditView(BGPNeighborCreateView):
    permission_required = 'configuration.change_bgpneighbor'


class BGPNeighborDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'configuration.delete_bgpneighbor'
    model = BGPNeighbor


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


class CommunityListDetailView(View):
    def get(self, request, pk):
        lst = get_object_or_404(BGPCommunityList, pk=pk)

        return render(request, 'configuration/communitylist.html', {
            'list': lst,
        })


class CommunityListAddToView(View):
    def get(self, request, pk):
        lst = get_object_or_404(BGPCommunityList, pk=pk)
        return render(request, 'configuration/communitylist_addto.html', {
            'list': lst,
            'communities': BGPCommunity.objects.all(),
        })

    def post(self, request, pk):
        lst = get_object_or_404(BGPCommunityList, pk=pk)

        for cpk in request.POST:
            # this is a little yucky.
            if cpk == 'csrfmiddlewaretoken':
                continue
            member = BGPCommunityListMember(list=lst, community_id=cpk, type=request.POST[cpk])
            member.save()

        return redirect('configuration:communitylist_detail', pk=pk)


class CommunityListRemoveFromView(View):
    def get(self, request, pk, other):
        member = get_object_or_404(BGPCommunityListMember, pk=other)
        member.delete()
        return redirect('configuration:communitylist_detail', pk=pk)


# sorry about the name; its CommunityList-ListView
class CommunityListListView(ObjectListView):
    queryset = BGPCommunityList.objects.all()
    filter = filters.CommunityListFilter
    filter_form = forms.CommunityListFilterForm
    table = tables.CommunityListTable
    template_name = 'configuration/communitylist_list.html'


class CommunityListCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = BGPCommunityList
    model_form = forms.CommunityListForm
    default_return_url = 'configuration:communitylist_list'


class CommunityListEditView(CommunityCreateView):
    permission_required = 'configuration.change_bgp'


class CommunityListDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'configuration.delete_bgp'
    model = BGPCommunityList


class CommunityListBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_bgp'
    model_form = forms.CommunityListCSVForm
    table = tables.CommunityListTable
    default_return_url = 'configuration:communitylist_list'


class CommunityListBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgp'
    queryset = BGPCommunityList.objects
    filter = filters.CommunityListFilter
    table = tables.CommunityListTable
    default_return_url = 'configuration:communitylist_list'


class RouteMapListView(ObjectListView):
    queryset = RouteMap.objects.all()
    filter = filters.RouteMapFilter
    filter_form = forms.RouteMapFilterForm
    table = tables.RouteMapTable
    template_name = 'configuration/routemap_list.html'


class RouteMapCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = RouteMap
    model_form = forms.RouteMapForm
    default_return_url = 'configuration:routemap_list'


class RouteMapEditView(RouteMapCreateView):
    permission_required = 'configuration.change_bgp'


class RouteMapBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_bgp'
    model_form = forms.RouteMapCSVForm
    table = tables.RouteMapTable
    default_return_url = 'configuration:routemap_list'


class RouteMapBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgp'
    queryset = RouteMap.objects
    filter = filters.RouteMapFilter
    table = tables.RouteMapTable
    default_return_url = 'configuration:routemap_list'


class BGPASNListView(ObjectListView):
    queryset = BGPASN.objects.all()
    table = tables.BGPASNTable
    template_name = 'configuration/asn_list.html'


class BGPASNCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_asn'
    model = BGPASN
    model_form = forms.BGPASNForm
    default_return_url = 'configuration:asn_list'


class BGPASNEditView(BGPASNCreateView):
    permission_required = 'configuration.change_asn'


class BGPASNBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_asn'
    model_form = forms.BGPASNCSVForm
    table = tables.BGPASNTable
    default_return_url = 'configuration:asn_list'


class BGPASNBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_asn'
    queryset = BGPASN.objects
    table = tables.BGPASNTable
    default_return_url = 'configuration:asn_list'


class BGPDeviceASNCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgpdeviceasn'
    model = BGPDeviceASN
    model_form = forms.BGPDeviceASNForm


class BGPDeviceASNEditView(BGPDeviceASNCreateView):
    permission_required = 'configuration.change_bgpdeviceasn'


class BGPDeviceASNDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'configuration.delete_bgpdeviceasn'
    model = BGPDeviceASN


class BGPDeviceASNBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgpdeviceasn'
    queryset = BGPDeviceASN.objects
    table = tables.BGPDeviceASNTable

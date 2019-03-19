from django.contrib.auth.mixins import PermissionRequiredMixin

from utilities.views import (
    BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView,
)
from . import filters, forms, tables
from .models import BGPConfiguration

class BGPListView(ObjectListView):
    queryset = BGPConfiguration.objects.all()
    filter = filters.BGPFilter
    filter_form = forms.BGPFilterForm
    table = tables.BGPTable
    template_name = 'configuration/bgp_list.html'


class BGPCreateView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'configuration.add_bgp'
    model = BGPConfiguration
    model_form = forms.BGPForm
    default_return_url = 'configuration:bgp_list'


class BGPEditView(BGPCreateView):
    permission_required = 'configuration.change_bgp'


class BGPBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'configuration.add_bgp'
    model_form = forms.BGPCSVForm
    table = tables.BGPTable
    default_return_url = 'configuration:bgp_list'


class BGPBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'configuration.delete_bgp'
    queryset = BGPConfiguration.objects
    filter = filters.BGPFilter
    table = tables.BGPTable
    default_return_url = 'configuration:bgp_list'

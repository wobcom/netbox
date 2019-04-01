from __future__ import unicode_literals

from django.conf.urls import url

from . import views

app_name = 'configuration'
urlpatterns = [
    url(r'^bgp/$', views.BGPListView.as_view(), name='bgp_list'),
    url(r'^bgp/add-internal/$', views.BGPCreateInternalView.as_view(), name='bgp_add_internal'),
    url(r'^bgp/add-external/$', views.BGPCreateExternalView.as_view(), name='bgp_add_external'),
    url(r'^bgp/import/$', views.BGPBulkImportView.as_view(), name='bgp_import'),
    url(r'^bgp/delete/$', views.BGPBulkDeleteView.as_view(), name='bgp_bulk_delete'),
    url(r'^bgp/(?P<pk>\d+)/edit-internal/$', views.BGPEditInternalView.as_view(), name='bgp_edit_external'),
    url(r'^bgp/(?P<pk>\d+)/edit-external/$', views.BGPEditExternalView.as_view(), name='bgp_edit_external'),
    url(r'^bgp/addto/(?P<pk>\d+)/$', views.BGPAddView.as_view(), name='bgp_addto'),
    url(r'^bgp/deletefrom/(?P<pk>\d+)/$', views.BGPDeleteView.as_view(), name='bgp_deletefrom'),
    url(r'^communities/$', views.CommunityListView.as_view(), name='community_list'),
    url(r'^communities/add/$', views.CommunityCreateView.as_view(), name='community_add'),
    url(r'^communities/import/$', views.CommunityBulkImportView.as_view(), name='community_import'),
    url(r'^communities/delete/$', views.CommunityBulkDeleteView.as_view(), name='community_bulk_delete'),
    url(r'^communities/(?P<pk>\d+)/edit/$', views.CommunityEditView.as_view(), name='community_edit'),
]

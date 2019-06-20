from __future__ import unicode_literals

from django.conf.urls import url

from . import views

app_name = 'configuration'
urlpatterns = [
    url(r'^bgp/add', views.BGPNeighborCreateView.as_view(), name='bgp_add'),
    url(r'^bgp/(?P<pk>\d+)/edit$', views.BGPNeighborEditView.as_view(), name='bgp_edit'),
    url(r'^bgp/(?P<pk>\d+)/delete$', views.BGPNeighborDeleteView.as_view(), name='bgp_delete'),
    url(r'^communities/$', views.CommunityListView.as_view(), name='community_list'),
    url(r'^communities/add/$', views.CommunityCreateView.as_view(), name='community_add'),
    url(r'^communities/import/$', views.CommunityBulkImportView.as_view(), name='community_import'),
    url(r'^communities/delete/$', views.CommunityBulkDeleteView.as_view(), name='community_bulk_delete'),
    url(r'^communities/(?P<pk>\d+)/edit/$', views.CommunityEditView.as_view(), name='community_edit'),
    url(r'^community_lists/$', views.CommunityListListView.as_view(), name='communitylist_list'),
    url(r'^community_lists/(?P<pk>\d+)/$', views.CommunityListDetailView.as_view(), name='communitylist_detail'),
    url(r'^community_lists/(?P<pk>\d+)/add/$', views.CommunityListAddToView.as_view(), name='communitylist_addto'),
    url(r'^community_lists/(?P<pk>\d+)/remove/(?P<other>\d+)/$', views.CommunityListRemoveFromView.as_view(), name='communitylist_removefrom'),
    url(r'^community_lists/add/$', views.CommunityListCreateView.as_view(), name='communitylist_add'),
    url(r'^community_lists/(?P<pk>\d+)/delete$', views.CommunityListDeleteView.as_view(), name='communitylist_delete'),
    url(r'^community_lists/import/$', views.CommunityListBulkImportView.as_view(), name='communitylist_import'),
    url(r'^community_lists/delete/$', views.CommunityListBulkDeleteView.as_view(), name='communitylist_bulk_delete'),
    url(r'^community_lists/(?P<pk>\d+)/edit/$', views.CommunityListEditView.as_view(), name='communitylist_edit'),
    url(r'^routemaps/$', views.RouteMapListView.as_view(), name='routemap_list'),
    url(r'^routemaps/add/$', views.RouteMapCreateView.as_view(), name='routemap_add'),
    url(r'^routemaps/import/$', views.RouteMapBulkImportView.as_view(), name='routemap_import'),
    url(r'^routemaps/delete/$', views.RouteMapBulkDeleteView.as_view(), name='routemap_bulk_delete'),
    url(r'^routemaps/(?P<pk>\d+)/edit/$', views.RouteMapEditView.as_view(), name='routemap_edit'),
    url(r'^asns/$', views.BGPASNListView.as_view(), name='asn_list'),
    url(r'^asns/add/$', views.BGPASNCreateView.as_view(), name='asn_add'),
    url(r'^asns/import/$', views.BGPASNBulkImportView.as_view(), name='asn_import'),
    url(r'^asns/delete/$', views.BGPASNBulkDeleteView.as_view(), name='asn_bulk_delete'),
    url(r'^asns/(?P<pk>\d+)/edit/$', views.BGPASNEditView.as_view(), name='asn_edit'),
    url(r'^asns/link/add$', views.BGPDeviceASNCreateView.as_view(), name='asn_link'),
    url(r'^asns/link/(?P<pk>\d+)/edit$', views.BGPDeviceASNEditView.as_view(), name='asn_link_edit'),
    url(r'^asns/link/(?P<pk>\d+)/delete$', views.BGPDeviceASNDeleteView.as_view(), name='asn_link_delete'),
    url(r'^asns/link/delete$', views.BGPDeviceASNBulkDeleteView.as_view(), name='asn_link_bulk_delete'),
]

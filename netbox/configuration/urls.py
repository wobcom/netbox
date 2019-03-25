from __future__ import unicode_literals

from django.conf.urls import url

from . import views

app_name = 'configuration'
urlpatterns = [
    url(r'^bgp/$', views.BGPListView.as_view(), name='bgp_list'),
    url(r'^bgp/add/$', views.BGPCreateView.as_view(), name='bgp_add'),
    url(r'^bgp/import/$', views.BGPBulkImportView.as_view(), name='bgp_import'),
    url(r'^bgp/delete/$', views.BGPBulkDeleteView.as_view(), name='bgp_bulk_delete'),
    url(r'^bgp/(?P<pk>\d+)/edit/$', views.BGPEditView.as_view(), name='bgp_edit'),
    url(r'^bgp/addto/(?P<pk>\d+)/$', views.BGPAddView.as_view(), name='bgp_addto'),
]

from __future__ import unicode_literals

from django.conf.urls import url

from . import views

app_name = 'change'
urlpatterns = [
    url(r'^(?P<pk>\d+)/$', views.DetailView.as_view(), name='change_detail'),
    url(r'^list/$', views.ListView.as_view(), name='change_list'),
    url(r'^toggle/$', views.ToggleView.as_view(), name='change_toggle'),
    url(r'^form/$', views.ChangeFormView.as_view(), name='change_form'),
    url(r'^(?P<pk>\d+)/mr/$', views.MRView.as_view(), name='change_mr'),
    url(r'^(?P<pk>\d+)/accept/$', views.AcceptView.as_view(),
        name='change_accept'),
    url(r'^(?P<pk>\d+)/reject/$', views.RejectView.as_view(),
        name='change_reject'),
    url(r'^(?P<pk>\d+)/reactivate/$', views.ReactivateView.as_view(),
        name='change_reactivate'),
]

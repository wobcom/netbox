from __future__ import unicode_literals

from django.conf.urls import url

from . import views

app_name = 'change'
urlpatterns = [
    url(r'^(?P<pk>\d+)/$', views.DetailView.as_view(), name='detail'),
    url(r'^toggle/$', views.ToggleView.as_view(), name='toggle'),
    url(r'^form/$', views.ChangeFormView.as_view(), name='form'),
    url(r'^(?P<pk>\d+)/mr/$', views.MRView.as_view(), name='mr'),
    url(r'^(?P<pk>\d+)/accept/$', views.AcceptView.as_view(), name='accept'),
    url(r'^(?P<pk>\d+)/reject/$', views.RejectView.as_view(), name='reject'),
    url(r'^(?P<pk>\d+)/reactivate/$', views.ReactivateView.as_view(),
        name='reactivate'),
]

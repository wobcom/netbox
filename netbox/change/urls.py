from __future__ import unicode_literals

from django.conf.urls import url

from . import views

app_name = 'change'
urlpatterns = [
    url(r'^toggle/$', views.ToggleView.as_view(), name='toggle'),
    url(r'^accept/(?P<pk>\d+)/$', views.AcceptView.as_view(), name='accept'),
]

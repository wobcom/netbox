from __future__ import unicode_literals

from django.urls import path, re_path

from . import views, consumers

app_name = 'change'
urlpatterns = [
    path(r'<int:pk>/', views.DetailView.as_view(), name='detail'),
    path(r'form/', views.ChangeFormView.as_view(), name='form'),
    path(r'end_change/', views.EndChangeView.as_view(), name='end_change'),
    path(r'deploy/', views.DeployView.as_view(), name='deploy'),

    path(r'provisions/', views.ProvisionsView.as_view(), name='provisions'),
    path(r'provisions/<int:pk>/', views.ProvisionSetView.as_view(), name='provision_set'),
    path(r'provisions/<int:pk>/logs/', views.ProvisionSetLogView.as_view(), name='provision_set_logs'),
]

websocket_urlpatterns = [
    path(r'change/provisions/<int:pk>/logs/ws/', consumers.LogfileConsumer),
]

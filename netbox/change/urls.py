from __future__ import unicode_literals

from django.urls import path

from . import views, consumers

app_name = 'change'
urlpatterns = [
    path(r'<int:pk>/', views.DetailView.as_view(), name='detail'),
    path(r'form/', views.ChangeFormView.as_view(), name='form'),
    path(r'end_change/', views.EndChangeView.as_view(), name='end_change'),
    path(r'deploy/', views.DeployView.as_view(), name='deploy'),

    path(r'provisions/', views.ProvisionsView.as_view(), name='provisions'),
    path(r'provisions/<int:pk>/', views.ProvisionSetView.as_view(), name='provision_set'),
    path(r'provisions/<int:pk>/terminate', views.TerminateView.as_view(), name='terminate_provision_set'),
    path(r'provisions/<int:pk>/second_stage/', views.SecondStageView.as_view(), name='second_stage'),
    path(r'provisions/<int:pk>/rollback/', views.RollbackView.as_view(), name='rollback')
]

websocket_urlpatterns = [
    path(r'ws/change/active_users/', consumers.UsersInChangeConsumer.as_asgi()),
    path(r'ws/change/provisions/status/', consumers.GlobalProvisionStatusConsumer.as_asgi()),
    path(r'ws/change/provisions/<int:pk>/logs/', consumers.LogfileConsumer.as_asgi()),
    path(r'ws/change/provisions/<int:pk>/odin/diff/', consumers.OdinDiffConsumer.as_asgi()),
    path(r'ws/change/provisions/<int:pk>/odin/commit/', consumers.OdinCommitConsumer.as_asgi()),
    path(r'ws/change/provisions/<int:pk>/status/', consumers.ProvisionStatusConsumer.as_asgi()),
]

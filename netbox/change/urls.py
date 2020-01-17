from __future__ import unicode_literals

from django.urls import path

from . import views

app_name = 'change'
urlpatterns = [
    path(r'<int:pk>/', views.DetailView.as_view(), name='detail'),
    path(r'form/', views.ChangeFormView.as_view(), name='form'),
    path(r'end_change/', views.EndChangeView.as_view(), name='end_change'),
    path(r'deploy/', views.DeployView.as_view(), name='deploy'),
    path(r'<int:pk>/finalize/', views.FinalizeView.as_view(), name='finalize'),
]

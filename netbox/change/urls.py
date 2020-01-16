from __future__ import unicode_literals

from django.urls import path

from . import views

app_name = 'change'
urlpatterns = [
    path(r'<int:pk>/', views.DetailView.as_view(), name='detail'),
    path(r'toggle/', views.ToggleView.as_view(), name='toggle'),
    path(r'form/', views.ChangeFormView.as_view(), name='form'),
    path(r'<int:pk>/finalize/', views.FinalizeView.as_view(), name='finalize'),
    path(r'<int:pk>/accept/', views.AcceptView.as_view(), name='accept'),
    path(r'<int:pk>/reject/', views.RejectView.as_view(), name='reject'),
    path(r'<int:pk>/reactivate/', views.ReactivateView.as_view(),
        name='reactivate'),
]

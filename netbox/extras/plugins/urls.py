from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path
from django.utils.module_loading import import_string

from . import views

# Initialize URL base, API, and admin URL patterns for plugins
plugin_patterns = []
plugin_api_patterns = [
    path('', views.PluginsAPIRootView.as_view(), name='api-root'),
    path('installed-plugins/', views.InstalledPluginsAPIView.as_view(), name='plugins-list')
]
plugin_admin_patterns = [
    path('installed-plugins/', staff_member_required(views.InstalledPluginsAdminView.as_view()), name='plugins_list')
]

# Register base/API URL patterns for each plugin
for plugin_path in settings.PLUGINS:
    plugin_name = plugin_path.split('.')[-1]
    app = apps.get_app_config(plugin_name)
    base_url = getattr(app, 'base_url') or app.label

    # Check if the plugin specifies any base URLs
    try:
        urlpatterns = import_string(f"{plugin_path}.urls.urlpatterns")
        plugin_patterns.append(
            path(f"{base_url}/", include((urlpatterns, app.label)))
        )
    except ImportError:
        pass

    # Check if the plugin specifies any API URLs
    try:
        urlpatterns = import_string(f"{plugin_path}.api.urls.urlpatterns")
        plugin_api_patterns.append(
            path(f"{base_url}/", include((urlpatterns, f"{app.label}-api")))
        )
    except ImportError:
        pass

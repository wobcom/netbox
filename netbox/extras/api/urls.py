from utilities.api import OrderedDefaultRouter
from . import views


router = OrderedDefaultRouter()
router.APIRootView = views.ExtrasRootView

# Custom field choices
router.register('_custom_field_choices', views.CustomFieldChoicesViewSet, basename='custom-field-choice')

# Graphs
router.register('graphs', views.GraphViewSet)

# Export templates
router.register('export-templates', views.ExportTemplateViewSet)

# Tags
router.register('tags', views.TagViewSet)

# Image attachments
router.register('image-attachments', views.ImageAttachmentViewSet)

# Config contexts
router.register('config-contexts', views.ConfigContextViewSet)

# Reports
router.register('reports', views.ReportViewSet, basename='report')

# Scripts
router.register('scripts', views.ScriptViewSet, basename='script')

# Change logging
router.register('object-changes', views.ObjectChangeViewSet)

# Job Results
router.register('job-results', views.JobResultViewSet)

app_name = 'extras-api'
urlpatterns = router.urls

from __future__ import unicode_literals

from rest_framework import routers

from .. import views


class ChangeRootView(routers.APIRootView):
    """
    Change API root view
    """
    def get_view_name(self):
        return 'Change'


router = routers.DefaultRouter()
router.APIRootView = ChangeRootView
router.register(r'accepted', views.ReviewedView, 'change-accepted')
router.register(r'rejected', views.RejectedView, 'change-rejected')
router.register(r'provisioned', views.ProvisionedView, 'change-provisioned')
router.register(r'failed', views.FailedView, 'change-failed')

app_name = 'change-api'
urlpatterns = router.urls

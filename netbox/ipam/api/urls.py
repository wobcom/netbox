from utilities.api import OrderedDefaultRouter
from . import views


router = OrderedDefaultRouter()
router.APIRootView = views.IPAMRootView

# VRFs
router.register('vrfs', views.VRFViewSet)

# RIRs
router.register('rirs', views.RIRViewSet)

# Aggregates
router.register('aggregates', views.AggregateViewSet)

# Prefixes
router.register('roles', views.RoleViewSet)
router.register('prefixes', views.PrefixViewSet)

# IP addresses
router.register('ip-addresses', views.IPAddressViewSet)

# VLANs
router.register('vlan-groups', views.VLANGroupViewSet)
router.register('vlans', views.VLANViewSet)

# Services
router.register('services', views.ServiceViewSet)

# Overlay Networks
router.register('overlay-networks', views.OverlayNetworkViewSet)
router.register('overlay-network-groups', views.OverlayNetworkGroupViewSet)

app_name = 'ipam-api'
urlpatterns = router.urls

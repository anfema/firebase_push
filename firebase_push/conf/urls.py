from rest_framework import routers

from firebase_push.views import DeviceRegistrationViewSet


router = routers.SimpleRouter()
router.register(r"firebase-push", DeviceRegistrationViewSet, basename="firebase-device")

urlpatterns = router.urls

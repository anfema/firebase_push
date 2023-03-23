from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string
from rest_framework.viewsets import ModelViewSet

from firebase_push.serializers import FCMDeviceSerializer
from firebase_push.utils import get_device_model


FCMDevice = get_device_model()

try:
    get_user = import_string(settings.FCM_FETCH_USER_FUNCTION)
except AttributeError:
    get_user = import_string("firebase_push.defaults.get_user")


class DeviceRegistrationViewSet(ModelViewSet):
    serializer_class = FCMDeviceSerializer
    lookup_field = "registration_id"

    def get_queryset(self):
        user = get_user(self.request)
        return FCMDevice.objects.filter(user_id=user)

    def get_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(FCMDevice.objects.all())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

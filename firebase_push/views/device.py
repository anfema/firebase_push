from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from django.conf import settings
from django.utils.module_loading import import_string
from django.shortcuts import get_object_or_404

from firebase_push.models import FCMDevice, FCMTopic
from firebase_push.serializers import FCMDeviceSerializer

get_user = import_string(settings.FCM_FETCH_USER_FUNCTION)


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


# class DeviceRegistrationViewSet(ViewSet):
#     lookup_field = "registration_id"

#     def create(self, request):
#         """
#         Custom endpoint to register the device (create or update)
#         """
#         registration_id = request.data.get("registration_id")
#         if registration_id is None:
#             raise ValidationError

#         topics = request.data.get("topics")
#         if topics is None:
#             topics = ["default"]

#         topics = FCMTopic.objects.filter(name__in=topics)
#         user = get_user(request)

#         try:
#             fcm_device = FCMDevice.objects.get(registration_id=registration_id)

#             # If user changes invalidate old registration and create a new one
#             if fcm_device.user != user:
#                 fcm_device.delete()
#                 fcm_device = None
#         except FCMDevice.DoesNotExist:
#             fcm_device = None

#         # No registration found or invalidated previously? Create a new one.
#         if fcm_device is None:
#             fcm_device = FCMDevice.objects.create(
#                 registration_id=registration_id, topics=topics, user=user, platform=FCMDevice.Platforms.UNKNOWN
#             )

#         # topics updated?
#         current_topics = set(fcm_device.topics.all())
#         new_topics = set(topics)
#         if current_topics != new_topics:
#             fcm_device.topics = topics
#             fcm_device.save()

#         # update device infos (enable device on success if required)
#         update_device_info.delay(fcm_device.registration_id)

#         # return registration object
#         serializer = FCMDeviceSerializer(fcm_device)
#         return Response(serializer.data)

#     def destroy(self, request, registration_id=None):
#         """
#         Custom endpoint to remove the device
#         """
#         if registration_id is None:
#             raise ValidationError

#         try:
#             fcm_device = FCMDevice.objects.get(registration_id=registration_id)
#         except FCMDevice.DoesNotExist:
#             raise NotFound

#         # check for permission
#         user = get_user(request)
#         if fcm_device.user != user:
#             raise PermissionDenied

#         # disable device
#         fcm_device.delete()

#         # return deleted item
#         serializer = FCMDeviceSerializer(fcm_device)
#         return Response(serializer.data)

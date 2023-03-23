from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import serializers

from firebase_push.models import FCMTopic
from firebase_push.utils import get_device_model


FCMDevice = get_device_model()

try:
    get_user = import_string(settings.FCM_FETCH_USER_FUNCTION)
except AttributeError:
    get_user = import_string("firebase_push.defaults.get_user")


class FCMDeviceSerializer(serializers.ModelSerializer):
    registration_id = serializers.CharField(allow_blank=False, min_length=10, max_length=255)
    topics = serializers.SlugRelatedField(many=True, slug_field="name", queryset=FCMTopic.objects.all())

    class Meta:
        model = FCMDevice
        exclude = ("user", "id")
        read_only_fields = ("created_at", "updated_at", "registration_id")

    def create(self, validated_data):
        user = get_user(self.context["request"])
        try:
            fcm_device = FCMDevice.objects.get(registration_id=validated_data["registration_id"])

            # if user does not match, destroy registration and re-create
            if fcm_device.user.id != user:
                fcm_device.delete()
                fcm_device = None
        except FCMDevice.DoesNotExist:
            # registration does not exist
            fcm_device = None

        # run create normally when fcm_device does not exist
        if fcm_device is None:
            validated_data["user_id"] = get_user(self.context["request"])
            return super().create(validated_data)

        # run an update instead if it exists
        return self.update(fcm_device, validated_data)

    def update(self, instance, validated_data):
        # when user does not match, destroy registration and re-create
        user = get_user(self.context["request"])
        if instance.user.id != user:
            validated_data["registration_id"] = instance.registration_id
            instance.delete()
            return self.create(validated_data)

        # user matches, make sure to add the user id to validated_data
        validated_data["user_id"] = user

        # Someone updated the device, so it is active again
        validated_data["disabled_at"] = None
        return super().update(instance, validated_data)

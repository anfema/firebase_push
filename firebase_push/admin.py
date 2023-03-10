from typing import Any

from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.module_loading import import_string

from firebase_push.models import FCMDevice, FCMTopic


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    ordering = ("updated_at",)
    search_fields = ("registration_id", "app_version")
    list_display = ("registration_id", "platform", "app_version")


@admin.register(FCMTopic)
class FCMTopicAdmin(admin.ModelAdmin):
    ordering = ("name",)
    search_fields = ("name", "description")
    list_display = ("name", "description", "subscribers")

    def subscribers(self, instance):
        return instance.devices.count()


try:
    FCMHistory = import_string(settings.FCM_PUSH_HISTORY_MODEL)

    @admin.register(FCMHistory)
    class FCMHistoryAdmin(admin.ModelAdmin):
        ordering = ("updated_at",)
        search_fields = ("topic__name", "device__registration_id", "error_message")
        list_display = ("registration_id", "topic", "status", "created_at", "updated_at")

        def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
            return super().get_queryset(request).select_related("topic", "device")

        def registration_id(self, instance):
            return instance.device.registration_id

        def topic(self, instance):
            return instance.topic.name

except AttributeError:
    pass

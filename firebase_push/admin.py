from typing import Any

from admin_extra_buttons.api import ExtraButtonsMixin, button
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.auth import get_user_model
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from firebase_push.models import FCMTopic
from firebase_push.utils import get_device_model, get_history_model


User = get_user_model()
FCMHistory = get_history_model()
FCMDevice = get_device_model()
UserModel = FCMDevice._meta.get_field("user").related_model


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


class PushNotificationForm(forms.Form):
    title = forms.CharField(max_length=100, label="Title", required=False)
    body = forms.CharField(max_length=1024, label="Body", required=False)
    link = forms.CharField(max_length=1024, label="Link", required=False)

    user = forms.ModelChoiceField(
        UserModel.objects.annotate(device_count=Count("fcmdevice")).filter(device_count__gt=0), empty_label="User"
    )
    topic = forms.ModelChoiceField(FCMTopic.objects.all(), required=False)


class FCMHistoryAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    ordering = ("updated_at",)
    search_fields = ("topic__name", "device__registration_id", "error_message")
    list_display = ("registration_id", "topic", "status", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related("topic", "device")

    def registration_id(self, instance):
        if instance.device:
            return instance.device.registration_id
        else:
            return "-"

    def topic(self, instance):
        return instance.topic.name

    @button()
    def send_notification(self, request):
        context = self.get_common_context(request, title="Upload")
        if request.method == "POST":
            form = PushNotificationForm(request.POST)
            if form.is_valid():
                from firebase_push.message import PushMessage

                link = form.cleaned_data.get("link", None)
                pm = PushMessage(form.cleaned_data["title"], form.cleaned_data["body"], link=link)
                pm.add_user(form.cleaned_data["user"])
                topic = form.cleaned_data.get("topic", None)
                if topic:
                    pm.add_topic(topic)
                pm.send()

                # return success message
                messages.add_message(request, messages.SUCCESS, "Push notification queued!")
                return redirect(admin_urlname(context["opts"], "changelist"))
        else:
            form = PushNotificationForm()
        context["form"] = form
        return TemplateResponse(request, "firebase_push/send_push.html", context)


admin.site.register(FCMHistory, FCMHistoryAdmin)
admin.site.register(FCMDevice, FCMDeviceAdmin)

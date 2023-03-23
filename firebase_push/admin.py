from typing import Any

from admin_extra_buttons.api import ExtraButtonsMixin, button
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.auth import get_user_model
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.module_loading import import_string

from firebase_push.models import FCMDevice, FCMTopic


try:
    UserModel = import_string(settings.FCM_USER_MODEL)
except AttributeError:
    UserModel = get_user_model()


# class PushSenderAdmin(admins.CustomPageModelAdmin):
#     fields = ("title", "body", "link", "user", "topic")
#     autocomplete_fields = ("user", "topic")


# class PushSender(CustomModelPage):
#     app_label = "firebase_push"

#     # Define some fields.
#     title = models.CharField("Push Notification Title", max_length=100, blank=True)
#     body = models.CharField("Push Notification Body", max_length=1024, blank=True)
#     link = models.CharField("Push Notification Deeplink", max_length=1024, blank=True)

#     user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
#     topic = models.ForeignKey(FCMTopic, null=True, blank=True, on_delete=models.CASCADE)

#     admin_cls = PushSenderAdmin  # set admin class for this page

#     class Meta:
#         verbose_name = "Send Push Notification"

#     def save(self):
#         from firebase_push.message import PushMessage

#         link = self.link if self.link else None
#         pm = PushMessage(self.title, self.body, link=link)
#         pm.add_user(self.user)
#         if self.topic:
#             pm.add_topic(self.topic)
#         pm.send()

#         # self.bound_admin has some useful methods.
#         # self.bound_request allows you to access current HTTP request.
#         self.bound_admin.message_success(self.bound_request, "Notification queued!")

#         super().save()


# PushSender.register()


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
        return instance.device.registration_id

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


try:
    FCMHistory = import_string(settings.FCM_PUSH_HISTORY_MODEL)
    admin.site.register(FCMHistory, FCMHistoryAdmin)
except AttributeError:
    pass

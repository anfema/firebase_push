from admin_extra_buttons.api import ExtraButtonsMixin, button
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from firebase_push.models import FCMTopic
from firebase_push.utils import get_device_model, get_history_model


User = get_user_model()
FCMHistory = get_history_model()
FCMDevice = get_device_model()
UserModel = FCMDevice._meta.get_field("user").related_model


class IsActiveFilter(SimpleListFilter):
    title = _("is active")
    parameter_name = "is_active"

    def lookups(self, request, model_admin):
        return [
            ("1", _("Yes")),
            ("0", _("No")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_active=True)
        if self.value() == "0":
            return queryset.filter(is_active=False)


class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "platform",
        "is_active",
        "app_version",
        "created_at",
        "updated_at",
        "disabled_at",
    )
    list_filter = (IsActiveFilter, "platform", "app_version")
    ordering = ("updated_at",)
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "disabled_at")
    search_fields = (f"user__{User.EMAIL_FIELD}", f"user__{User.USERNAME_FIELD}", "registration_id")

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).annotate(is_active=Q(disabled_at__isnull=True))

    @admin.display(boolean=True, ordering="is_active")
    def is_active(self, instance) -> bool:
        return instance.is_active


@admin.register(FCMTopic)
class FCMTopicAdmin(admin.ModelAdmin):
    ordering = ("name",)
    search_fields = ("name", "description")
    list_display = ("name", "description", "subscribers")

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).annotate(device_count=Count("devices"))

    @admin.display(ordering="device_count")
    def subscribers(self, instance) -> int:
        return instance.device_count


class PushNotificationForm(forms.Form):
    title = forms.CharField(max_length=100, label="Title", required=False)
    body = forms.CharField(max_length=1024, label="Body", required=False)
    link = forms.CharField(max_length=1024, label="Link", required=False)

    user = forms.ModelChoiceField(
        UserModel.objects.annotate(device_count=Count(FCMDevice._meta.get_field("user").related_query_name())).filter(
            device_count__gt=0
        ),
        empty_label="User",
    )
    topic = forms.ModelChoiceField(FCMTopic.objects.all(), required=False)


class FCMHistoryAdmin(ExtraButtonsMixin, admin.ModelAdmin):
    ordering = ("updated_at",)
    search_fields = ("topic__name", "device__registration_id", "error_message")
    list_display = ("registration_id", "topic", "status", "created_at", "updated_at")
    list_filter = ("status",)
    raw_id_fields = ("user", "device", "topic")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request: HttpRequest):
        return super().get_queryset(request).select_related("topic", "device")

    @admin.display
    def registration_id(self, instance) -> str | SafeString:
        if instance.device:
            return instance.device.registration_id
        return self.get_empty_value_display()

    @admin.display
    def topic(self, instance) -> str:
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

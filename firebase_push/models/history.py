from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class FCMHistoryBase(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    message_data = models.JSONField()
    message_id = models.UUIDField()
    device = models.ForeignKey(settings.FCM_DEVICE_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    topic = models.ForeignKey("firebase_push.FCMTopic", on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=8, blank=False, null=False)
    error_message = models.TextField(default="", blank=True, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

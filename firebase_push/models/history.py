from django.utils.translation import gettext_lazy as _
from django.db import models
from django.conf import settings

UserModel = settings.FCM_USER_MODEL or settings.AUTH_USER_MODEL


class FCMHistoryBase(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    message_data = models.JSONField()
    device = models.ForeignKey("firebase_push.FCMDevice", on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, null=False, blank=False)
    topic = models.ForeignKey("firebase_push.FCMTopic", on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=8, blank=False, null=False)
    error_message = models.TextField(default="", blank=True, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

from django.utils.translation import gettext_lazy as _
from django.db import models


class FCMHistory(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    message_data = models.JSONField()
    device = models.ForeignKey("firebase_push.FCMDevice", on_delete=models.CASCADE, blank=False, null=False)
    topic = models.ForeignKey("firebase_push.FCMTopic", on_delete=models.CASCADE, blank=False, null=False)
    status = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=8, blank=False, null=False)
    error_message = models.TextField(default="", blank=True, null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

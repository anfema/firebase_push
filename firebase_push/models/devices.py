from django.conf import settings
from django.db import models


class FCMDeviceBase(models.Model):
    class Platforms(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"
        UNKNOWN = "unknown", "Unknown"

    registration_id = models.CharField(unique=True, max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False)
    topics = models.ManyToManyField("firebase_push.FCMTopic", related_name="devices")
    platform = models.CharField(
        choices=Platforms.choices, max_length=8, default=Platforms.UNKNOWN, null=False, blank=False
    )
    app_version = models.CharField(max_length=255, default="", blank=True)

    disabled_at = models.DateTimeField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Registration <{}>, platform: {}, topics: [{}], version: {}".format(
            self.registration_id,
            self.platform,
            ", ".join([topic.name for topic in self.topics.all()]),
            self.app_version,
        )

    class Meta:
        abstract = True

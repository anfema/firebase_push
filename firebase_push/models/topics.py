from django.db import models


class FCMTopic(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    description = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return self.name

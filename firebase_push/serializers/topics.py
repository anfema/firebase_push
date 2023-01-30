from rest_framework import serializers

from firebase_push.models import FCMTopic


class FCMTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMTopic
        fields = ("name",)

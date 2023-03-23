from datetime import timedelta

from django.conf import settings
from django.utils.module_loading import import_string


def get_device_model():
    app, model = settings.FCM_DEVICE_MODEL.split(".", maxsplit=1)
    path = f"{app}.models.{model}"
    FCMDevice = import_string(path)
    return FCMDevice


def get_history_model():
    app, model = settings.FCM_PUSH_HISTORY_MODEL.split(".", maxsplit=1)
    path = f"{app}.models.{model}"
    FCMHistory = import_string(path)
    return FCMHistory

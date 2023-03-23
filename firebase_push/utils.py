from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


def get_device_model():
    """
    Return the FCMDevice model that is active in this project.
    """
    try:
        return django_apps.get_model(settings.FCM_DEVICE_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("FCM_DEVICE_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "FCM_DEVICE_MODEL refers to model '%s' that has not been installed" % settings.FCM_DEVICE_MODEL
        )


def get_history_model():
    """
    Return the FCMHistory model that is active in this project.
    """
    try:
        return django_apps.get_model(settings.FCM_PUSH_HISTORY_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("FCM_PUSH_HISTORY_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "FCM_PUSH_HISTORY_MODEL refers to model '%s' that has not been installed" % settings.FCM_PUSH_HISTORY_MODEL
        )

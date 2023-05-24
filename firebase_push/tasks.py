from traceback import format_exception

import firebase_admin
import google
from celery import shared_task
from requests import HTTPError, Timeout

from firebase_push.models import FCMHistoryBase
from firebase_push.utils import get_device_model


FCMDevice = get_device_model()

FCM_RETRY_EXCEPTIONS = (HTTPError, Timeout)
firebase = firebase_admin.initialize_app()


@shared_task(autoretry_for=FCM_RETRY_EXCEPTIONS, retry_backoff=True)
def send_message(message: str):
    from .message import PushMessageBase

    message = PushMessageBase.from_json(message)
    messages = message.fanout()
    for history_items, message in messages:
        error = None
        response = None
        try:
            response = firebase_admin.messaging.send(message, app=firebase)
        except firebase_admin._messaging_utils.UnregisteredError as e:
            # Remove Token from devices
            FCMDevice.objects.filter(registration_id=message.token).delete()
            for history in history_items:
                history.device = None
            error = e
        except Exception as e:
            error = e

        # Now update the history objects
        for history in history_items:
            if response is not None and isinstance(response, str) and error is None:
                history.status = FCMHistoryBase.Status.SENT
                history.error_message = response
            else:
                history.status = FCMHistoryBase.Status.FAILED
                if error is not None:
                    history.error_message = "\n".join(format_exception(error))
                    history.error_message += "\n\nMessage:\n"
                    history.error_message += str(message)
                else:
                    history.error_message = "Unknown error"
            history.save()

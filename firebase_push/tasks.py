from traceback import format_exception

import firebase_admin
import google
from celery import shared_task
from requests import HTTPError, Timeout

from firebase_push.models import FCMHistoryBase


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
        except firebase_admin.exceptions.InvalidArgumentError as e:
            error = e
        except google.auth.exceptions.DefaultCredentialsError as e:
            error = e

        # Now update the history objects
        for history in history_items:
            if response is not None and response.success:
                history.status = FCMHistoryBase.Status.SUCCESS
            else:
                history.status = FCMHistoryBase.Status.FAILED
                if response:
                    history.error_message = repr(response.exception)
                elif error is not None:
                    history.error_message = format_exception(error)
                else:
                    history.error_message = "Unknown error"
            history.save()

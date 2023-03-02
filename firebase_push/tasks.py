from datetime import datetime
from typing import Sequence, Union, TYPE_CHECKING

from traceback import format_exception

import firebase_admin
import google

from django.conf import settings
from django.db.models import Model, QuerySet

from celery import shared_task
from requests import HTTPError, Timeout

from firebase_push.models import FCMHistoryBase

if TYPE_CHECKING:
    from .message import PushMessageBase

FCM_RETRY_EXCEPTIONS = (HTTPError, Timeout)
firebase = firebase_admin.initialize_app()


@shared_task(autoretry_for=FCM_RETRY_EXCEPTIONS, retry_backoff=True)
def send_message(message: str):
    message = PushMessageBase.deserialize(message)
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

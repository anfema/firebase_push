from datetime import datetime
from typing import Sequence, Union, TYPE_CHECKING

import firebase_admin

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
def send_message(message: "PushMessageBase"):
    messages = message.fanout()
    for history_items, message in messages:
        response = firebase_admin.messaging.send(message, app=firebase)

        # Now update the history objects
        for history in history_items:
            if response.success:
                history.status = FCMHistoryBase.Status.SUCCESS
            else:
                history.status = FCMHistoryBase.Status.FAILED
                history.error_message = repr(response.exception)
            history.save()

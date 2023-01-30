from datetime import datetime
from typing import List, Set, Union

import firebase_admin

from django.conf import settings

from celery import shared_task
from requests import HTTPError, Timeout

from firebase_push.models import FCMDevice

RegistrationIds = Union[List[str], Set[str]]

FCM_RETRY_EXCEPTIONS = (HTTPError, Timeout)
firebase = firebase_admin.initialize_app()


@shared_task(autoretry_for=FCM_RETRY_EXCEPTIONS, retry_backoff=True)
def send_message(registration_id: str):
    pass

from typing import Sequence, Optional, Union, Tuple, Any
from datetime import datetime
import re

from firebase_admin.messaging import (
    Message,
    Notification,
    AndroidConfig,
    AndroidNotification,
    WebpushConfig,
    WebpushNotification,
    WebpushNotificationAction,
    APNSConfig,
    APNSPayload,
    Aps,
    ApsAlert,
)

from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy

from django.utils.module_loading import import_string
from django.db.models import Model, QuerySet, Q
from django.conf import settings

from firebase_push.models import FCMDevice, FCMTopic

from .tasks import send_message_to_devices, send_message_to_topics, send_message_to_users

UserModel: Model = import_string(settings.FCM_USER_MODEL or settings.AUTH_USER_MODEL)

#
# TODO:
#
# - Image content for notifications on android /web
# - Launch image for iOS apps


class PushMessageBase:
    """Push notification message base class

    Common attributes:

    - ``collapse_id``: If multiple messages with this ID are sent they are collapsed
    - ``badge_count``: Badge count to display on app icon, may not work for all android devices,
      set to 0 to remove badge
    - ``data_available``: Set to ``True`` to trigger the app to be launched in background for a
      data download.
    - ``sound``: Play a sound for the notification, set to ``default`` to play default sound or
      to name of sound file in app-bundle otherwise.
    - ``data``: Custom dictionary of strings to append as data to the message

    Android specific:
    - ``android_icon``: Icon for the notification
    - ``color``: CSS-Style Hex color for the notification
    - ``expiration``: Date until which the message is valid to be delivered
    - ``is_priority``: Set to ``True`` to make it a priority message

    Web specific:
    - ``web_actions``: Actions for the push notifications, is a tuple: ("title", "action", "icon")
    - ``web_icon``: Icon for the notification
    """

    def __init__(self) -> None:
        self._topics: list[str] = []
        self._devices: list[str] = []
        self._users: Optional[Union[Q, QuerySet]] = None

        # Common
        self.collapse_id: Optional[str] = None
        self.badge_count: Optional[int] = None
        self.data_available: Optional[bool] = None
        self.sound: Optional[str] = None
        self.data: Optional[dict[str, str]] = None

        # Android
        self.android_icon: Optional[str] = None
        self.color: Optional[str] = None
        self.expiration: Optional[datetime] = None
        self.is_priority: bool = False

        # Web
        self.web_actions: Optional[Tuple[str, str, str]] = None
        self.web_icon: Optional[str] = None

    @property
    def topics(self) -> list[str]:
        return self._topics

    @topics.setter
    def topics(self, value: list[str]):
        self._topics = value

    def add_topic(self, topic: str):
        self._topics.append(topic)

    def remove_topic(self, topic: str):
        self._topics.remove(topic)

    @property
    def devices(self) -> list[str]:
        return self._devices

    @devices.setter
    def devices(self, value: list[str]):
        self._devices = value

    def add_device(self, registration_id: str):
        self._devices.append(registration_id)

    def remove_device(self, registration_id: str):
        self._devices.remove(registration_id)

    @property
    def users(self) -> Optional[QuerySet]:
        if isinstance(self._users, QuerySet):
            return self._users

        if len(self._users) == 0:
            return None
        q = self._users[0]
        if len(self._users) > 1:
            for nq in self._users[1:]:
                q |= nq
        return UserModel.objects.filter(q)

    @users.setter
    def users(self, value: QuerySet):
        self._users = value

    def add_user(self, user: UserModel):
        if isinstance(self._users, QuerySet):
            self._users = self._users | UserModel.objects.filter(pk=user.pk)
        else:
            if self._users is None:
                self._users = []
            self._users.append(Q(pk=user.pk))

    def remove_user(self, user: UserModel):
        if isinstance(self._users, QuerySet):
            self._users = self._users.exclude(pk=user.pk)
        else:
            self._users.remove(Q(pk=user.pk))

    def send(self):
        if self._users is not None:
            if not self._users.exists():
                raise UserModel.DoesNotExist
            return send_message_to_users(self, self.users)
        if self._topics:
            for topic in self._topics:
                if not FCMTopic.objects.filter(name=topic).exists():
                    FCMTopic.objects.create(name=topic)
            return send_message_to_topics(self, self._topics)
        if self._devices:
            if not FCMDevice.objects.filter(registration_id__in=self._devices).exists():
                raise FCMDevice.DoesNotExist
            return send_message_to_devices(self, self._devices)
        raise ValueError("No target to send message to, either set a user, device or topic")

    def render(self) -> Message:
        # Apple specific
        aps = Aps(
            badge=self.badge_count,
            sound=self.sound,
            content_available=self.data_available,
            thread_id=self.collapse_id,
        )
        apns_payload = APNSPayload(aps)
        apns = APNSConfig(payload=apns_payload)

        # Android specific

        android_notification = AndroidNotification(
            icon=self.android_icon,
            color=self.color,
            notification_count=self.badge_count,
        )
        if self.sound == "default":
            android_notification.default_sound = True
        elif self.sound:
            android_notification.sound = self.sound

        android = AndroidConfig(
            self.collapse_id, "high" if self.is_priority else "normal", notification=android_notification
        )
        if self.expiration:
            android.ttl = self.expiration - datetime.now()

        # Web specific
        actions: list[WebpushNotificationAction] = []
        for (title, action, icon) in self.web_actions:
            actions.append(WebpushNotificationAction(action, title, icon))

        web_notification = WebpushNotification(
            icon=self.web_icon,
            language="en",
            actions=actions,
        )
        web = WebpushConfig(notification=web_notification)

        # Construct message
        msg = Message(self.data, apns=apns, android=android, webpush=web)
        return msg


class PushMessage(PushMessageBase):
    """Push notification message container

    This inherits all attributes from the base class and add these new ones:

    Common attributes:

    - ``title``: Message title
    - ``body``: Message body
    - ``link``: Message target link
    """

    def __init__(self, title: str, body: str, link: Optional[str] = None) -> None:
        self.title = title
        self.body = body
        self.link = link
        super().__init__()

    def render(self) -> Message:
        if self.data is None:
            self.data = {}
        self.data["link"] = self.link
        msg = super().render()
        msg.notification = Notification(self.title, self.body)
        return msg


class LocalizedPushMessage(PushMessageBase):
    """This is the localizable version of a ``PushMessage`` all values for
    display strings are localization keys here.

    This inherits all attributes from the base class and add these new ones:

    Common attributes:

    - ``title_loc``: Message title identifier, can contain android style placeholders
    - ``title_args``: Arguments for the placeholders in the localized title string
    - ``body_loc``: Message body identifier, can contain android style placeholders
    - ``body_args``: Arguments for the placeholders in the localised body string
    - ``link``: Message target link

    Apple specific:
    - ``action_loc``: Identifier for the action item that is displayed (optional,
      will not display an action if undefined)

    Web specific:
    - ``web_actions``: ``action`` and ``title`` should be translatable strings or
      translation identifiers
    """

    def __init__(
        self,
        title_loc: str,
        body_loc: str,
        title_args: Optional[Sequence[Any]] = None,
        body_args: Optional[Sequence[Any]] = None,
        link: Optional[str] = None,
    ) -> None:
        self.title_loc = title_loc
        self.title_args = title_args
        self.body_loc = body_loc
        self.body_args = body_args
        self.link = link
        self.action_loc: Optional[str] = None
        super().__init__()

    def _apple_loc(self, loc: str) -> str:
        # Converts Android/printf style format specifiers into simpler %n$@ specifiers
        # for apple.
        return re.sub(r"%(([0-9]*)\$)? ?[#'0-9.,\-+hl]*[a-zA-Z@]", r"%\1@", loc)

    def _web_loc(self, loc: str) -> str:
        # Converts Android/printf style format specifiers into something we can use
        # with python's ``format``. Be careful, not everything will work.
        return re.sub(r"%(([0-9]*)\$)? ?([#'0-9.,\-+hl]*[a-zA-Z@])", r"{\2:\3}", _(loc))

    def render(self) -> Message:
        if self.data is None:
            self.data = {}
        self.data["link"] = self.link

        msg = super().render()

        # Apple specific code
        aps_alert = ApsAlert(
            loc_key=self._apple_loc(self.body_loc),
            loc_args=self.body_args,
            title_loc_key=self._apple_loc(self.title_loc),
            title_loc_args=self.title_args,
            action_loc_key=self.action_loc,
        )

        apns = msg.apns
        if apns is None:
            apns = APNSConfig()
            msg.apns = apns

        apns_payload = apns.payload
        if apns_payload is None:
            apns_payload = APNSPayload()
            apns.payload = apns_payload

        aps = apns_payload.aps
        if aps is None:
            aps = Aps(
                badge=self.badge_count,
                sound=self.sound,
                content_available=self.data_available,
                thread_id=self.collapse_id,
            )
            apns_payload.aps = aps
        aps.alert = aps_alert

        # Android specfic code
        android = msg.android
        if android is None:
            ttl = self.expiration - datetime.now()
            android = AndroidConfig(self.collapse_id, "high" if self.is_priority else "normal", ttl)
            msg.android = android

        android_notification = AndroidNotification(
            icon=self.android_icon,
            color=self.color,
            body_loc_key=self.body_loc,
            body_loc_args=self.body_args,
            title_loc_key=self.title_loc,
            title_loc_args=self.title_args,
            notification_count=self.badge_count,
        )
        if self.sound == "default":
            android_notification.default_sound = True
        elif self.sound:
            android_notification.sound = self.sound
        msg.android.notification = android_notification

        # Web specific code
        web = msg.webpush
        if web is None:
            web = WebpushConfig()
            msg.webpush = web

        actions: list[WebpushNotificationAction] = []
        for (title, action, icon) in self.web_actions:
            actions.append(WebpushNotificationAction(_(action), _(title), icon))

        web_notification = WebpushNotification(
            title=format_lazy(self._web_loc(self.title_loc), *self.title_args),
            body=format_lazy(self._web_loc(self.body_loc), *self.body_args),
            icon=self.web_icon,
            language="en",
            actions=actions,
        )

        msg.webpush.notification = web_notification

        return msg

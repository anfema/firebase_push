import re
from datetime import datetime
from typing import Any, Optional, Sequence

from django.conf import settings
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from firebase_admin.messaging import (
    AndroidConfig,
    AndroidNotification,
    APNSConfig,
    APNSPayload,
    Aps,
    ApsAlert,
    Message,
    WebpushConfig,
    WebpushNotification,
    WebpushNotificationAction,
)

from .base import PushMessageBase


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
        title_loc: str = "",
        body_loc: str = "",
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

    def serialize(self) -> dict[str, Any]:
        result = super().serialize()
        result.update(
            dict(
                title_loc=self.title_loc,
                title_args=self.title_args,
                body_loc=self.body_loc,
                body_args=self.body_args,
                link=self.link,
                action_loc=self.action_loc,
            )
        )
        return result

    def deserialize(self, data: dict[str, Any]):
        super().deserialize(data)
        self.title_loc = data["title_loc"]
        self.title_ars = data["title_args"]
        self.body_loc = data["body_loc"]
        self.body_args = data["body_args"]
        self.link = data["link"]
        self.action_loc = data["action_loc"]

    def render(self) -> Message:
        if self.data is None:
            self.data = {}
        if self.link:
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
        for title, action, icon in self.web_actions:
            actions.append(WebpushNotificationAction(_(action), _(title), icon))

        web_notification = WebpushNotification(
            title=format_lazy(self._web_loc(self.title_loc), *self.title_args),
            body=format_lazy(self._web_loc(self.body_loc), *self.body_args),
            icon=self.web_icon,
            language=settings.LANGUAGE_CODE or "en",
            actions=actions,
        )

        msg.webpush.notification = web_notification

        return msg

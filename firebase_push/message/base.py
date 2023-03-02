from typing import Optional, Union, Tuple, Any, Self
from datetime import datetime
import json
import inspect
from copy import copy
from uuid import uuid4

from firebase_admin.messaging import (
    Message,
    AndroidConfig,
    AndroidNotification,
    WebpushConfig,
    WebpushNotification,
    WebpushNotificationAction,
    APNSConfig,
    APNSPayload,
    Aps,
)

from django.utils.module_loading import import_string
from django.db.models import Model, QuerySet, Q
from django.conf import settings

from firebase_push.models import FCMDevice, FCMTopic, FCMHistoryBase

from firebase_push.tasks import send_message

if settings.FCM_USER_MODEL:
    UserModel: Model = import_string(settings.FCM_USER_MODEL)
else:
    from django.contrib.auth import get_user_model

    UserModel = get_user_model()

FCMHistory: FCMHistoryBase = import_string(settings.FCM_PUSH_HISTORY_MODEL)


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
        self._users: list[Any] = []

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

        # Internal message id
        self.uuid = str(uuid4())

    def serialize(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        attributes = dir(self)
        for attr in attributes:
            # skip internals
            if attr.startswith("__"):
                continue
            # skip values that have hidden variables
            if "_" + attr in attributes:
                continue
            # skip everything that is not an attribute
            value = getattr(self, attr)
            if inspect.ismethod(value) or inspect.isfunction(value):
                continue

            result[attr] = value

        # save the class for the deserializer
        result["__class__"] = ".".join((self.__class__.__module__, self.__class__.__name__))
        return result

    @classmethod
    def deserialize(cls, data: str) -> Self:
        tree = json.loads(data)

        # try instanciating class from serialized data
        klass = import_string(tree["__class__"])
        c = klass()

        # set all attributes
        for key, value in tree.items():
            if key.startswith("__"):  # skip internals
                continue
            setattr(c, key, value)
        return c

    @property
    def topics(self) -> list[str]:
        return self._topics

    @topics.setter
    def topics(self, value: list[str]):
        self._topics = value

    def add_topic(self, topic: Union[str, FCMTopic]):
        if isinstance(topic, FCMTopic):
            topic = topic.name
        self._topics.append(topic)

    def remove_topic(self, topic: Union[str, FCMTopic]):
        if isinstance(topic, FCMTopic):
            topic = topic.name
        self._topics.remove(topic)

    @property
    def devices(self) -> list[str]:
        return self._devices

    @devices.setter
    def devices(self, value: list[str]):
        self._devices = value

    def add_device(self, registration_id: Optional[str] = None, device: Optional[FCMDevice] = None):
        if registration_id:
            self._devices.append(registration_id)
        elif device:
            self._devices.append(device.registration_id)
        else:
            raise ValueError("Either specify registration_id or device")

    def remove_device(self, registration_id: Optional[str] = None, device: Optional[FCMDevice] = None):
        if registration_id:
            self._devices.remove(registration_id)
        elif device:
            self._devices.remove(device.registration_id)
        else:
            raise ValueError("Either specify registration_id or device")

    @property
    def users(self) -> Optional[QuerySet]:
        return UserModel.objects.filter(pk__in=self._users)

    @users.setter
    def users(self, value: QuerySet):
        self._users = value.values_list("pk", flat=True)

    def add_user(self, user: UserModel):
        self._users.append(user.pk)

    def remove_user(self, user: UserModel):
        self._users.remove(user.pk)

    def create_history_entries(
        self,
        message: Message,
        user: Optional[UserModel] = None,
        topic: Optional[str] = None,
        device: Optional[FCMDevice] = None,
    ) -> list[FCMHistoryBase]:
        """Create a FCMHistory entry for each sent message

        Override this function to add custom data to the history objects.
        Do not save the objects yet, this function will be called at the
        appropriate time and saving of objects will be done by the caller.

        This will be bulk created, so no fired signals or calls on the
        save() function of the model.

        :returns: List of unsaved FCMHistory entries
        """
        message_data = json.loads(str(message))
        entries: list[FCMHistory] = []

        if user is not None:
            entries.append(
                FCMHistory(
                    message_data=message_data,
                    message_id=self.uuid,
                    user=user,
                    device=device,
                    topic=FCMTopic.objects.get(name=topic) if topic else None,
                    status=FCMHistoryBase.Status.PENDING,
                )
            )
        elif topic and device:
            entries.append(
                FCMHistory(
                    message_data=message_data,
                    message_id=self.uuid,
                    user=device.user,
                    device=device,
                    topic=FCMTopic.objects.get(name=topic),
                    status=FCMHistoryBase.Status.PENDING,
                )
            )
        elif topic:
            for device in FCMDevice.objects.filter(topic__name=topic, disabled_at__isnull=True):
                entries.append(
                    FCMHistory(
                        message_data=message_data,
                        message_id=self.uuid,
                        user=device.user,
                        device=device,
                        topic=FCMTopic.objects.get(name=topic),
                        status=FCMHistoryBase.Status.PENDING,
                    )
                )
        elif device:
            entries.append(
                FCMHistory(
                    message_data=message_data,
                    message_id=self.uuid,
                    device=device,
                    topic=FCMTopic.objects.get(name=topic) if topic else None,
                    status=FCMHistoryBase.Status.PENDING,
                )
            )
        return entries

    def fanout(self) -> list[Tuple[list[FCMHistoryBase], Message]]:
        """Create message object for each device we want to address

        :returns: List of messages to send to firebase
        """
        rendered = self.render()
        topic = self._topics[0] if len(self._topics) > 0 else "default"
        topic_obj = FCMTopic.objects.get(name=topic)

        messages: list[Tuple[list[FCMHistoryBase], Message]] = []
        if self._users:
            for user in self.users:
                for device in FCMDevice.objects.filter(user=user, disabled_at__isnull=True, topics=topic_obj):
                    msg = copy(rendered)
                    msg.token = device.registration_id
                    history = self.create_history_entries(msg, device=device, user=user, topic=topic)
                    messages.append((history, msg))
        elif self._topics:
            for topic in self._topics:
                for device in FCMDevice.objects.filter(topic__name=topic, disabled_at__isnull=True):
                    msg = copy(rendered)
                    msg.token = device.registration_id
                    history = self.create_history_entries(msg, device=device, topic=topic)
                    messages.append((history, msg))
        elif self._devices:
            for device in self._devices:
                if device.disabled_at is not None:
                    continue
                if not device.topics.contains(topic_obj):
                    continue
                msg = copy(rendered)
                msg.token = device
                history = self.create_history_entries(msg, device=device, topic=topic)
                messages.append((history, msg))

        # extract all history items and flatten the arrays
        history: list[FCMHistory] = []
        for history_items, _ in messages:
            history.extend(history_items)
        FCMHistory.objects.bulk_create(history)

        return messages

    def send(self, sync=False):
        """Send a fully configured message in the background

        Raises:
            UserModel.DoesNotExist: If a user is configured and does not exist anymore
            FCMDevice.DoesNotExist: If a device has been configured that does not exist anymore
            ValueError: When neither user, topic or device is configured
            AttributeError: When sending to a device but the device does not subscribe to the topic or is disabled
        """

        topic = self._topics[0] if len(self._topics) > 0 else "default"

        serialized = json.dumps(self.serialize())
        if self._users:
            if not self.users.exists():
                raise UserModel.DoesNotExist
            if sync:
                return send_message(serialized)
            return send_message.delay(serialized)
        if self._topics:
            for topic in self._topics:
                if not FCMTopic.objects.filter(name=topic).exists():
                    FCMTopic.objects.create(name=topic)
            if sync:
                return send_message(serialized)
            return send_message.delay(serialized)
        if self._devices:
            if not FCMDevice.objects.filter(registration_id__in=self._devices).exists():
                raise FCMDevice.DoesNotExist
            if not FCMDevice.objects.filter(
                registration_id__in=self._devices, disabled_at__isnull=True, topics__name=topic
            ).exists():
                raise AttributeError("No enabled devices subscribing to the topic found")
            if sync:
                return send_message(serialized)
            return send_message.delay(serialized)
        raise ValueError("No target to send message to, either set a user, device or topic")

    def render(self) -> Message:
        """Render a message into firebase objects

        This will be overridden by subclasses to facilitate different message types,
        for example internationalized vs standard messages/.

        :returns: Firebase Message object without receiving device token set
        """
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
        if self.web_actions:
            for (title, action, icon) in self.web_actions:
                actions.append(WebpushNotificationAction(action, title, icon))

        web_notification = WebpushNotification(
            icon=self.web_icon,
            language=settings.LANGUAGE_CODE or "en",
            actions=actions,
        )
        web = WebpushConfig(notification=web_notification)

        # Construct message
        msg = Message(self.data, apns=apns, android=android, webpush=web)
        return msg

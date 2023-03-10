from typing import Any, Optional

from firebase_admin.messaging import Message, Notification

from .base import PushMessageBase


class PushMessage(PushMessageBase):
    """Push notification message container

    This inherits all attributes from the base class and add these new ones:

    Common attributes:

    - ``title``: Message title
    - ``body``: Message body
    - ``link``: Message target link
    """

    def __init__(self, title: str = "", body: str = "", link: Optional[str] = None) -> None:
        self.title = title
        self.body = body
        self.link = link
        super().__init__()

    def serialize(self) -> dict[str, Any]:
        result = super().serialize()
        result.update(
            dict(
                title=self.title,
                body=self.body,
                link=self.link,
            )
        )
        return result

    def deserialize(self, data: dict[str, Any]):
        super().deserialize(data)
        self.title = data["title"]
        self.body = data["body"]
        self.link = data["link"]

    def render(self) -> Message:
        if self.data is None:
            self.data = {}
        if self.link:
            self.data["link"] = self.link
        msg = super().render()
        msg.notification = Notification(self.title, self.body)
        return msg

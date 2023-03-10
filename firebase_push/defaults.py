from typing import Any

from django.http import HttpRequest


def get_user(request: HttpRequest) -> Any:
    if request.user:
        return request.user.id
    return None

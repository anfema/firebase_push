"""
Django settings for firebase-push development project running on the host.
"""
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")  # set environment variables from .env.

from .base import *  # noqa


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": "localhost",
        "PORT": os.environ.get("POSTGRES_HOST_PORT"),
    }
}

# Cache
# https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-CACHES

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://localhost:{os.environ.get('REDIS_HOST_PORT')}",
    }
}

# Celery
# https://docs.celeryq.dev/en/stable/userguide/configuration.html

CELERY_BROKER_URL = f"redis://localhost:{os.environ.get('REDIS_HOST_PORT')}/1"

# import local overrides
try:
    from .local import *  # noqa
except ImportError:
    pass

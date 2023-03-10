"""
Django settings for firebase-push demo project running in docker.
"""
import os
from pathlib import Path


BASE_DIR = Path("/code/")

from .base import *  # noqa


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": "db",
        "PORT": 5432,
    }
}

# Cache
# https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-CACHES

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://cache:6379",
    }
}

# Celery
# https://docs.celeryq.dev/en/stable/userguide/configuration.html

CELERY_BROKER_URL = "redis://cache:6379/1"

# import local overrides
try:
    from .local import *  # noqa
except ImportError:
    pass

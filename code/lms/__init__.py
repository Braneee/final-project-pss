# Pastikan Celery app selalu di-load saat Django start
from .celery import app as celery_app

__all__ = ("celery_app",)

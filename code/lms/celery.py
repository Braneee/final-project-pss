"""
Celery Configuration untuk LMS
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms.settings")

app = Celery("lms")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["courses", "enrollments"])

app.conf.update(
    task_default_queue="default",
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


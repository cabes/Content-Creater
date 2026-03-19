"""Celery application configuration."""
from __future__ import annotations

import os

from celery import Celery

from src.scheduler.jobs import CELERY_BEAT_SCHEDULE, register_celery_tasks

# Create Celery app
celery_app = Celery(
    "content_creater",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule=CELERY_BEAT_SCHEDULE,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Register tasks
register_celery_tasks(celery_app)

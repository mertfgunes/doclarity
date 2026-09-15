from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "doclarity",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.extraction", "app.tasks.embedding"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)

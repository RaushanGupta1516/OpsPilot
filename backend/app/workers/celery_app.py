from celery import Celery
from app.core.config import settings

# upstash requires ssl - add ssl_cert_reqs=CERT_NONE to broker url
broker_url = settings.redis_url + "?ssl_cert_reqs=CERT_NONE"
backend_url = settings.redis_url + "?ssl_cert_reqs=CERT_NONE"

celery_app = Celery(
    "opspilot",
    broker=broker_url,
    backend=backend_url,
    include=["app.workers.monitor_task"],
)

celery_app.config_from_object("celeryconfig")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_use_ssl={"ssl_cert_reqs": "CERT_NONE"},
    redis_backend_use_ssl={"ssl_cert_reqs": "CERT_NONE"},
)
import logging
import os

from celery import Celery
from celery.utils.log import get_task_logger

BROKER_URL = os.getenv("BROKER_URL")
REDBEAT_REDIS_URL = os.getenv("REDBEAT_REDIS_URL")

app = Celery("uptime_agent", broker=BROKER_URL, include=['tasks'])
app.conf.update({
    'redbeat_redis_url': REDBEAT_REDIS_URL,
    'beat_scheduler': "redbeat.RedBeatScheduler"
})

logger = get_task_logger("uptime_agent")
logging.basicConfig(level=logging.INFO)


logger.info(f"REDIS={app.conf.broker_url}")


app.conf.beat_schedule = {
    'crawl_labels': {
        'task': 'tasks.crawl_labels',
        'schedule': 60.0,
        'options': {
            'delete_unused': False
        }
    },
}
app.conf.timezone = 'UTC'
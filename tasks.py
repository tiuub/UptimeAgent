import docker as docker
from redbeat import RedBeatSchedulerEntry
from celery.schedules import schedule

from models import *
from utils import get_redbeat_entries, get_redbeat_entrie_from_entries_by_name
from uptime_agent import app, logger

@app.task
def crawl_labels():
    entries = get_redbeat_entries(app)

    client = docker.from_env()
    containers = client.containers.list()

    for container in containers:
        container_wrapper = ContainerWrapper(container)

        if not container_wrapper.enable:
            continue

        logger.info(f"Fetching Container: {container_wrapper.name}")

        for healthcheck in container_wrapper.healthchecks:
            entry = get_redbeat_entrie_from_entries_by_name(entries, healthcheck.uid)
            if entry is not None:
                entries.remove(entry)
                interval = entry.schedule.run_every.seconds.real
                if float(interval) != healthcheck.interval:
                    logger.info(f"Changing {healthcheck.name} from {interval}s to {healthcheck.interval}s")
                    entry.schedule = schedule(run_every=interval)
                    entry.args = [container_wrapper.id, healthcheck.id]
                    entry.save()
            else:
                interval = schedule(run_every=healthcheck.interval)
                logger.info(f"Register healthcheck with interval: {interval}")
                entry = RedBeatSchedulerEntry(healthcheck.uid, 'tasks.run_healthcheck', interval, args=[container_wrapper.id, healthcheck.id], app=app)
                entry.options.setdefault("delete_unused", True)
                entry.save()

    for entry in entries:
        if entry.options.get("delete_unused", False):
            logger.info(f"Deleting {entry.name}")
            entry.delete()


@app.task
def run_healthcheck(container_id: str, healthcheck_id: str):
    client = docker.from_env()
    container = client.containers.get(container_id)

    if container is None:
        return

    container_wrapper = ContainerWrapper(container)

    healthcheck = container_wrapper.healthchecks.get(healthcheck_id)

    if healthcheck is None:
        return

    logger.info(f"[{healthcheck.uid}] enable:{healthcheck.enable}, interval:{healthcheck.interval}, status:{healthcheck.status}")
    for pusher in healthcheck.pushers:
        logger.info(f"[{pusher.uid}] method:{pusher.method}, url:{pusher.url}")
        if healthcheck.status in pusher.trigger:
            logger.info(f"[{pusher.uid}] Pushed!")
            pusher.push()


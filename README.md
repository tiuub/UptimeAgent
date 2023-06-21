# UptimeAgent
[![Latest Release](https://img.shields.io/github/v/release/tiuub/UptimeAgent)](https://github.com/tiuub/UptimeAgent/releases/latest)
[![Docker Hub All Releases](https://img.shields.io/docker/pulls/tiuub/uptimeagent)](https://hub.docker.com/repository/docker/tiuub/uptimeagent/general)
[![Issues](https://img.shields.io/github/issues/tiuub/UptimeAgent)](https://github.com/tiuub/UptimeAgent/issues)
[![GitHub](https://img.shields.io/github/license/tiuub/UptimeAgent)](https://github.com/tiuub/UptimeAgent/blob/master/LICENSE)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=5F5QB7744AD5G&source=url)


UptimeAgent is a docker image written in Python to push the status of another docker container to an external server.

## Installation

Simplest way to use the image is through docker compose.

### docker-compose.yml

```yaml
services:
  uptimeagent:
    container_name: uptimeagent
    image: tiuub/uptimeagent
    command: celery -A uptime_agent beat --loglevel=info
    environment:
      - "BROKER_URL=redis://uptimeagent-redis:6379/0"
      - "REDBEAT_REDIS_URL=redis://uptimeagent-redis:6379/1"
  uptimeagent-worker:
    container_name: uptimeagent-worker
    image: tiuub/uptimeagent
    command: celery -A uptime_agent worker --loglevel=info
    environment:
      - "BROKER_URL=redis://uptimeagent-redis:6379/0"
      - "REDBEAT_REDIS_URL=redis://uptimeagent-redis:6379/1"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
  uptimeagent-redis:
    container_name: uptimeagent-redis
    image: redis:6.2-alpine
    restart: always
```

## Usage

The agent can be started through the labels of a container. These you can easily add in the docker-compose.yml of a container.

### Example
```yaml
services:
  whoami:
    image: "containous/whoami"
    container_name: "whoami"
    healthcheck:
      test: timeout 10s bash -c ':> /dev/tcp/127.0.0.1/80' || exit 1
      interval: 30s
      timeout: 15s
      retries: 3
    labels:
      - "uptime-agent.enable=true"
      - "uptime-agent.healthcheck.docker.enable=true"
      - "uptime-agent.healthcheck.docker.interval=12"
      - "uptime-agent.healthcheck.docker.pusher.0.url=https://uptime-kuma.de/api/push/FFFFFF?status=up&msg=OK&ping="
      - "uptime-agent.healthcheck.docker.pusher.0.method=GET"
      - "uptime-agent.healthcheck.docker.pusher.0.trigger=healthy,unhealthy,starting"

      - "uptime-agent.healthcheck.ping.0.enable=true"
      - "uptime-agent.healthcheck.ping.0.url=http://whoami/"
      - "uptime-agent.healthcheck.ping.0.method=GET"
      - "uptime-agent.healthcheck.ping.0.status_codes=500"
      - "uptime-agent.healthcheck.ping.0.pusher.0.url=https://uptime-kuma.de/api/push/FFFFFF?status=up&msg={status}&ping="
      - "uptime-agent.healthcheck.ping.0.pusher.0.method=GET"
      - "uptime-agent.healthcheck.ping.0.pusher.0.trigger=healthy,unhealthy,starting,none"
      - "uptime-agent.healthcheck.ping.1.enable=true"
      - "uptime-agent.healthcheck.ping.1.url=http://whoami/"
      - "uptime-agent.healthcheck.ping.1.method=GET"
      - "uptime-agent.healthcheck.ping.1.pusher.0.url=https://uptime-kuma.de/api/push/FFFFFF?status=up&msg={status}&ping="
```


## License

[![GitHub](https://img.shields.io/github/license/tiuub/UptimeAgent)](https://github.com/tiuub/UptimeAgent/blob/master/LICENSE)


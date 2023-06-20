import re
from enum import Enum
from types import SimpleNamespace
from urllib import parse

import cachetools
import requests
from docker.models.containers import Container

import statics
from utils import create_nested_simplenamespaces


class HealthcheckCollection(list):
    def get(self, healthcheck_id):
        for obj in self:
            if obj.id == healthcheck_id:
                return obj
        return None


class Status(Enum):
    HEALTHY = 1
    UNHEALTHY = 2
    STARTING = 3
    NONE = 4


class ContainerWrapper:
    id: str
    name: str
    enable: bool
    container: Container

    def __init__(self, container):
        self.container = container

    @property
    def id(self) -> str:
        return self.container.id

    @property
    def name(self) -> str:
        return self.container.name

    @property
    def labels(self) -> dict:
        return self.container.labels

    @property
    def app_labels(self) -> SimpleNamespace:
        filtered_labels = create_nested_simplenamespaces(self.labels, statics.PREFIX)
        if hasattr(filtered_labels, statics.PREFIX):
            return getattr(filtered_labels, statics.PREFIX)
        return SimpleNamespace()

    @property
    def enable(self) -> bool:
        if not hasattr(self.app_labels, "enable"):
            return False
        return getattr(self.app_labels, "enable")

    @property
    def healthchecks(self) -> HealthcheckCollection:
        if not hasattr(self.app_labels, "healthcheck"):
            return HealthcheckCollection()

        out = HealthcheckCollection()
        healthcheck = getattr(self.app_labels, "healthcheck")
        if hasattr(healthcheck, "docker"):
            out.append(DockerHealthcheck(self, getattr(healthcheck, "docker"), "docker"))

        if hasattr(healthcheck, "ping"):
            ping = getattr(healthcheck, "ping")
            for k, v in ping.__dict__.items():
                out.append(PingHealthcheck(self, v, k))
        return out

    def reload(self):
        self.container.reload()

    def get_attr_by_path(self, path):
        keys = path.split('.')
        value = self.container.attrs
        try:
            for key in keys:
                if key.endswith(']'):
                    # Handle list index access
                    index = int(key[key.index('[') + 1:-1])
                    value = value[key[:key.index('[')]][index]
                else:
                    value = value[key]
            return value
        except (KeyError, IndexError):
            return None


class Healthcheck:
    container_wrapper: ContainerWrapper
    name: str

    def __init__(self, container_wrapper, data, name):
        self.container_wrapper = container_wrapper
        self._data = data
        self.name = name

    @property
    def id(self) -> str:
        return f"{self.__class__.__name__}/{self.name}"

    @property
    def uid(self) -> str:
        return f"{self.container_wrapper.id}/{self.id}"

    @property
    def enable(self) -> bool:
        if not hasattr(self._data, "enable"):
            return True
        return getattr(self._data, "enable")

    @property
    def interval(self) -> int:
        if not hasattr(self._data, "interval"):
            return 30
        return int(getattr(self._data, "interval"))

    @property
    def pushers(self) -> list:
        if not hasattr(self._data, "pusher"):
            return []

        out = []
        pusher = getattr(self._data, "pusher")
        for k, v in pusher.__dict__.items():
            out.append(Pusher(self, v, k))
        return out

    @property
    def status(self) -> Status:
        return Status.NONE

    def push_all(self):
        for pusher in self.pushers:
            pusher.push()


class DockerHealthcheck(Healthcheck):
    @property
    def status(self) -> Status:
        self.container_wrapper.reload()
        status = self.container_wrapper.get_attr_by_path("State.Health.Status")
        if status is None:
            return Status.NONE

        if status.__eq__("healthy"):
            return Status.HEALTHY
        elif status.__eq__("unhealthy"):
            return Status.UNHEALTHY
        elif status.__eq__("starting"):
            return Status.STARTING

        return Status.NONE


class PingHealthcheck(Healthcheck):
    @property
    def url(self) -> str:
        if not hasattr(self._data, "url"):
            raise Exception("Missing url!")
        return getattr(self._data, "url")

    @property
    def method(self) -> str:
        if not hasattr(self._data, "method"):
            return "GET"
        return getattr(self._data, "method")

    @property
    def timeout(self) -> int:
        if not hasattr(self._data, "timeout"):
            return 5
        return int(getattr(self._data, "timeout"))

    @property
    def status_codes(self) -> list:
        if not hasattr(self._data, "status_codes"):
            return [200]
        status_codes = getattr(self._data, "status_codes")
        if status_codes is not None:
            status_codes = [int(x) for x in str(status_codes).split(",")]
            return status_codes
        return [200]

    @property
    @cachetools.cached(cache=cachetools.TTLCache(maxsize=1024, ttl=5))
    def status(self) -> Status:
        session = requests.Session()
        session.trust_env = False

        try:
            r = session.request(self.method, self.url, timeout=self.timeout)
        except requests.exceptions.Timeout:
            return Status.UNHEALTHY
        except requests.exceptions.ConnectionError:
            return Status.UNHEALTHY

        if r.status_code not in self.status_codes:
            return Status.UNHEALTHY
        return Status.HEALTHY


class Pusher:
    url: str
    method: str

    healthcheck: Healthcheck
    name: str

    def __init__(self, healthcheck, data, name):
        self.healthcheck = healthcheck
        self._data = data
        self.name = name

    @property
    def id(self) -> str:
        return f"{self.__class__.__name__}/{self.name}"

    @property
    def uid(self) -> str:
        return f"{self.healthcheck.uid}/{self.id}"

    @property
    def url(self) -> str:
        if not hasattr(self._data, "url"):
            raise Exception("Missing url!")

        url = getattr(self._data, "url")

        url = url.replace("{status}", self.healthcheck.status.name)

        pattern = r"\{([^}]*)\}"
        matches = re.findall(pattern, url)

        for key in matches:
            value = str(self.healthcheck.container_wrapper.get_attr_by_path(key))
            value_safe = parse.quote(value)
            url = url.replace(f"{{{key}}}", value_safe)
        return url

    @property
    def method(self) -> str:
        if not hasattr(self._data, "method"):
            return "GET"
        return getattr(self._data, "method")

    @property
    def trigger(self) -> list:
        if not hasattr(self._data, 'trigger'):
            return [Status.HEALTHY]

        trigger_str = getattr(self._data, 'trigger')
        trigger_values = trigger_str.split(',')

        trigger_enums = [Status.__members__[str(value).upper()] for value in trigger_values]
        return trigger_enums

    @property
    def timeout(self) -> int:
        if not hasattr(self._data, "timeout"):
            return 5
        return int(getattr(self._data, "timeout"))

    def push(self):
        try:
            r = requests.request(self.method, self.url, timeout=self.timeout)
            return r.status_code
        except requests.exceptions.Timeout:
            return 0
        except requests.exceptions.ConnectionError:
            return -1

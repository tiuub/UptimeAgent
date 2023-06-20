from types import SimpleNamespace

from redbeat import schedulers


def create_nested_simplenamespaces(data, prefix=None):
    result = {}
    for key, value in data.items():
        if prefix and not key.startswith(prefix):
            continue
        parts = key.split('.')
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return convert_to_simplenamespaces(result)

def convert_to_simplenamespaces(data):
    if isinstance(data, dict):
        return SimpleNamespace(**{k: convert_to_simplenamespaces(v) for k, v in data.items()})
    return data

def get_redbeat_entries(app):
    redis = schedulers.get_redis(app)
    conf = schedulers.RedBeatConfig(app)
    keys = redis.zrange(conf.schedule_key, 0, -1)
    entries = [schedulers.RedBeatSchedulerEntry.from_key(key, app=app)
               for key in keys]
    return entries

def get_redbeat_entrie_from_entries_by_name(entries, name):
    if entries is None or len(entries) <= 0:
        return None

    return next((entrie for entrie in entries if entrie.name == name), None)


from os import environ
import os


class BaseConfig(dict):
    def __init__(self, env_key='', **kwargs):
        self.env_key = env_key
        dict.__init__(self)
        self.update_default(kwargs)

    def __getattr__(self, item):
        return self.get_item(item) or self.get_item(item.upper()) \
               or self.get_item(item.lower()) or self.get_default(item)

    def get_item(self, item):
        if item.upper() in self:
            return self[item.upper()]
        return environ.get(self.env_key.upper() + item) or environ.get(self.env_key.lower() + item) or environ.get(item)

    def from_json(self, path):
        import json
        self.update(json.load(open(path, encoding='utf-8')))

    def from_yaml(self, path):
        import yaml
        self.update(yaml.load(open(path)))

    def update(self, data):
        for k, v in data.items():
            self[k.upper()] = v

    def get_default(self, item):
        key = item.upper()
        if not key.endswith('_DEFAULT'):
            key += '_DEFAULT'
        if key in self:
            return self[key]
        else:
            return None

    def update_default(self, data):
        for k, v in data.items():
            key = k.upper()
            if not key.endswith('_DEFAULT'):
                key += '_DEFAULT'
            self[key] = v


aws_config = BaseConfig(env_key='AWS_')
object_storage_config = BaseConfig(env_key='OBJECT_STORAGE_')
rabbit_config = BaseConfig(env_key='RABBIT_', HOST='localhost', PORT=5672)
apm_config = BaseConfig(env_key='ELASTIC_APM_')
redis_config = BaseConfig(env_key='REDIS_', HOST='localhost', PORT=6379, PASSWORD="", DB=0)
logstash_config = BaseConfig(env_key='LOGSTASH_', HOST='localhost', PORT=5000)
minio_config = BaseConfig(env_key='MINIO_', URL='localhost:9001', access_key='minioKey', secret_key='minioSecret')
elastic_search_config = BaseConfig(env_key='ELASTIC_SEARCH_', HOST='localhost', PORT=9200)

class MLConfig(BaseConfig):
    def __init__(self,*args,**kwargs):
        BaseConfig.__init__(self,*args,**kwargs)

    def load_config(self,path):
        if isinstance(path, str) and os.path.exists(path):
            if path.endswith('.json'):
                data = load_json(path)
            elif path.endswith('.yaml') or path.endswith('.yml'):
                data = load_yaml(path)
            else:
                raise AssertionError("Only support config file is json or yaml")
        if 'mode' in data:
            if 'default' in data['mode']:
                default = data['mode']['default']
            else:
                default = 'default'

            if 'env' in data['mode']:
                for mode in ['default', default]:
                    if mode in data['mode']['env']:
                        for k, v in data['mode']['env'][mode].items():
                            environ[k] = str(v)
                        self.update(data['mode']['env'][mode])

mlconfig = MLConfig(env_key='')

all_configs = [aws_config, object_storage_config, rabbit_config, apm_config, redis_config, logstash_config, minio_config,
           elastic_search_config]

def prepare(data,force = False):
    if 'artifact' in data:
        artifact = data['artifact']
        from mlchain.storage.object_storage import ObjectStorage
        for source in artifact:
            storage = ObjectStorage(bucket=source.get('bucket', None), url=source.get('url', None),
                                    access_key=source.get('access_key'), secret_key=source.get('secret_key', None),
                                    provider=source.get('provider', None))
            for download in source.get('mapping', []):
                d_from = download.get('from', None)
                d_to = download.get('to', None)
                if d_from and d_to:
                    if force or not os.path.exists(d_to):
                        storage.download_file(d_from, d_to, download.get('bucket', None))

def load_config(data):
    for config in all_configs:
        env_key = config.env_key.strip('_').lower()
        if env_key in data:
            config.update(data[env_key])

    if 'mode' in data:
        if 'default' in data['mode']:
            default = data['mode']['default']
        else:
            default = 'default'

        if 'env' in data['mode']:
            for mode in ['default', default]:
                if mode in data['mode']['env']:
                    for k,v in data['mode']['env'][mode].items():
                        environ[k] = str(v)
                    mlconfig.update(data['mode']['env'][mode])

def load_json(path):
    import json
    return json.load(open(path, encoding='utf-8'))


def load_yaml(path):
    import yaml
    return yaml.load(open(path))


def get_value(value=None, config=None, key=None, default=None):
    if value is not None:
        return value
    if isinstance(config,dict) and key in config:
        return config[key]
    return default


def load_from_file(path):
    if isinstance(path, str) and os.path.exists(path):
        if path.endswith('.json'):
            load_config(load_json(path))
        elif path.endswith('.yaml') or path.endswith('.yml'):
            load_config(load_yaml(path))
        else:
            raise AssertionError("Only support config file is json or yaml")

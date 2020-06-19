from cachetools import Cache
from redis import StrictRedis
import pickle
import atexit
import time
from mlchain.config import redis_config


class RedisCache(Cache):
    def __init__(self, maxsize, client=None, host=None, port=None, password=None, db=None, ttl=15 * 60,
                 clear_on_exit=False,
                 key_prefix='RedisCache'):
        Cache.__init__(self, maxsize, None)
        self.client_ = client
        self.host = host or redis_config.HOST
        self.port = port or redis_config.PORT
        self.password = password or redis_config.PASSWORD
        self.db = db or redis_config.DB

        self.ttl = ttl
        self.key_prefix = key_prefix
        if clear_on_exit:
            atexit.register(self.clear())
    @property
    def client(self):
        if self.client_ is None:
            self.client_ = StrictRedis(host=self.host, port=self.port, password=self.password, db=self.db)
        return self.client_

    def close(self):
        try:
            self.client_.close()
        except:
            pass
        self.client_ = None

    def __setitem__(self, key, value):
        try:
            self.set(f'{self.key_prefix}_{key}', value)
        except:
            pass

    def set(self, key, value):
        ttl = self.ttl
        value = pickle.dumps(value)
        self.client.set(key, value, ex=ttl)

    def __getitem__(self, key):
        try:
            if not self.client.exists(f'{self.key_prefix}_{key}'):
                raise KeyError()
            else:
                result = self.client.get(f'{self.key_prefix}_{key}')
                return pickle.loads(result)
        except Exception as e:
            raise e

    def delete_keys(self, items):
        pipeline = self.client.pipeline()
        for item in items:
            pipeline.delete(item)
        pipeline.execute()

    def __delitem__(self, key):
        try:
            self.delete_keys([key])
        except:
            pass
    def clear_all_cache(self):
        match = '{}*'.format(self.key_prefix)
        keys = []
        for key in self.client.scan_iter(match, count=100):
            keys.append(key)
            if len(keys) >= 100:
                self.delete_keys(keys)
                keys = []
                time.sleep(0.01)
        if len(keys) > 0:
            self.delete_keys(keys)

    def clear(self):
        atexit.register(self.clear_all_cache)

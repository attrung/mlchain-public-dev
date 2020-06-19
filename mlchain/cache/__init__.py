from cachetools import TTLCache, LRUCache, Cache as _Cache,LFUCache
from .function import function_cache


def cache(maxsize=1024):
    return function_cache(cache=_Cache(maxsize))


def ttlcache(maxsize=1024, ttl=15 * 60):
    return function_cache(cache=TTLCache(maxsize, ttl))


def lrucache(maxsize=1024):
    return function_cache(cache=LRUCache(maxsize))


def redis_ttlcache(maxsize=1024, ttl=15 * 60, client=None, host='localhost', port=6379, password='', db=0,
                   clear_on_exit=False,
                   key_prefix='RedisCache'):
    from .remote import RedisCache
    return function_cache(
        cache=RedisCache(maxsize, client=client, host=host, port=port, password=password, db=db, ttl=ttl,
                         clear_on_exit=clear_on_exit, key_prefix=key_prefix))


class Cache:
    def __init__(self, cache_type='local', **config):
        self.cache_type = cache_type
        self.config = config

    def ttl_cache(self, maxsize=1024*1024, ttl=15, **config):
        """LRU Cache implementation with per-item time-to-live (TTL) value."""
        if self.cache_type == 'redis':
            from .remote import RedisCache
            params = ['client', 'host', 'port', 'password', 'db', 'key_prefix']
            params = {k: self.config[k] for k in params if k in self.config}
            params.update({k: config[k] for k in params if k in config})
            return function_cache(RedisCache(maxsize=maxsize, ttl=ttl, **params))
        else:
            return function_cache(TTLCache(maxsize=maxsize, ttl=ttl))

    def lru_cache(self, maxsize=1024*1024, **config):
        """Least Recently Used (LRU) cache implementation."""
        if self.cache_type == 'redis':
            from .remote import RedisCache
            params = ['client', 'host', 'port', 'password', 'db', 'key_prefix']
            params = {k: self.config[k] for k in params if k in self.config}
            params.update({k: config[k] for k in params if k in config})
            return function_cache(RedisCache(maxsize=maxsize, ttl=None, **params))
        else:
            return function_cache(LRUCache(maxsize=maxsize))

    def cache(self,maxsize = 1024*1024,**config):
        if self.cache_type == 'redis':
            from .remote import RedisCache
            params = ['client', 'host', 'port', 'password', 'db', 'key_prefix']
            params = {k: self.config[k] for k in params if k in self.config}
            params.update({k: config[k] for k in params if k in config})
            return function_cache(RedisCache(maxsize=maxsize, ttl=None, **params))
        else:
            return function_cache(_Cache(maxsize=maxsize))
from functools import wraps
from cachetools import Cache
from threading import Event, Thread
import xxhash
from typing import *
import numpy as np
import ctypes


def hash(value):
    key = xxhash.xxh64()
    if isinstance(value, (bytes, bytearray)):
        key.update(value)
    elif isinstance(value, (int, float, str, bool, type(None))):
        key.update(str(value).encode())
    elif isinstance(value, (list, List, tuple)):
        for v in value:
            key.update(hash(v))
    elif isinstance(value, (set, Set)):
        for v in sorted(value):
            key.update(hash(v))
    elif isinstance(value, (dict, Dict)):
        hash_dict = [(hash(k), hash(v)) for k, v in value.items()]
        hash_dict = sorted(hash_dict, key=lambda x: x[0])
        for k, v in hash_dict:
            key.update(k)
            key.update(v)
    elif isinstance(value, np.ndarray):
        key.update(value.data)
    elif isinstance(value, object):
        key.update(
            (value.__module__ + '.' + value.__class__.__name__ + '.' + str(getattr(value, '__cache__', ''))).encode())
    else:
        raise ArgsUnhashable()
    return key.digest()


class ArgsUnhashable(Exception):
    pass


class function_cache:
    def __init__(self, cache: Cache = None, maxsize=1024):
        if cache is None:
            cache = Cache(maxsize=maxsize)
        self.cache = cache

    def __call__(self, func):
        def inner(*args, **kwargs):
            is_done = Event()
            key_done = Event()
            output = dict(
                has_cache=False,
                result=None,
                key=None
            )

            def func_nocache(out):
                result_ = func(*args, **kwargs)
                out['result'] = result_
                is_done.set()

            def func_cache(out):
                try:
                    key_ = self._decorator_key(func, *args, **kwargs)
                    output['key'] = key_
                except ArgsUnhashable:
                    pass
                key_done.set()
                try:
                    result_ = self[key_]
                    out['result'], out['has_cache'] = result_, True
                    is_done.set()
                except Exception as e:
                    pass

            c1 = Thread(target=func_cache, args=[output])
            c2 = Thread(target=func_nocache, args=[output])
            c1.start()
            c2.start()
            key_done.wait()
            is_done.wait()
            for th in [c1,c2]:
                if th.is_alive():
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(th.ident, ctypes.py_object(SystemExit))

            if output['has_cache']:
                return output['result']
            elif output['key'] is not None:
                self[output['key']] = output['result']
                return output['result']
            else:
                return output['result']

        return wraps(func)(inner)

    def __setitem__(self, key, value):
        self.cache[key] = value

    def __getitem__(self, key):
        return self.cache[key]

    def _decorator_key(self, func, *args, **kwargs):
        try:
            keys = [func.__name__.encode()]
            keys.extend(hash(arg) for arg in args)
            keys.append(hash(kwargs))
            key = b''.join(keys)
            return key
        except Exception:
            raise ArgsUnhashable()

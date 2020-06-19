from uuid import uuid4
from mlchain.config import logstash_config
import socket
import json
import numpy as np


class MLLogger:
    def __init__(self, name=None, host=None, port=None):
        self.host = host or logstash_config.HOST
        self.port = port or logstash_config.PORT
        self._socket = None
        self.name = name

    @property
    def socket(self):
        if self._socket is None:
            self._socket = socket.create_connection((self.host, self.port))
        return self._socket

    def send(self, data):
        try:
            self.socket.send(json.dumps(data).encode() + b'\n')
        except:
            if self._socket:
                self._socket.close()
            self._socket = None

    def get_metadata(self, obj):
        if isinstance(obj, dict):
            return {"type": "dict", "keys": list(obj.keys())}
        elif isinstance(obj, np.ndarray):
            shape = obj.shape
            shape = [int(i) for i in shape]
            size = 1
            for i in shape:
                size *= i
            return {"type": "ndarray",
                    "shape": shape,
                    "size": size}
        elif isinstance(obj, list):
            return {"type": "list",
                    "length": len(obj)}
        elif isinstance(obj, str):
            return {"type": "string",
                    "str": obj}
        elif isinstance(obj, (int, float)):
            return {"type": "numeric",
                    "value": obj}
        elif isinstance(obj, bytes):
            return {"type": "binary",
                    "size": len(obj)}
        else:
            return {
                "type": type(obj).__name__,
                "repr": repr(obj)
            }

    def log(self, metrics, service_name=None, id=None, function_name=None, **kwargs):
        service_name = service_name or self.name
        id = id or uuid4().hex
        record = {'kwargs': {str(k): self.get_metadata(v) for k, v in kwargs.items()}}
        record.update({"index": '{0}-{1}'.format(service_name, function_name).lower(),
                       "id": id,
                       "metrics": metrics})
        self.send(record)

    @staticmethod
    def log_params(service_name_=None, id_=None, function_name_=None, meta_data_=None, **kwargs):
        logger = MLLogger(service_name_)
        id = id_ or uuid4().hex
        record = {'kwargs': {str(k): logger.get_metadata(v) for k, v in kwargs.items()}}
        if meta_data_ is None:
            meta_data_ = {}
        record.update({"index": '{0}-{1}'.format(service_name_, function_name_).lower(),
                       "id": id,
                       "meta_data": meta_data_})
        logger.send(record)

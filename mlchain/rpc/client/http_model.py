import weakref
from mlchain.storage import Path
import uuid
import os
from mlchain.log import format_exc, except_handler
from mlchain.observe.apm import get_transaction
from .async_utils import AsyncStorage
from .http_client import HttpClient

class RemoteFunction:
    def __init__(self, client, url, name):
        """
        Remote Function Call
        :client: Client to communicate, which can not be None
        :url: url to call
        """
        assert client is not None

        self.client = client
        self.url = url
        self.is_async = False
        self.__name__ = name

    def to_async(self):
        return AsyncRemoteFunction(self.client, self.url, self.__name__)

    def __call__(self, *args, **kwargs):
        args = list(args)
        files_args = {}
        files = []
        # Process files in args
        for idx, item in enumerate(args):
            if isinstance(item, Path):
                new_file_name = str(uuid.uuid4())

                args[idx] = ""
                files.append((new_file_name, (os.path.split(item)[1], open(item, 'rb'), 'application/octet-stream')))
                files_args[new_file_name] = idx
            elif isinstance(item, list) and all([isinstance(x, Path) for x in item]):
                for sub_idx, sub_item in enumerate(item):
                    new_file_name = str(uuid.uuid4())
                    item[sub_idx] = ""

                    files.append(
                        (new_file_name, (os.path.split(sub_item)[1], open(sub_item, 'rb'), 'application/octet-stream')))
                    files_args[new_file_name] = (idx, sub_idx)

        # Process files in kwargs
        drop_key = []
        for key, item in kwargs.items():
            if isinstance(item, Path):
                kwargs[key] = ""
                files.append((key, (os.path.split(item)[1], open(item, 'rb'), 'application/octet-stream')))
                drop_key.append(key)
            elif isinstance(item, list) and all([isinstance(x, Path) for x in item]):
                for sub_idx, sub_item in enumerate(item):
                    item[sub_idx] = ""

                    files.append((key, (os.path.split(sub_item)[1], open(sub_item, 'rb'), 'application/octet-stream')))
                drop_key.append(key)

        for key in drop_key:
            kwargs.pop(key)

        input = {
            'input': (tuple(args), kwargs),
            'files_args': files_args
        }
        headers = {}
        transaction = get_transaction()
        if transaction:
            headers['Traceparent'] = transaction.trace_parent.to_string()
        output = self.client.post(url=self.url, input=input, files=files, headers=headers)
        return output


class AsyncRemoteFunction(RemoteFunction):
    def __init__(self, client, url, name):
        """
        Async Remote Function Call
        :client: Client to communicate, which can not be None
        :url: url to call
        """
        RemoteFunction.__init__(self, client, url, name)
        self.is_async = True

    def to_sync(self):
        return RemoteFunction(self.client, self.url, self.__name__)

    async def __call__(self, *args, **kwargs):
        return RemoteFunction.__call__(self, *args, **kwargs)


class HttpModel:
    """
    Mlchain Client Model Class
    """

    def __init__(self,api_key = None, api_address = None, serializer='json', check_status=True):
        """
        Remote model
        :client: Client to communicate, which can not be None
        :name: Name of model
        :version: Version of model
        :check_status: Check model is exist or not, and get description of model
        """

        self.client = HttpClient(api_key=api_key,api_address=api_address,serializer=serializer)

        self.pre_url = ""
        self.all_func_des = None
        self.all_func_params = None

        if check_status:
            output_description = self.client.get('{0}api/description'.format(self.pre_url))
            if 'error' in output_description:
                with except_handler():
                    raise AssertionError("ERROR: Model {0} is not found".format(api_address))
            else:
                # output_description = output_description['output']
                self.__doc__ = output_description['__main__']
                self.all_func_des = output_description['all_func_des']
                self.all_func_params = output_description['all_func_params']
                self.all_attributes = output_description['all_attributes']

        self._cache = weakref.WeakValueDictionary()
        self.store_ = None

    @property
    def store(self):
        if self.store_ is None:
            self.store_ = AsyncStorage(
                RemoteFunction(client=self.client, url='{0}call/{1}'.format(self.pre_url, 'store_get'),
                               name='store_get'))
        return self.store_

    def __check_function(self, name):
        if self.all_func_des is not None:
            if name in self.all_func_des:
                return True
            else:
                return False
        else:
            return True

    def __check_attribute(self, name):
        if self.all_attributes is not None:
            if name in self.all_attributes:
                return True
            else:
                return False
        else:
            return True

    def __getattr__(self, name):
        if name in self._cache:
            return self._cache[name]
        else:
            if not self.__check_function(name):
                if not self.__check_attribute(name) and not name.endswith('_async'):
                    with except_handler():
                        raise AssertionError("This model has no method or attribute name = {0} or it hasnt been served. The only served is: \n\
                                            Functions: {1} \n\
                                            Attributes: {2}".format(name, list(self.all_func_des.keys()),
                                                                    list(self.all_attributes)))
                else:
                    return RemoteFunction(client=self.client, url='{0}call/{1}'.format(self.pre_url, name), name=name)()
            else:
                true_function = RemoteFunction(client=self.client, url='{0}call/{1}'.format(self.pre_url, name),
                                               name=name)
                self._cache[name] = true_function
                return true_function

    def __eq__(self, other):
        return self.client is other.client

    def __hash__(self):
        return hash(self.client)


class HttpAsyncModel(HttpModel):
    """
    Mlchain Client Model Class
    """

    def __getattr__(self, name):
        if name in self._cache:
            return self._cache[name]
        else:
            if not self.__check_function(name):
                if not self.__check_attribute(name) and not name.endswith('_async'):
                    with except_handler():
                        raise AssertionError("This model has no method or attribute name = {0}".format(name))
                else:
                    return RemoteFunction(client=self.client, url='{0}call/{1}'.format(self.pre_url, name), name=name)()
            else:
                true_function = AsyncRemoteFunction(client=self.client, url='{0}call/{1}'.format(self.pre_url, name),
                                                    name=name)
                self._cache[name] = true_function

                return true_function


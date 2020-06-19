import weakref
import grpc
from mlchain.base.serializer import JsonSerializer, MsgpackSerializer, MsgpackBloscSerializer
from ..server.protos import mlchain_pb2_grpc, mlchain_pb2
from mlchain.observe.apm import get_transaction
from .async_utils import AsyncStorage


class GrpcFunction:
    def __init__(self, stub: mlchain_pb2_grpc.MLChainServiceStub, function_name, serializer='msgpack'):
        self.stub = stub
        self.function_name = function_name
        if serializer == 'msgpack':
            self.serializer = MsgpackSerializer()
            self.serializer_type = 'application/msgpack'
        elif serializer == 'msgpack_blosc':
            self.serializer = MsgpackBloscSerializer()
            self.serializer_type = 'application/msgpack_blosc'
        else:
            self.serializer = JsonSerializer()
            self.serializer_type = 'application/json'
        self.header = mlchain_pb2.Header(serializer=self.serializer_type)

    def __call__(self, *args, **kwargs):
        transaction = get_transaction()
        if transaction:
            Traceparent = transaction.trace_parent.to_string()
            header = mlchain_pb2.Header(serializer=self.serializer_type, Traceparent=Traceparent)
        else:
            header = self.header
        output = self.stub.call(mlchain_pb2.Message(header=header, function_name=self.function_name,
                                                    args=self.serializer.encode(args),
                                                    kwargs=self.serializer.encode(kwargs)))
        return self.serializer.decode(output.output)


class GrpcAsyncFunction(GrpcFunction):
    async def __call__(self, *args, **kwargs):
        return GrpcFunction.__call__(self, *args, **kwargs)


class GrpcModel:
    def __init__(self, api_address, serializer='msgpack', check_status=False):
        """
        Remote model
        :client: Client to communicate, which can not be None
        :name: Name of model
        :version: Version of model
        :check_status: Check model is exist or not, and get description of model
        """

        self.serializer = serializer
        self.channel = grpc.insecure_channel(api_address)
        self.stub = mlchain_pb2_grpc.MLChainServiceStub(self.channel)

        self.all_func_des = None
        self.all_func_params = None
        self.all_attributes = None

        self._cache = weakref.WeakValueDictionary()
        self.store_ = None

    @property
    def store(self):
        if self.store_ is None:
            self.store_ = AsyncStorage(GrpcFunction(self.stub, 'store_get', self.serializer))
        return self.store_

    def _check_function(self, name):
        if self.all_func_des is not None:
            if name in self.all_func_des:
                return True
            else:
                return False
        else:
            return True

    def _check_attribute(self, name):
        if self.all_attributes is not None:
            if name in self.all_attributes:
                return True
            else:
                return False
        else:
            return True

    def __getattr__(self, name):
        if name in self._cache:
            true_function = self._cache[name]
        else:
            if not self._check_function(name):
                if not self._check_attribute(name) and not name.endswith('_async'):
                    raise AssertionError("This model has no method or attribute name = {0} or it hasnt been served. The only served is: \n\
                                          Functions: {1} \n\
                                          Attributes: {2}".format(name, list(self.all_func_des.keys()),
                                                                  list(self.all_attributes)))
                else:
                    return GrpcFunction(self.stub, name, self.serializer)
            else:
                true_function = GrpcFunction(self.stub, name, self.serializer)
            self._cache[name] = true_function

        return true_function

    def __eq__(self, other):
        return self.client is other.client and self.name == other.name and self.version == other.version

    def __hash__(self):
        return hash(self.client) + hash(self.name) + hash(self.version)


class GrpcAsyncModel(GrpcModel):
    def __getattr__(self, name):
        if name in self._cache:
            true_function = self._cache[name]
        else:
            if not self._check_function(name):
                if not self._check_attribute(name) and not name.endswith('_async'):
                    raise AssertionError("This model has no method or attribute name = {0} or it hasnt been served. The only served is: \n\
                                          Functions: {1} \n\
                                          Attributes: {2}".format(name, list(self.all_func_des.keys()),
                                                                  list(self.all_attributes)))
                else:
                    return GrpcAsyncFunction(self.stub, name, self.serializer)
            else:
                true_function = GrpcAsyncFunction(self.stub, name, self.serializer)
            self._cache[name] = true_function

        return true_function

    def __eq__(self, other):
        return self.client is other.client and self.name == other.name and self.version == other.version

    def __hash__(self):
        return hash(self.client) + hash(self.name) + hash(self.version)

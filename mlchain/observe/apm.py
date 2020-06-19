import warnings

try:
    from elasticapm import Client as APMClient
    from elasticapm.context.contextvars import execution_context
    from elasticapm.utils.disttracing import TraceParent
    from mlchain.config import apm_config


    class Client:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.client_ = APMClient(*args, **kwargs)
            try:
                self.client_.capture_message('ping')
                self.client_._transport.flush()
            except:
                self.client_.close()
                raise ConnectionError("Can't connect to APM-Server")

        @property
        def client(self):
            if self.client_ is None:
                self.client_ = APMClient(*self.args, **self.kwargs)
            return self.client_

        def close(self):
            try:
                self.client_.close()
            except:
                pass
            self.client_ = None

        def end_transaction(self, name=None, result="", duration=None):
            try:
                return self.client.end_transaction(name=name, result=result, duration=duration)
            except:
                self.close()
                return None

        def begin_transaction(self, transaction_type, trace_parent=None, start=None):
            try:
                return self.client.begin_transaction(transaction_type, trace_parent=trace_parent, start=start)
            except:
                self.close()
                return None

        def capture_exception(self, exc_info=None, handled=True, **kwargs):
            try:
                return self.client.capture_exception(exc_info=exc_info, handled=handled, **kwargs)
            except:
                self.close()
                return None

        def __getattr__(self, item):
            attr = getattr(self.client, item)
            return attr


    def get_transaction(clear=False):
        try:
            return execution_context.get_transaction(clear=clear)
        except:
            return None
except:

    warnings.warn("Can't import elasticapm. Set trace is False")
    elasticapm = None
    Client = None


    def get_transaction(clear=False):
        return None


    TraceParent = None

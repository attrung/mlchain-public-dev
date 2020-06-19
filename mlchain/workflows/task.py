import inspect
from mlchain.observe import apm
import trio


class Task:
    """
    This class wrap a function to a Task 
    :func_: Function 
    """

    def __init__(self, func_, *args, **kwargs):
        assert callable(func_), 'You have to transfer a callable instance and its params'
        self.func_ = func_
        self.args = args
        self.kwargs = kwargs
        self.transaction = apm.get_transaction()
        self.span = None

    def exec(self):
        if inspect.iscoroutinefunction(self.func_) or (
                not inspect.isfunction(self.func_) and hasattr(self.func_, '__call__') and inspect.iscoroutinefunction(
            self.func_.__call__)):
            return trio.run(self.__call__)
        else:
            with self:
                return self.func_(*self.args, **self.kwargs)

    async def exec_async(self):
        return self.__call__()

    async def __call__(self):
        """
        Task's process code
        """
        if inspect.iscoroutinefunction(self.func_) or (
                not inspect.isfunction(self.func_) and hasattr(self.func_, '__call__') and inspect.iscoroutinefunction(
            self.func_.__call__)):
            async with self:
                return await self.func_(*self.args, **self.kwargs)
        else:
            with self:
                return self.func_(*self.args, **self.kwargs)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    def __enter__(self):
        transaction = self.transaction
        if transaction and transaction.is_sampled:

            self.span = transaction.begin_span(
                getattr(self.func_, '__name__', 'task'),
                'task',
            )
            from elasticapm.context.contextvars import execution_context
            execution_context.set_transaction(transaction)
            return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        transaction = self.transaction
        if transaction and transaction.is_sampled:
            if self.span:
                self.span.end()

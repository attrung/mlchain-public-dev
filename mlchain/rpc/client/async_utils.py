import time

class AsyncResult:
    def __init__(self, response):
        self.response = response

    @property
    def output(self):
        if 'output' in self.response:
            return self.response['output']
        else:
            return None

    @property
    def status(self):
        if 'status' in self.response:
            return self.response['status']
        else:
            return None

    @property
    def time(self):
        if 'time' in self.response:
            return self.response['time']
        else:
            return 0

    def is_success(self):
        if self.status == 'SUCCESS':
            return True
        else:
            return False

    def json(self):
        return self.response

class AsyncStorage:
    def __init__(self, function):
        self.function = function

    def get(self, key):
        return AsyncResult(self.function(key))

    def get_wait_until_done(self, key, timeout=100, interval=0.5):
        start = time.time()
        result = AsyncResult(self.function(key))
        while not (result.is_success() or time.time() - start > timeout):
            time.sleep(interval)
            result = AsyncResult(self.function(key))
        return result





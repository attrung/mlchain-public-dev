import time
import pandas as pd
import os
from threading import Thread

class Observer:
    def __init__(self):
        self.data = {}

    def add(self, key, record):
        if key not in self.data:
            self.data[key] = pd.DataFrame()
        self.data[key] = self.data[key].append(
            record, ignore_index=True)

    def summary(self):
        return {key: df.describe().to_dict() for key, df in self.data.items()}

    def monitor(self, key, memory=False, cpu=False, interval=0.5):
        if memory or cpu:
            try:
                import psutil
            except ModuleNotFoundError:
                import warnings
                warnings.warn('Cant import psutil. Please install psutil to monitor cpu and memory')
                memory = False
                cpu = False

        class Mem(Thread):
            def __init__(sel, process):
                Thread.__init__(sel)
                sel.process = process
                sel.mem_begin = sel.process.memory_info().vms
                sel.usage = 0
                sel.running = True

            def run(sel):
                while sel.running:
                    sel.usage = max(sel.usage, sel.process.memory_info().vms - sel.mem_begin)
                    time.sleep(interval)
                sel.usage = max(sel.usage, sel.process.memory_info().vms - sel.mem_begin)

            def stop(sel):
                sel.running = False

        def func(user_function):
            def wrapper(*args, **kwds):
                if memory or cpu:
                    process = psutil.Process(os.getpid())
                    if cpu:
                        process.cpu_percent()
                    if memory:
                        mem = Mem(process)
                        mem.start()
                start = time.time()
                result = user_function(*args, **kwds)
                end = time.time()
                info = {'time': end - start}
                if memory or cpu:
                    if cpu:
                        info['cpu'] = process.cpu_percent()
                    if memory:
                        mem.stop()
                        info['memory'] = mem.usage
                self.add(key, info)
                return result

            return wrapper

        return func


observer = Observer()

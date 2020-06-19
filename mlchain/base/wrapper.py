try:
    from gunicorn.app.base import BaseApplication
except Exception as e:
    import warnings
    warnings.warn("Import error {0}".format(e))
    class BaseApplication(object):
        def __init__(self):
            raise ImportError("Can't import gunicorn. Please set gunicorn = False")

class GunicornWrapper(BaseApplication):
    def __init__(self, app, **kwargs):
        self.application = app
        self.options = kwargs
        super(GunicornWrapper, self).__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application
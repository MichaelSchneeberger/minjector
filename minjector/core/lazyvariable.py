class LazyVariable:
    def __init__(self, func):
        self._func = func
        self._obj = None

    def __getattr__(self, item):
        if not self._obj:
            self._obj = self._func()

        return getattr(self._obj, item)
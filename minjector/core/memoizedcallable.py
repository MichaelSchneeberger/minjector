class MemoizedCallable:
    def __init__(self, callable):
        self._callable = callable
        self._return_val = None

    def __call__(self, *args, **kwargs):
        if self._return_val is None:
            self._return_val = self._callable()

        return self._return_val
from typing import Generic, Callable

from minjector.readermonad.types import EnvType, ValType


class Reader(Generic[EnvType, ValType]):
    def __init__(self, func: Callable[[EnvType], ValType]):
        self._func = func

    def __call__(self, env: EnvType) -> ValType:
        return self._func(env)
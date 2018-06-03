from typing import Callable, Any

from minjector.readermonad.reader import Reader
from minjector.readermonad.types import EnvType, ValType


class ReaderMonadOp:
    @staticmethod
    def unit(v) -> Reader[EnvType, ValType]:
        def _(env: EnvType) -> ValType:
            return v

        return Reader(_)

    @staticmethod
    def ask(mf: Callable[[EnvType], Callable[[EnvType], ValType]]) -> Reader[EnvType, ValType]:
        def _(env: EnvType) -> ValType:
            return mf(env)(env)

        return Reader(_)

    @staticmethod
    def asks(mv: Callable[[EnvType], Any], mf: Callable[[Any], Callable[[EnvType], ValType]]) -> Reader[
        EnvType, ValType]:
        def _(env: EnvType) -> ValType:
            val = mv(env)
            return mf(val)(env)

        return Reader(_)

    @staticmethod
    def local(ef: Callable[[EnvType], EnvType]):
        def __(reader: Reader[EnvType, ValType]) -> Reader[EnvType, ValType]:
            def _(env: EnvType) -> ValType:
                new_env = ef(env)
                return reader(new_env)

            return Reader(_)

        return __

    @staticmethod
    def concat(f1, f2):
        def _(env):
            new_env = f1(env)
            return f2(new_env)

        return Reader(_)
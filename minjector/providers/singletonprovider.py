from minjector.core.memoizedcallable import MemoizedCallable
from minjector.providers.providerbase import ProviderBase
from minjector.readermonad.readermonadop import ReaderMonadOp
from minjector.core.variableenvironment import VariableEnvironment


class SingletonProvider(ProviderBase):
    def __init__(self, local_func):
        self._local_func = local_func
        self._obj = None

    def get(self, key):
        def brackets(env: VariableEnvironment):
            if self._obj is None:
                func = self._local_func.get(key)(ReaderMonadOp.ask(lambda env: ReaderMonadOp.unit(env[key])))(
                    env)
                self._obj = MemoizedCallable(func)

            new_env = env.add_callable(key, self._obj)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider
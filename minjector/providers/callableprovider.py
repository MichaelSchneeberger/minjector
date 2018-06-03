from minjector.core.memoizedcallable import MemoizedCallable
from minjector.providers.providerbase import ProviderBase
from minjector.readermonad.readermonadop import ReaderMonadOp
from minjector.core.variableenvironment import VariableEnvironment


class CallableProvider(ProviderBase):
    def __init__(self, get_func):
        self._get_func = get_func

    def get(self, key):
        def brackets(env: VariableEnvironment):
            memoized_callable = MemoizedCallable(callable=self._get_func)
            new_env = env.add_callable(key, memoized_callable)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider
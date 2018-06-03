from minjector.providers.providerbase import ProviderBase
from minjector.readermonad.readermonadop import ReaderMonadOp
from minjector.core.variableenvironment import VariableEnvironment


class ObjectProvider(ProviderBase):
    def __init__(self, obj):
        self._obj = obj

    def get(self, key):
        def brackets(env: VariableEnvironment):
            new_env = env.add_callable(key, lambda: self._obj)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider
from minjector.providers.providerbase import ProviderBase
from minjector.readermonad.readermonadop import ReaderMonadOp
from minjector.core.variableenvironment import VariableEnvironment


class NonLazyProvider(ProviderBase):
    def __init__(self, local_func):
        self._local_func = local_func
        self._obj = None

    def get(self, key):
        def brackets(env: VariableEnvironment):
            self._obj = self._local_func.get(key)(ReaderMonadOp.ask(lambda env: ReaderMonadOp.unit(env[key])))(
                env)()

            new_env = env.add_callable(key, lambda: self._obj)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider
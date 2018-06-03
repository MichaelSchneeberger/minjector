from minjector.providers.providerbase import ProviderBase
from minjector.readermonad.reader import Reader
from minjector.readermonad.readermonadop import ReaderMonadOp
from minjector.core.variableenvironment import VariableEnvironment


class ClassProvider(ProviderBase):
    def __init__(self, cls):
        self._cls = cls

    def get(self, key):
        def brackets(env: VariableEnvironment):
            # def func():
            cls = self._cls
            instance = cls.__new__(cls)
            init = cls.__init__
            func = init(instance)

            if isinstance(func, Reader):
                new_env = func((key, env))
            else:
                new_env = env.add_object(key, instance)

            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider
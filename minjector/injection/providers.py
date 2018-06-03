import functools
import inspect

from minjector.providers.providerbase import ProviderBase
from minjector.providers.singletonprovider import SingletonProvider
from minjector.readermonad.readermonadop import ReaderMonadOp


def provides(key, singleton=False):
    def wrapper(func):
        argspec = inspect.getfullargspec(func)

        if argspec.args and argspec.args[0] == 'self_':
            @functools.wraps(func)
            def inject(self_, *args, **kwargs):
                reader = func(self_, *args, **kwargs)
                # func might not return a reader
                provider = ReaderMonadOp.local(lambda env: reader((key, env)))

                class DummyProvider(ProviderBase):
                    def get(self, key):
                        return provider

                if singleton:
                    singleton_provider = SingletonProvider(DummyProvider()).get(key)
                else:
                    singleton_provider = provider

                return ReaderMonadOp.local(lambda providers: {**providers, **{key: singleton_provider}})(
                    ReaderMonadOp.ask(lambda providers: ReaderMonadOp.unit(providers)))
        else:
            raise Exception('annotation "provides" can only be used inside a class')

        return inject
    return wrapper
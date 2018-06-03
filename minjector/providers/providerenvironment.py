from minjector.core.variableenvironment import VariableEnvironment
from minjector.providers.callableprovider import CallableProvider
from minjector.providers.classprovider import ClassProvider
from minjector.providers.nonlazyprovider import NonLazyProvider
from minjector.providers.objectprovider import ObjectProvider
from minjector.providers.singletonprovider import SingletonProvider


class ProviderEnvironment:
    def __init__(self, providers=None):
        self.providers = providers or {}

    def add_provider(self, key, to):
        provider = to
        return self._add(key, provider)

    def add_callable(self, key, to):
        provider = CallableProvider(to)
        return self._add(key, provider)

    def add_class(self, key, to):
        provider = ClassProvider(to)
        return self._add(key, provider)

    def add_object(self, key, to):
        provider = ObjectProvider(to)
        return self._add(key, provider)

    def _add(self, key, provider, singleton=False, lazy=False) -> 'ProviderEnvironment':
        if singleton:
            singleton_provider = SingletonProvider(provider)
        else:
            singleton_provider = provider

        if lazy:
            lazy_provider = singleton_provider
        else:
            lazy_provider = NonLazyProvider(singleton_provider)

        device_provider = lazy_provider.get(key)

        new_providers = {**self.providers, **{key: device_provider}}
        provider_env = ProviderEnvironment(new_providers)

        return provider_env

    def add_module(self, module):
        providers = module.configure()(self.providers)
        provider_env = ProviderEnvironment(providers)

        return provider_env

    def provide(self):
        return VariableEnvironment(providers=self.providers)

    def __getitem__(self, key):
        return self.providers[key]
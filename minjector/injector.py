import inspect
import functools
import types

from typing import TypeVar, Generic, Callable, Any, Dict

T = TypeVar('T')
V = TypeVar('V')


class ReaderMonad:
    def __init__(self, func):
        self._func = func

    def __call__(self, env):
        return self._func(env)


class ReaderMonadOp(Generic[T, V]):
    @staticmethod
    def unit(v) -> Callable[[T], V]:
        def _(env: T):
            return v

        return ReaderMonad(_)

    @staticmethod
    def ask(mf: Callable[[Any], Callable[[T], 'ReaderMonad']]) -> Callable[[T], 'ReaderMonad']:
        def _(env: T) -> 'ReaderMonad':
            return mf(env)(env)

        return ReaderMonad(_)

    @staticmethod
    def asks(mv: Callable[[T], Any], mf: Callable[[Any], ReaderMonad]) -> ReaderMonad:
        def _(env: T) -> 'ReaderMonadOp':
            val = mv(env)
            return mf(val)(env)

        return ReaderMonad(_)

    @staticmethod
    def local(ef: Callable[[T], T]):
        def __(reader: ReaderMonad) -> ReaderMonad:
            def _(env: T) -> Any:
                new_env = ef(env)
                return reader(new_env)

            return ReaderMonad(_)

        return __

    @staticmethod
    def concat(f1, f2):
        def _(env):
            new_env = f1(env)
            return f2(new_env)

        return ReaderMonad(_)


class VariableEnvironment:
    def __init__(self, variables: dict, providers: dict):
        self._variables = variables or {}
        self.providers = providers

    def add(self, key, to):
        if key not in self._variables:
            variables = {**self._variables, **{key: to}}
            return VariableEnvironment(variables=variables, providers=self.providers)
        else:
            return self

    def provide(self, key):
        if key in self:
            new_var_env = self
        else:
            provider = self.providers[key]
            new_var_env = provider(ReaderMonadOp.ask(lambda var_env: ReaderMonadOp.unit(var_env)))(self)
        return new_var_env

    def __contains__(self, item):
        return item in self._variables

    def __getitem__(self, key):
        return self._variables[key]


class Provider:
    def get(self, key):
        raise NotImplementedError


class MemoizedCallable:
    def __init__(self, callable):
        self._callable = callable
        self._return_val = None

    def __call__(self, *args, **kwargs):
        if self._return_val is None:
            self._return_val = self._callable()

        return self._return_val


class CallableProvider(Provider):
    def __init__(self, get_func):
        self._get_func = get_func

    def get(self, key):
        def brackets(env: VariableEnvironment):
            memoized_callable = MemoizedCallable(callable=self._get_func)
            new_env = env.add(key, memoized_callable)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider


class ObjectProvider(Provider):
    def __init__(self, obj):
        self._obj = obj

    def get(self, key):
        def brackets(env: VariableEnvironment):
            new_env = env.add(key, lambda: self._obj)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider


class SingletonProvider(Provider):
    def __init__(self, local_func):
        self._local_func = local_func
        self._obj = None

    def get(self, key):
        def brackets(env: VariableEnvironment):
            if self._obj is None:
                func = self._local_func.get(key)(ReaderMonadOp.ask(lambda env: ReaderMonadOp.unit(env[key])))(
                    env)
                self._obj = MemoizedCallable(func)

            new_env = env.add(key, self._obj)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider


class NonLazyProvider(Provider):
    def __init__(self, local_func):
        self._local_func = local_func
        self._obj = None

    def get(self, key):
        def brackets(env: VariableEnvironment):
            self._obj = self._local_func.get(key)(ReaderMonadOp.ask(lambda env: ReaderMonadOp.unit(env[key])))(
                env)()

            new_env = env.add(key, lambda: self._obj)
            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider


class ClassProvider(Provider):
    def __init__(self, cls):
        self._cls = cls

    def get(self, key):
        def brackets(env: VariableEnvironment):
            # def func():
            cls = self._cls
            instance = cls.__new__(cls)
            init = cls.__init__
            func = init(instance)

            if isinstance(func, ReaderMonad):
                new_env = func((key, env))
            else:
                new_env = env.add(key, lambda: instance)

            return new_env

        var_provider = ReaderMonadOp.local(brackets)
        return var_provider


class Module:
    def configure(self, *args, **kwargs):
        raise NotImplementedError


class ProviderEnvironment:
    def __init__(self, providers=None):
        self.providers = providers or {}

    def add(self, key, to, singleton=False, lazy=False) -> 'ProviderEnvironment':
        if isinstance(to, Provider):
            provider = to
        elif isinstance(to, (types.FunctionType, types.LambdaType,
                             types.MethodType, types.BuiltinFunctionType,
                             types.BuiltinMethodType)):
            provider = CallableProvider(to)

        elif issubclass(type(to), type):
            provider = ClassProvider(to)

        else:
            provider = ObjectProvider(to)

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
        print(providers)
        provider_env = ProviderEnvironment(providers)

        return provider_env

    def __getitem__(self, key):
        return self.providers[key]


class LazyVariable:
    def __init__(self, func):
        self._func = func
        self._obj = None

    def __getattr__(self, item):
        if not self._obj:
            self._obj = self._func()

        return getattr(self._obj, item)


def provides(key):
    def wrapper(func):
        argspec = inspect.getfullargspec(func)

        if argspec.args and argspec.args[0] == 'self_':
            @functools.wraps(func)
            def inject(self_, *args, **kwargs):
                reader = func(self_, *args, **kwargs)
                provider = ReaderMonadOp.local(lambda env: reader((key, env)))
                return ReaderMonadOp.local(lambda providers: {**providers, **{key: provider}})(ReaderMonadOp.ask(lambda providers: ReaderMonadOp.unit(providers)))
        else:
            raise Exception('annotation "provides" can only be used inside a class')

        return inject
    return wrapper


def inject_base(bindings, lazy=False, func=False):
    def multi_wrapper(func):
        argspec = inspect.getfullargspec(func)

        if argspec.args and argspec.args[0] == 'self':
            @functools.wraps(func)
            def inject(self_, *args, **kwargs):

                def brackets(env):
                    def init_obj():
                        dependencies = dict(env[1])
                        dependencies.update(kwargs)
                        if func.__name__ == '__init__':
                            func(self=self_, *args, **dependencies)
                            return self_
                        else:
                            return func(self=self_, *args, **dependencies)
                    new_env = env[0][1].add(env[0][0], init_obj)
                    return ReaderMonadOp.unit(new_env)

                reader = ReaderMonadOp.ask(brackets)

                for key, arg in bindings.items():
                    def modify_env(env, key=key, arg=arg):
                        dependencies = dict(env[1])
                        new_env = env[0][1].provide(arg)

                        def selector(env):
                            var = env[arg]()
                            return var

                        if func:
                            dependencies[key] = lambda: selector(new_env)
                        elif lazy:
                            dependencies[key] = LazyVariable(lambda: selector(new_env))
                        else:
                            dependencies[key] = selector(new_env)
                        return ((env[0][0], new_env), dependencies)

                    reader = ReaderMonadOp.local(modify_env)(reader)

                return ReaderMonadOp.local(lambda env: (env, {}))(reader)

        else:
            raise Exception('inject is only allowed for binded functions')

        return inject

    return multi_wrapper


def inject(**bindings):
    return inject_base(bindings)


def inject_lazy(**bindings):
    return inject_base(bindings, lazy=True)


def inject_func(**bindings):
    return inject_base(bindings, func=True)

import inspect
import functools
import types

from typing import TypeVar, Generic, Callable, Any


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
    def local(ef: Callable[[T], T], reader: ReaderMonad) -> ReaderMonad:
        def _(env: T) -> Any:
            new_env = ef(env)
            return reader(new_env)

        return ReaderMonad(_)

    @staticmethod
    def concat(f1, f2):
        def _(env):
            new_env = f1(env)
            return f2(new_env)

        return ReaderMonad(_)


class Provider:
    def get(self):
        raise NotImplementedError


class SingletonProvider(Provider):
    def __init__(self, get_func):
        self._get_func = get_func
        self._obj = None

    def get(self):
        if self._obj is None:
            self._obj = self._get_func()

        return self._obj


class CallableProvider(Provider):
    def __init__(self, get_func):
        self._get_func = get_func

    def get(self):
        return self._get_func()


class ObjectProvider(Provider):
    def __init__(self, obj):
        self._obj = obj

    def get(self):
        return self._obj


class SingletonScope:
    pass


class InjectionEnvironment:
    def __init__(self, providers=None, variables=None):
        self._providers = providers or {}
        self._variables = variables or {}

    def add(self, key, to, scope=None, lazy=False) -> 'InjectionEnvironment':
        if key not in self._providers:
            if isinstance(to, Provider):
                provider = to
            elif isinstance(to, (types.FunctionType, types.LambdaType,
                                 types.MethodType, types.BuiltinFunctionType,
                                 types.BuiltinMethodType)):
                provider = CallableProvider(to)
            elif issubclass(type(to), type):
                def init_instance():
                    instance = to.__new__(to)
                    init = to.__init__
                    func = init(instance)

                    if isinstance(func, ReaderMonad):
                        func(self)

                    return instance

                provider = CallableProvider(init_instance)
            else:
                provider = ObjectProvider(to)

            if isinstance(scope, SingletonScope):
                scoped_provider = SingletonProvider(lambda: provider.get())
            else:
                scoped_provider = provider

            providers = {**self._providers, **{key: scoped_provider}}
        else:
            providers = self._providers

        variables = dict(self._variables)
        if lazy:
            variables.pop(key, None)
        else:
            # get the value immediately
            variables[key] = providers[key].get()

        return InjectionEnvironment(providers, variables)

    def __getitem__(self, key):
        if key not in self._variables:
            var_provider = self._providers[key].get()
            self._variables[key] = var_provider

        obj = self._variables[key]
        return obj


class LazyVariable:
    def __init__(self, func):
        self._func = func
        self._obj = None

    def __getattr__(self, item):
        if not self._obj:
            self._obj = self._func()

        return getattr(self._obj, item)


def inject_base(bindings, lazy=False, func=False):
    def multi_wrapper(init_func):
        argspec = inspect.getfullargspec(init_func)

        if argspec.args and argspec.args[0] == 'self':
            @functools.wraps(init_func)
            def inject(self_, *args, **kwargs):

                def brackets(env):
                    dependencies = dict(env[1])
                    dependencies.update(kwargs)
                    ReaderMonadOp.unit(init_func(self=self_, *args, **dependencies))

                reader = ReaderMonadOp.asks(lambda e: e, lambda e: brackets)

                for key, arg in bindings.items():
                    def modify_env(env, key=key, arg=arg):
                        dependencies = dict(env[1])
                        if func:
                            dependencies[key] = lambda: arg(env[0])
                        elif lazy:
                            dependencies[key] = LazyVariable(lambda: arg(env[0]))
                        else:
                            dependencies[key] = arg(env[0])
                        return (env[0], dependencies)

                    reader = ReaderMonadOp.local(modify_env, reader)

                return ReaderMonadOp.local(lambda env: (env, {}), reader)

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

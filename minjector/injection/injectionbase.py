import functools
import inspect

from minjector.core.lazyvariable import LazyVariable
from minjector.readermonad.readermonadop import ReaderMonadOp


def inject_base(bindings, lazy=False, return_func=False):
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
                    new_env = env[0][1].add_callable(env[0][0], init_obj)
                    return ReaderMonadOp.unit(new_env)

                reader = ReaderMonadOp.ask(brackets)

                for key, arg in bindings.items():
                    def modify_env(env, key=key, arg=arg):
                        dependencies = dict(env[1])
                        new_env = env[0][1].provide(arg)

                        def selector(env):
                            var = env[arg]()
                            return var

                        if return_func:
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
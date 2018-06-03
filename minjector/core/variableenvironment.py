from minjector.readermonad.readermonadop import ReaderMonadOp


class VariableEnvironment:
    def __init__(self, providers: dict, variables: dict = None):
        self._variables = variables or {}
        self.providers = providers

    def add_callable(self, key, to):
        callable = to
        return self._add(key, callable)

    def add_object(self, key, to):
        callable = lambda: to
        return self._add(key, callable)

    def _add(self, key, callable):
        variables = {**self._variables, **{key: callable}}
        return VariableEnvironment(variables=variables, providers=self.providers)

    def provide(self, key):
        if key in self:
            new_var_env = self
        else:
            if key not in self.providers:
                raise Exception('No provider found for key "{}"'.format(key))

            provider = self.providers[key]
            new_var_env = provider(ReaderMonadOp.ask(lambda var_env: ReaderMonadOp.unit(var_env)))(self)
        return new_var_env

    def get_once(self, key):
        provided_env = self.provide(key)
        return provided_env[key]()

    def __contains__(self, item):
        return item in self._variables

    def __getitem__(self, key):
        return self._variables[key]
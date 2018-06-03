from minjector.injection.injectionbase import inject_base


def inject_lazy(**bindings):
    return inject_base(bindings, lazy=True)
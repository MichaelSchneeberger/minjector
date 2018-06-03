from minjector.injection.injectionbase import inject_base


def inject_func(**bindings):
    return inject_base(bindings, return_func=True)
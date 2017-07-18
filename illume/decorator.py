"""Decorators."""


from functools import wraps


def invalidatable():
    """
    Return a tuple pair of functions that represent an invalidatable namespace.

    The decorator's return value acts as a lazily-evaluated property that is
    recomputed when invalidated by calling the invalidator function.

    (invalidator, decorator)

    decorator:
        pass

    invalidator:
        pass
    """
    x = {1: 1, 0: 0}

    def decorator(fn):
        @property
        @wraps(fn)
        def checker(self):
            if x[1] == 0:
                return x[0]

            x[0] = fn(self)
            x.update({1: 0})
            return x[0]

        return checker

    return decorator, lambda self: x.update({1: 1, 0: 0})

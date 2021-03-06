import inspect
from trtools.tools.attrdict import attrdict

def locals_ns(skip=[]):
    """
    Useful for returning all the locals() in a function as an attrdict

    Parameters
    ----------
    skip : iterable
        list of keys to skip including in return dict

    Usage:
        def test():
            test = '123'
            test_int = 222
            return locals_ns()
        ret = test()
        assert ret.test == '123'
    """
    caller_globals = inspect.stack()[1][0].f_locals
    # remove skip items
    for k in skip:
        caller_globals.pop(k, None)
    return attrdict(caller_globals)

import pandas as pd
import numpy as np

def parallel_apply(func_name, *args):
    """
    """
    d = dict()
    for i, series in enumerate(args):
        name = series.name or 'arg_' + i
        d[name] = series
    df = pd.DataFrame(d, index=args[0].index)
    func = getattr(df, func_name)
    return func(axis=1)

def pmax(*args, **kwargs):
    return parallel_apply('max', *args)

def pmin(*args, **kwargs):
    return parallel_apply('min', *args)

def generic_wrap(data):
    """
        This is to handle cases like aggregate where the return 
        can be anything from a scalar to a panel. 

        This is useful when using DataFrames and ColumnPanels. 
        ColumnPanels are meant to be interchangable with DataFrames.
        Aggregating results is a common thing, this is to make that easier.
    """
    if isinstance(data, (pd.Panel, pd.DataFrame, pd.Series)):
        return data

    if np.isscalar(data):
       return data

    if isinstance(data, dict):
       return _generic_wrap_dict(data)

def _generic_wrap_dict(data):
    if len(data) == 0:
        return None

    test = next(iter(data.values()))

    if np.isscalar(test):
        return pd.Series(data)

    if isinstance(test, pd.Series):
        return pd.DataFrame(data)

    if isinstance(test, pd.DataFrame):
        return pd.Panel.from_dict(data)

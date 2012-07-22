import operator

import pandas as pd

def combine_filters(filters):
    return reduce(lambda a,b: a & b, filters)

class PandasSQL(object):
    def __init__(self, df):
        self.df = df

    def query(self, *args):
        cols = args or None
        return Query(self, cols)

    def execute_query_all(self, query):
        cols = query.cols
        filters = query.filters
        order_by = query.order_by
        return self.execute(cols, filters, order_by)

    def execute(self, cols=None, filters=None, order_by=None):
        ret = self.df
        if cols is not None and len(cols) > 0:
            ret = ret.xs(cols, axis=1)
        if filters is not None:
            combined_filter = combine_filters(filters)
            ret = ret[combined_filter]
        return ret

    def __getattr__(self, attr):
        if attr in self.df.columns:
            return PandasColumn(self, attr)

class PandasColumn(object):
    """
        Designed for quick column queries

        db.col == val
        db.col.startswith(str)
    """
    def __init__(self, db, column):
        self.db = db
        self.column = column

    def column_filter(self, other, op):
        filter = op(self.db.df[self.column],other)
        return self.db.execute(filters=[filter])

    def __eq__(self, other):
        return self.column_filter(other, operator.eq)

    def __ne__(self, other):
        return self.column_filter(other, operator.ne)

    def __gt__(self, other):
        return self.column_filter(other, operator.gt)

    def __ge__(self, other):
        return self.column_filter(other, operator.ge)

    def __lt__(self, other):
        return self.column_filter(other, operator.lt)

    def __le__(self, other):
        return self.column_filter(other, operator.le)

    def __imod__(self, other):
        #TODO replace with a like or re matching func
        return self.startswith(other)

    def startswith(self, other):
        func = lambda x: x.startswith(other)
        return self.column_filter(func, pd.Series.apply)


class Query(object):
    """
        Query object modeled after sqlalchemy.

        db.query().filter_by(bool_array).all()
    """
    def __init__(self, db, cols, filters=None):
        self.db = db
        self.cols = cols
        if filters is None:
            filters = []
        self.filters = filters
        self.order_by = None 

    def filter_by(self, filter):
        filters = self.filters[:]
        filters.append(filter)
        return Query(self.db, self.cols, filters)

    def all(self):
        return self.db.execute_query_all(self)

# monkey patch
pd.DataFrame.sql = property(lambda x: PandasSQL(x))

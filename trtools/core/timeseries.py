from datetime import datetime, time
from functools import partial
from dateutil import relativedelta
import calendar

from pandas import DateOffset, datetools, DataFrame, Series, Panel
from pandas.tseries.index import DatetimeIndex
from pandas.tseries.resample import _get_range_edges
from pandas.core.groupby import BinGrouper
import pandas.lib as lib
import numpy as np

def first_day(year, month, bday=True):
    """ 
        Return first day of month. Default to business days
    """
    weekday, days_in_month = calendar.monthrange(year, month)

    if not bday: 
        return 1

    if weekday <= 4:
        return 1
    else:
        return 7-weekday+1

class MonthStart(DateOffset):
    """ 
        Really the point of this is for DateRange, creating
        a range where the month is anchored on day=1 and not the end
    """
    def apply(self, other):
        first = first_day(other.year, other.month)
        if other.day == first:
            result =  other + relativedelta.relativedelta(months=1)
            result = result.replace(day=first_day(result.year, result.month))
        else:
            result = other.replace(day=first)

        return datetime(result.year, result.month, result.day) 

    def onOffset(self, someDate):
        return someDate.day == first_day(someDate.year, someDate.month) 

def daily_group(df):
    daterange_func = partial(DatetimeIndex, freq=datetools.day)
    return down_sample(df, daterange_func)

def weekly_group(df):
    daterange_func = partial(DatetimeIndex, freq="W@MON")
    return down_sample(df, daterange_func)

def monthly_group(df):
    daterange_func = partial(DatetimeIndex, freq=MonthStart())
    return down_sample(df, daterange_func)

def down_sample(obj, daterange_func):
    if isinstance(obj, Panel):
        index = obj.major_axis
    else:
        index = obj.index

    start = datetime.combine(index[0].date(), time(0))
    end = datetime.combine(index[-1].date(), time(0))
    range = daterange_func(start=start, end=end)
    grouped = obj.groupby(range.asof)
    grouped._range = range
    return grouped

def fillforward(df):
    """
        Take a lower than day freq, and map it to business days.
        This is to make mapping to a daily chart easy and helps handle
        business days that vacations.
    """
    return df.asfreq(datetools.BDay(), method='pad')


def cols(self, *args):
    return self.xs(list(args), axis=1)

def dropna_get(x, pos):
    try:
        return x.dropna().iget(pos)
    except:
        return None


def aggregate_picker(grouped, grouped_indices, col=None):
    """
    In [276]: g.agg(np.argmax).high
    Out[276]: 
        key_0
        2007-04-27    281
        2007-04-30      0
        2007-05-01      5
        2007-05-02    294
        2007-05-03      3
        2007-05-04     53

    Should take something in that form and return a DataFrame with the proper date indexes and values...
    """
    index = []
    values = []
    for key, group in grouped:
        if col:
            group = group[col]
        sub_index = grouped_indices[key] 
        index.append(group.index[sub_index])
        values.append(group.iget_value(sub_index))
    return {'index':index, 'values':values}

# old version
def _kv_agg(grouped, func, col=None):
    """
        Works like agg but returns index label and value for each hit
    """
    if col:
        sub_indices = grouped.agg({col: func})[col]
    else:
        sub_indices = grouped.agg(func)

    data = aggregate_picker(grouped, sub_indices, col=col)
    return TimeSeries(data['values'], index=data['index'])

def kv_agg(grouped, func, col=None):
    """
        Simpler version that is a bit faster. Really, I don't use aggregate_picker, 
        which makes it slightly faster.
    """

    index = []
    values = []

    for key, group in grouped:
        if col:
            group = group[col]
        sub_index = func(group)
        val = group.iget_value(sub_index)
        values.append(val)
        index.append(group.index[sub_index])
    
    return TimeSeries(values, index=index)

def set_time(arr, hour, minute):
    """
        Given a list of datetimes, set the time on all of them
    """
    results = []
    t = time(hour, minute)
    for date in arr:
        d = datetime.combine(date.date(), t)
        results.append(d)
    return results      

def reset_time(df, hour, minute):
    if isinstance(df, (DataFrame, Series)):
        df.index = set_time(df.index, hour, minute)
    if isinstance(df, Panel):
        df.major_axis = set_time(df.major_axis, hour, minute)

def max_groupby(grouped, col=None):
    df = kv_agg(grouped, np.argmax, col)
    return df

th  = lambda x: time(9, 30) < x.time() <= time(16)
trading_hours = np.vectorize(th)

times = np.vectorize(lambda x: x.time())
hours = np.vectorize(lambda x: x.time().hour)
minutes = np.vectorize(lambda x: x.time().minute)

def time_slice(series, hour=None, minute=None):
    """
        Will vectorize a function taht returns a boolean array if value matches the hour
        and/or minute
    """
    bh = hour is not None
    bm = minute is not None
    if bh and bm:
        t = time(hour, minute)
        vec = np.vectorize(lambda x: x.time() == t)
    if bh and not bm:
        vec = np.vectorize(lambda x: x.time().hour == hour)
    if not bh and bm:
        vec = np.vectorize(lambda x: x.time().minute == minute)

    return vec(series.index)

def end_asof(index, label):
    """
        Like index.asof but places the timestamp to the end of the bar
    """
    if label not in index:
        loc = index.searchsorted(label, side='left')
        if loc > 0:

            return index[loc]
        else:
            return np.nan

    return label


class TimeIndex(object):
    def __init__(self, times):
        self.times = times

    def asof(self, date):
        testtime = date.time()
        last = None
        for time in self.times:
            if testtime == time:
                return date
            if testtime < time:
                # found spot
                break
            last = time
        if last is None:
            return date
        new_date = datetime.combine(date.date(), last)
        return new_date

def anchor(freq, start=None, end=None):
    if start is None:
        start = "1/1/2012 9:30AM"
    if end is None:
        end = "1/1/2012 4:00PM"
    ideal = DatetimeIndex(start=start, end=end, freq=freq)
    times = [date.time() for date in ideal]
    return TimeIndex(times)

def anchor_index(index, freq):
    ideal = anchor(freq)

    start = index[0]
    start = ideal.asof(start)
    end = index[-1]
    start, end = _get_range_edges(index, offset=freq, closed='right')
    ind = DatetimeIndex(start=start, end=end, freq=freq)
    return ind

def anchor_downsample(obj, freq, axis=None):
    """
        Point of this is to fix the freq to regular intervals like 9:30, 9:45, 10:00
        and not 9:13, 9:28: 9:43
    """
    if axis is None:
        axis = 0
        if isinstance(obj, Panel):
            axis = 1
    index = obj._get_axis(axis)
    ind = anchor_index(index, freq)
    bins = lib.generate_bins_dt64(index.asi8, ind.asi8, closed='right')
    labels = ind[1:]
    grouper = BinGrouper(bins, labels)
    return obj.groupby(grouper)

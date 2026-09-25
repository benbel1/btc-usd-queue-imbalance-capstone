"""Causal predictors and explicitly future-looking labels on a UTC grid."""
import numpy as np
import pandas as pd
BASE = ['return_1','return_5','return_10','volatility_60','spread_bps','log_depth']


def build_features(observations):
    d = observations.copy()
    d['timestamp'] = pd.to_datetime(d['timestamp'],utc=True)
    if d['timestamp'].duplicated().any():
        raise ValueError('duplicate timestamps')
    d = d.sort_values('timestamp').set_index('timestamp')
    if d.empty:
        raise ValueError('empty observations')
    if not (d.index == d.index.floor('s')).all():
        raise ValueError('observations must lie on whole UTC seconds')
    d = d.reindex(pd.date_range(d.index[0],d.index[-1],freq='s'))
    nums = ['bid','ask','bid_qty','ask_qty']
    for c in nums:
        d[c] = pd.to_numeric(d[c],errors='coerce')
    valid = (pd.to_numeric(d['valid'],errors='coerce').eq(1)
             & np.isfinite(d[nums]).all(axis=1) & d[nums].gt(0).all(axis=1)
             & d.ask.gt(d.bid) & d.session_id.notna())
    mid = ((d.bid+d.ask)/2).where(valid)
    depth = (d.bid_qty+d.ask_qty).where(valid)
    x = pd.DataFrame(index=d.index)
    x['mid'] = mid
    x['spread_bps'] = 10000*(d.ask-d.bid)/mid
    x['log_depth'] = np.log(depth)
    x['depth_btc'] = depth
    x['imbalance'] = (d.bid_qty-d.ask_qty)/depth
    for lag in (1,5,10):
        x[f'return_{lag}'] = 10000*np.log(mid/mid.shift(lag))
    x['volatility_60'] = x.return_1.rolling(60,min_periods=60).std(ddof=1)
    x['target'] = 10000*np.log(mid.shift(-10)/mid)
    x['label_end'] = x.index + pd.Timedelta(seconds=10)
    # All 71 grid points in [t-60,t+10] must be valid within one session.
    continuous = valid.rolling(71,min_periods=71).sum().shift(-10).eq(71)
    segment = d.session_id.ne(d.session_id.shift()).cumsum()
    same_session = segment.shift(60).eq(segment.shift(-10))
    x['eligible'] = continuous & same_session & np.isfinite(x[BASE+['imbalance','target']]).all(axis=1)
    x.index.name = 'timestamp'
    return x


def chronological_split(x, mode='pilot'):
    if mode == 'main':
        start = x.index[0].normalize()
        days = (x.index[-1].normalize()-start).days+1
        if days < 30:
            raise ValueError('main evaluation requires at least 30 calendar days')
        a = start+pd.Timedelta(days=int(days*.6))
        b = start+pd.Timedelta(days=int(days*.8))
    else:
        start,end = x.index[0],x.index[-1]
        a = start+(end-start)*.6
        b = start+(end-start)*.8
    ok = x.eligible
    train = x[ok & (x.index<a) & (x.label_end<a)]
    val = x[ok & (x.index>=a) & (x.index<b) & (x.label_end<b)]
    test = x[ok & (x.index>=b)]
    if min(map(len,[train,val,test])) < 100:
        raise ValueError('fewer than 100 eligible rows in a split, collect more data')
    return train,val,test,a,b

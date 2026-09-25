"""Descriptive checks and chronological pilot/main ridge comparison."""
import argparse,json,platform,sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import sklearn
from features import build_features,chronological_split,BASE

GRID = [.01,.1,1,10,100]
def pipeline(alpha):
    return make_pipeline(StandardScaler(),Ridge(alpha=alpha))

def metrics(y,p):
    e=np.asarray(y)-np.asarray(p)
    return {'mse':float(np.mean(e**2)),'rmse':float(np.sqrt(np.mean(e**2))),
            'mae':float(np.mean(np.abs(e)))}

def fit_compare(x,mode):
    tr,va,te,a,b=chronological_split(x,mode)
    out={'mode':mode,'train_rows':len(tr),'validation_rows':len(va),'test_rows':len(te),
         'validation_start':a.isoformat(),'test_start':b.isoformat(),
         'metrics':{},'selected_alpha':{},'interpretation':'Pilot results are exploratory only' if mode=='pilot' else 'Main held-out evaluation'}
    pred=te[['target','spread_bps','volatility_60']].copy()
    for name,cols in [('baseline',BASE),('augmented',BASE+['imbalance'])]:
        scores=[]
        for alpha in GRID:
            m=pipeline(alpha).fit(tr[cols],tr.target)
            scores.append((metrics(va.target,m.predict(va[cols]))['mse'],-alpha))
        alpha=-min(scores)[1]
        out['selected_alpha'][name]=alpha
        both=pd.concat([tr,va])
        m=pipeline(alpha).fit(both[cols],both.target)
        pred[name]=m.predict(te[cols])
        out['metrics'][name]=metrics(te.target,pred[name])
    pred['zero']=0.
    out['metrics']['zero']=metrics(te.target,pred.zero)
    base=out['metrics']['baseline']['mse']
    out['relative_mse_reduction']=1-out['metrics']['augmented']['mse']/base if base>0 else None
    for name in ['baseline','augmented']:
        pred[name+'_loss']=(pred.target-pred[name])**2
    day=pred.groupby(pred.index.normalize()).agg(n=('target','size'),
            baseline_sse=('baseline_loss','sum'),augmented_sse=('augmented_loss','sum'))
    out['test_days']=len(day)
    if mode=='main' and len(day)>=5:
        rng=np.random.default_rng(690)
        ratios=[]
        for _ in range(2000):
            s=day.iloc[rng.integers(0,len(day),len(day))].sum()
            if s.baseline_sse>0:ratios.append(1-s.augmented_sse/s.baseline_sse)
        out['paired_day_bootstrap_95pct']=np.quantile(ratios,[.025,.975]).tolist() if ratios else None
        out['bootstrap_note']='Approximate, assumes independent days, few test days limit inference.'
    else:
        out['paired_day_bootstrap_95pct']=None
        out['bootstrap_note']='Not estimated for pilot or fewer than five test days.'
    robust=pred[pred.index.second%10==0]
    out['nonoverlapping_10s_metrics']={n:metrics(robust.target,robust[n]) for n in ['baseline','augmented','zero']} if len(robust) else {}
    out['subgroups']={}
    for c in ['spread_bps','volatility_60']:
        cut=float(tr[c].median())
        for label,mask in [('low',pred[c]<=cut),('high',pred[c]>cut)]:
            s=pred[mask]
            out['subgroups'][c+'_'+label]={'training_median':cut,'rows':len(s),
                'metrics':{n:metrics(s.target,s[n]) for n in ['baseline','augmented','zero']} if len(s) else {}}
    return out,pred,day

def analyze(path,out,mode):
    out.mkdir(parents=True,exist_ok=False)
    d=pd.read_csv(path)
    x=build_features(d)
    daily=d.assign(day=pd.to_datetime(d.timestamp,utc=True).dt.floor('D')).groupby('day').agg(
        recorded_seconds=('valid','size'),valid_seconds=('valid','sum'))
    daily['recorded_valid_fraction']=daily.valid_seconds/daily.recorded_seconds
    daily['fraction_of_full_day_valid']=daily.valid_seconds/86400
    daily.to_csv(out/'coverage.csv')
    x.loc[x.eligible].to_csv(out/'features.csv',index=True)
    summary={'input':str(path),'grid_seconds':len(x),'eligible_rows':int(x.eligible.sum()),
             'data_start':x.index[0].isoformat(),'data_end':x.index[-1].isoformat(),
             'versions':{'python':platform.python_version(),'numpy':np.__version__,
             'pandas':pd.__version__,'scikit_learn':sklearn.__version__}}
    stats=x.loc[x.eligible,['spread_bps','depth_btc','imbalance','target']].describe(percentiles=[.01,.5,.99])
    stats.to_csv(out/'descriptive_statistics.csv')
    try:
        if mode == 'main':
            start=x.index[0].normalize()
            full_index=pd.date_range(start,periods=30,freq='D')
            if x.index[-1] >= start+pd.Timedelta(days=30):
                raise ValueError('main input must cover the preselected 30-day window only')
            qualified=daily.reindex(full_index).valid_seconds.fillna(0).ge(.95*86400)
            if qualified.sum()<24 or qualified.iloc[24:].sum()<5:
                raise ValueError('main coverage gate failed: need 24/30 days and 5/6 test days at 95% valid seconds')
        result,pred,day=fit_compare(x,mode)
        summary['evaluation']=result
        pred.to_csv(out/'predictions.csv')
        day.to_csv(out/'daily_losses.csv')
    except ValueError as e:
        summary['evaluation']={'status':'not_run','reason':str(e)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    if x.eligible.any():
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axs=plt.subplots(1,2,figsize=(10,4))
        z=x.loc[x.eligible]
        axs[0].hist(z.imbalance,bins=40);axs[0].set(xlabel='Queue imbalance',ylabel='Observations')
        axs[1].hist(z.spread_bps,bins=40);axs[1].set(xlabel='Quoted spread (basis points)',ylabel='Observations')
        fig.suptitle('BTC-USD pilot observations' if mode=='pilot' else 'BTC-USD main observations')
        fig.tight_layout();fig.savefig(out/'distributions.png',dpi=160);plt.close(fig)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--mode',choices=['pilot','main'],default='pilot')
    a=ap.parse_args();analyze(a.input,a.out,a.mode)

"""Descriptive attribution from saved predictions. Usage: python return_size.py predictions.csv output.csv"""
import sys
import numpy as np
import pandas as pd

def attribute(path):
    p = pd.read_csv(path)
    assert len(p) == 505117 and p.timestamp.is_unique and p.zero.eq(0).all()
    y = p.target
    names = ['baseline','augmented','zero']
    errors = p[names].sub(y,axis=0)
    assert np.isfinite(errors.to_numpy()).all()
    groups = pd.cut(y.abs(), [-1,0,1,2,5,np.inf], labels=['zero','(0,1]','(1,2]','(2,5]','>5'])
    records = []
    for band in groups.cat.categories:
        e = errors.loc[groups == band]
        rec = dict(band=band,n=len(e),share=len(e)/len(p))
        for label,loss in [('mse',e**2),('mae',e.abs())]:
            for name in names:
                rec[label+'_'+name] = loss[name].mean()
            rec[label+'_gain_contribution']=(loss.baseline-loss.augmented).sum()/len(p)
            rec[label+'_vs_zero_contribution']=(loss.zero-loss.augmented).sum()/len(p)
        records.append(rec)
    out=pd.DataFrame(records)
    assert out.n.sum()==len(p)
    for k,v in [('mse',errors**2),('mae',errors.abs())]:
        np.testing.assert_allclose(out[k+'_gain_contribution'].sum(),v.baseline.mean()-v.augmented.mean())
    return out

if __name__=='__main__':
    attribute(sys.argv[1]).to_csv(sys.argv[2],index=False)

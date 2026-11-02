import pathlib,json,numpy as np,pandas as pd,datetime,hashlib
R=pathlib.Path(r'ANALYSIS_WORKDIR');O=R/'results';s=json.loads((O/'summary.json').read_text())['evaluation'];p=pd.read_csv(O/'held_out_predictions.csv',index_col=0,parse_dates=True);assert len(p)==505117 and p.index.is_unique and p.index.is_monotonic_increasing;assert p.index.min()>=pd.Timestamp('2026-10-26T00:00:00Z') and p.index.max()<pd.Timestamp('2026-11-01T00:00:00Z');assert np.isfinite(p.to_numpy()).all() and (p.zero==0).all()
for name in ['baseline','augmented','zero']:
 e=p.target-p[name];m={'mse':float(np.mean(e**2)),'rmse':float(np.sqrt(np.mean(e**2))),'mae':float(np.mean(np.abs(e)))}
 for k,v in m.items():np.testing.assert_allclose(v,s['metrics'][name][k],rtol=1e-12,atol=1e-12)
d=p.assign(base=(p.target-p.baseline)**2,aug=(p.target-p.augmented)**2).groupby(p.index.normalize()).agg(n=('target','size'),b=('base','sum'),a=('aug','sum'));assert len(d)==6
rng=np.random.default_rng(690);ratios=[]
for _ in range(2000):
 z=d.iloc[rng.integers(0,6,6)].sum();ratios.append(1-z.a/z.b)
np.testing.assert_allclose(np.quantile(ratios,[.025,.975]),s['paired_day_bootstrap_95pct'],rtol=1e-12,atol=1e-12)
assert s['subgroups']['spread_bps_low']['rows']==0;assert s['subgroups']['spread_bps_high']['rows']==505117
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'saved_prediction_rows':len(p),'first_timestamp':p.index.min().isoformat(),'last_timestamp':p.index.max().isoformat(),'unique_ordered_finite':True,'saved_metrics_reproduced':True,'saved_bootstrap_reproduced':True,'tolerance':'rtol=atol=1e-12 for CSV round-trip floating point','test_days':6,'predictions_sha256':hashlib.sha256((O/'held_out_predictions.csv').read_bytes()).hexdigest(),'warnings':['Only six test days; day independence assumption limits bootstrap inference','Frozen training-median low-spread subgroup has zero test rows; not estimable and threshold not changed','Augmented MAE exceeds baseline and zero-return MAE despite lower MSE','Leave-one-day-out is exploratory aggregation without refitting']};(O/'post_analysis_verification.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))

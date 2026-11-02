import os
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[n]='1'
import pathlib,sys,json,datetime,time,hashlib,gc,ctypes
import numpy as np,pandas as pd
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'source'));from features import BASE
from analyze import fit_compare
checkpoint=json.loads((R/'feature-checkpoint.json').read_text());n=checkpoint['used_array_rows'];times=np.load(R/'working/eligible-times.npy',mmap_mode='r');cols=BASE+['imbalance','target','depth_btc'];v=np.lib.format.open_memmap(R/'working/synthetic-capacity.npy',mode='w+',dtype='float64',shape=(n,len(cols)));rng=np.random.default_rng(690)
for k in range(len(cols)):v[:,k]=rng.normal(size=n)
v[:,cols.index('spread_bps')]=np.abs(v[:,cols.index('spread_bps')]);v[:,cols.index('volatility_60')]=np.abs(v[:,cols.index('volatility_60')]);v[:,cols.index('depth_btc')]=np.exp(v[:,cols.index('depth_btc')]);v.flush()
x=pd.DataFrame(v,columns=cols,copy=False,index=pd.to_datetime(times[:n],utc=True));x['eligible']=True;x.iloc[0,x.columns.get_loc('eligible')]=False;x.iloc[-1,x.columns.get_loc('eligible')]=False;x['label_end']=x.index+pd.Timedelta(seconds=10)
print('Synthetic full-size capacity test: unchanged fitting code, no formal feature or target values loaded',flush=True);t=time.monotonic();result,pred,losses=fit_compare(x,'main')
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','synthetic_only':True,'formal_feature_or_target_values_loaded':False,'timestamp_grid_only_from_verified_checkpoint':True,'rows':n,'test_rows':len(pred),'elapsed_seconds':time.monotonic()-t,'source_sha256':{f:hashlib.sha256((R/'source'/f).read_bytes()).hexdigest() for f in ['analyze.py','features.py']},'method':'Unchanged fit_compare on full-size synthetic numeric values, same timestamps and eligibility; single-threaded; existing Windows paging; no OS settings changed.'};(R/'capacity-test.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)

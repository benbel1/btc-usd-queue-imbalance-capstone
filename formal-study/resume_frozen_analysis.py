"""Frozen analysis execution, 2026-11-02. Daily feature chunks and disk backing only; fit_compare unchanged."""
import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import pathlib,sys,json,datetime,hashlib,gc,ctypes,traceback
import numpy as np,pandas as pd
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'source'));from features import build_features,chronological_split,BASE
from analyze import fit_compare,metrics
OUT=R/'results';OUT.mkdir(exist_ok=True);WORK=R/'working';WORK.mkdir(exist_ok=True)
log=(OUT/'execution.log').open('a',encoding='utf-8')
def say(event,**kw):
 r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':event,**kw};s=json.dumps(r);print(s,flush=True);log.write(s+'\n');log.flush()
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def memory():
 class M(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total','available','totalPage','availablePage','totalVirtual','availableVirtual','extended']]
 m=M();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.available
def available_commit():
 class M(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total','available','totalPage','availablePage','totalVirtual','availableVirtual','extended']]
 m=M();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));return m.availablePage
S=pd.Timestamp('2026-10-02T00:00:00Z');E=pd.Timestamp('2026-11-01T00:00:00Z');A=pd.Timestamp('2026-10-20T00:00:00Z');B=pd.Timestamp('2026-10-26T00:00:00Z');cols=BASE+['imbalance','target','depth_btc']
try:
 say('resume_from_verified_features',available_ram=memory())
 gate=json.loads((OUT/'pre_fit_count_gate.json').read_text());assert gate['exact_match'];expected=gate['required']
 checkpoint=json.loads((R/'feature-checkpoint.json').read_text())
 for name,expected_hash in checkpoint['array_sha256'].items():
  h=hashlib.sha256()
  with (WORK/name).open('rb') as f:
   for block in iter(lambda:f.read(1048576),b''):h.update(block)
  assert h.hexdigest()==expected_hash,'Feature checkpoint changed'
 values=np.load(WORK/'eligible-values.npy',mmap_mode='r');times=np.load(WORK/'eligible-times.npy',mmap_mode='r');pos=checkpoint['used_array_rows']
 x=pd.DataFrame(values[:pos],columns=cols,copy=False,index=pd.to_datetime(times[:pos],utc=True));x.index.name='timestamp';x['eligible']=True;x.iloc[0,x.columns.get_loc('eligible')]=False;x.iloc[-1,x.columns.get_loc('eligible')]=False;x['label_end']=x.index+pd.Timedelta(seconds=10)
 tr,va,te,aa,bb=chronological_split(x,'main');actual=dict(expected);actual.update(eligible_after_purging=len(tr)+len(va)+len(te),training=len(tr),validation=len(va),test=len(te));assert actual==expected and aa==A and bb==B;del tr,va,te;gc.collect();say('resumed_count_gate_passed',counts=actual)
 capacity=json.loads((R/'capacity-test.json').read_text());assert capacity['status']=='PASS' and capacity['synthetic_only'] and capacity['rows']==pos
 for name,digest in capacity['source_sha256'].items():assert hashlib.sha256((R/'source'/name).read_bytes()).hexdigest()==digest
 if available_commit()<2*1024**3:raise MemoryError('Less than 2 GiB existing committed-memory headroom after loading verified features')
 say('full_size_synthetic_capacity_guard_passed',available_ram=memory(),available_commit=available_commit(),capacity_test_utc=capacity['utc'],settings_changed=False)
 save('execution_configuration.json',{'protocol':'Original frozen protocol; source/analyze.py fit_compare called unchanged','source_sha256':{n:hashlib.sha256((R/'source'/n).read_bytes()).hexdigest() for n in ['analyze.py','features.py']},'window':[S.isoformat(),E.isoformat()],'boundaries':[A.isoformat(),B.isoformat()],'bootstrap_seed':690,'bootstrap_resamples':2000,'ridge_grid':[.01,.1,1,10,100],'ridge_solver':'auto (unchanged sklearn Ridge default for dense inputs)','ridge_random_state':None,'threads':1,'platform':sys.platform,'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'sklearn':__import__('sklearn').__version__})
 say('formal_fit_started',available_ram=memory());result,pred,losses=fit_compare(x,'main');save('summary.json',{'counts':actual,'evaluation':result});pred.to_csv(OUT/'held_out_predictions.csv');losses['baseline_mse']=losses.baseline_sse/losses.n;losses['augmented_mse']=losses.augmented_sse/losses.n;losses['paired_mse_difference_baseline_minus_augmented']=losses.baseline_mse-losses.augmented_mse;losses['relative_mse_improvement']=1-losses.augmented_sse/losses.baseline_sse;losses.to_csv(OUT/'daily_paired_losses.csv');say('formal_fit_finished',selected_penalties=result['selected_alpha'])
 # Exploratory peer-review addition; aggregate fixed held-out predictions, never refit or retune.
 exploratory=[]
 for day in losses.index:
  retained=pred[pred.index.normalize()!=day];m={name:metrics(retained.target,retained[name]) for name in ['baseline','augmented','zero']};exploratory.append({'excluded_utc_day':day.date().isoformat(),'retained_rows':len(retained),'baseline_mse':m['baseline']['mse'],'augmented_mse':m['augmented']['mse'],'zero_mse':m['zero']['mse'],'relative_mse_improvement':1-m['augmented']['mse']/m['baseline']['mse'],'metrics':m})
 save('exploratory_leave_one_test_day_out.json',{'classification':'Exploratory peer-review addition, not original protocol','implemented_utc':'2026-11-02','method':'Omit each test UTC day from aggregation of the SAME frozen held-out predictions. No refitting, retuning, or penalty reselection. No new confirmatory interval.','results':exploratory});pd.DataFrame([{k:v for k,v in e.items() if k!='metrics'} for e in exploratory]).to_csv(OUT/'exploratory_leave_one_test_day_out.csv',index=False)
 # Descriptive and figures, after the unchanged confirmatory analysis.
 x.loc[x.eligible,['spread_bps','depth_btc','imbalance','target']].describe(percentiles=[.01,.5,.99]).to_csv(OUT/'descriptive_statistics.csv')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,axs=plt.subplots(1,2,figsize=(10,4));axs[0].hist(x.loc[x.eligible,'imbalance'],bins=40);axs[0].set(xlabel='Queue imbalance',ylabel='Observations');axs[1].hist(x.loc[x.eligible,'spread_bps'],bins=40);axs[1].set(xlabel='Quoted spread (basis points)',ylabel='Observations');fig.suptitle('BTC-USD main observations');fig.tight_layout();fig.savefig(OUT/'distributions.png',dpi=160);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4));days=[v.strftime('%b %d') for v in losses.index];ax.plot(days,losses.baseline_sse/losses.n,'o-',label='Baseline ridge');ax.plot(days,losses.augmented_sse/losses.n,'o-',label='Augmented ridge');ax.set(ylabel='Mean squared error (squared basis points)',xlabel='Held-out UTC day');ax.legend();fig.tight_layout();fig.savefig(OUT/'daily_model_losses.png',dpi=160);plt.close(fig)
 save('sensitivity_results.json',{'original_protocol':{'nonoverlapping_10s_metrics':result['nonoverlapping_10s_metrics'],'subgroups':result['subgroups']},'exploratory_addition':'exploratory_leave_one_test_day_out.json'});say('ANALYSIS_COMPLETE')
except Exception as e:
 say('BLOCKER',error=repr(e));traceback.print_exc(file=log);log.flush();raise

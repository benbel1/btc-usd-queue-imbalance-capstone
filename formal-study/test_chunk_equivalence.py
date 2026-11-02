import pathlib,sys,numpy as np,pandas as pd,json,datetime
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'source'));from features import build_features,BASE
n=3*86400;t=np.arange(n);mid=100+.01*np.sin(t/7)+.00001*t;obs=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=n,freq='s',tz='UTC'),'bid':mid-.01,'ask':mid+.01,'bid_qty':2+np.sin(t/9),'ask_qty':2+np.cos(t/9),'valid':1,'session_id':'a'});obs.loc[86395:86405,'valid']=0;obs.loc[172800:,'session_id']='b';full=build_features(obs);chunks=[]
for i in range(3):
 lo=max(0,i*86400-60);hi=min(n,(i+1)*86400+10);z=build_features(obs.iloc[lo:hi]);chunks.append(z[(z.index>=obs.timestamp.iloc[i*86400])&(z.index<obs.timestamp.iloc[i*86400]+pd.Timedelta(days=1))])
c=pd.concat(chunks);assert c.index.equals(full.index);assert c.eligible.equals(full.eligible);errors={}
for col in BASE+['imbalance','target','depth_btc']:
 m=full.eligible;np.testing.assert_allclose(c.loc[m,col],full.loc[m,col],rtol=1e-8,atol=1e-10);errors[col]=float(np.max(np.abs(c.loc[m,col]-full.loc[m,col])))
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'synthetic_only':True,'rows':n,'eligibility_identical':True,'all_features_agree_rtol_1e_8_atol_1e_10':True,'max_absolute_differences':errors},indent=2))

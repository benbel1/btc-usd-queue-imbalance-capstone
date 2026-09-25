import io,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from book import OrderBook
from collect import Sampler
from features import build_features,chronological_split,BASE
from analyze import fit_compare,pipeline


def fixture(n=1800):
    t=np.arange(n)
    mid=100+0.01*np.sin(t/7)+.001*t
    return pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=n,freq='s',tz='UTC'),
        'bid':mid-.01,'ask':mid+.01,'bid_qty':2+np.sin(t/9),
        'ask_qty':2+np.cos(t/9),'valid':1,'session_id':'synthetic-test'})

class ResearchTests(unittest.TestCase):
    def test_replacement_and_deletion(self):
        b=OrderBook();b.apply({'type':'snapshot','bids':[['99','2'],['98','3']],'asks':[['101','4']]})
        b.apply({'type':'l2update','changes':[['buy','99','5']]})
        self.assertEqual(b.best()[2],5)
        b.apply({'type':'l2update','changes':[['buy','99','0']]})
        self.assertEqual(b.best()[0],98)

    def test_atomic_batch(self):
        b=OrderBook();b.apply({'type':'snapshot','bids':[['99','2']],'asks':[['101','4']]})
        b.apply({'type':'l2update','changes':[['buy','102','1'],['sell','101','0'],['sell','103','2']]})
        self.assertEqual(b.best()[:2],(102.,103.))
        with self.assertRaises(ValueError):b.apply({'type':'l2update','changes':[['buy','104','1']]})

    def test_invalid_values(self):
        for price,size in [('0','1'),('99','-1'),('NaN','1'),('99','Infinity')]:
            with self.assertRaises(ValueError):OrderBook.put({},price,size)

    def test_sampler_receipt_time(self):
        class Writer:
            def __init__(self):self.rows=[]
            def writerow(self,row):self.rows.append(row)
        w=Writer();s=Sampler(w,0.1);s.session='test';s.heartbeat=.5
        s.book.apply({'type':'snapshot','bids':[['99','2']],'asks':[['101','4']]});s.active=True
        s.emit_due(1.1)
        s.book.apply({'type':'l2update','changes':[['buy','100','8']]})
        s.emit_due(2.1)
        self.assertEqual([r['bid'] for r in w.rows],[99.,100.])
        s.emit_due(7)
        self.assertEqual(w.rows[-1]['valid'],0)

    def test_target_and_imbalance(self):
        d=fixture();x=build_features(d);i=100
        mid=(d.bid+d.ask)/2
        self.assertAlmostEqual(x.target.iloc[i],10000*np.log(mid.iloc[i+10]/mid.iloc[i]))
        self.assertAlmostEqual(x.imbalance.iloc[i],(d.bid_qty.iloc[i]-d.ask_qty.iloc[i])/(d.bid_qty.iloc[i]+d.ask_qty.iloc[i]))
        self.assertFalse(x.eligible.iloc[:60].any());self.assertFalse(x.eligible.iloc[-10:].any())

    def test_future_changes_do_not_change_predictors(self):
        d=fixture();a=build_features(d)
        d.loc[101:,'bid']+=10;d.loc[101:,'ask']+=10
        b=build_features(d)
        pd.testing.assert_frame_equal(a[BASE+['imbalance']].iloc[:101],b[BASE+['imbalance']].iloc[:101])
        self.assertNotEqual(a.target.iloc[100],b.target.iloc[100])

    def test_gap_and_session_windows(self):
        d=fixture();d.loc[100,'valid']=0;x=build_features(d)
        self.assertFalse(x.eligible.iloc[90:161].any())
        d=fixture();d.loc[100:,'session_id']='new';x=build_features(d)
        self.assertFalse(x.eligible.iloc[90:160].any())
        d=fixture().drop(index=100);x=build_features(d)
        self.assertFalse(x.eligible.iloc[90:161].any())

    def test_partition_purging(self):
        tr,va,te,a,b=chronological_split(build_features(fixture()))
        self.assertTrue((tr.label_end<a).all());self.assertTrue((va.label_end<b).all())
        self.assertTrue((te.index>=b).all())

    def test_scaler_and_comparison(self):
        x=build_features(fixture());tr,va,te,a,b=chronological_split(x)
        m=pipeline(1).fit(tr[BASE],tr.target)
        np.testing.assert_allclose(m.named_steps['standardscaler'].mean_,tr[BASE].mean())
        r,p,d=fit_compare(x,'pilot')
        self.assertEqual(len(p),len(te));self.assertEqual(set(r['metrics']),{'baseline','augmented','zero'})
        self.assertIsNone(r['paired_day_bootstrap_95pct'])
        self.assertTrue(np.isfinite(p[['baseline','augmented']]).all().all())

    def test_short_main_rejected(self):
        with self.assertRaises(ValueError):chronological_split(build_features(fixture()),'main')

if __name__=='__main__':unittest.main()

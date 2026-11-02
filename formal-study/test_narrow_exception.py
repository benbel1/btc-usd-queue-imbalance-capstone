import pathlib,sys,json,csv,gzip,hashlib,datetime as dt,tempfile,unittest,sqlite3
R=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(R/'source/ops'));from assemble_reviewed import assemble,sha
F=['timestamp','bid','ask','bid_qty','ask_qty','valid','session_id','reason'];S=dt.datetime(2026,10,2,tzinfo=dt.timezone.utc);E=S+dt.timedelta(seconds=4)
def make(root,name='s',status='failed_no_market_data',valid=0,ticks=(0,2)):
 p=root/name/'collection';p.mkdir(parents=True)
 with (p/'observations.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=F);w.writeheader()
  for t in ticks:w.writerow(dict(zip(F,[(S+dt.timedelta(seconds=t)).isoformat(),1,2,1,1,valid,'session','bad' if not valid else ''])))
 with gzip.open(p/'raw.jsonl.gz','wt') as f:f.write(json.dumps({'connection_error':{'error':'synthetic'}})+'\n')
 m={'status':status,'seconds':len(ticks),'valid_seconds':valid*len(ticks),'messages':0,'connection_errors':[{'error':'synthetic'}],'observation_sha256':sha(p/'observations.csv')};(p/'metadata.json').write_text(json.dumps(m));return p.parent

def pin(p):
 m=json.loads((p/'collection/metadata.json').read_text());return {p.name:{'rows':m['seconds'],'sha256':{n:sha(p/'collection'/n) for n in ['metadata.json','observations.csv','raw.jsonl.gz']}}}
(R/'test-tmp').mkdir(exist_ok=True)
tempfile.tempdir=str(R/'test-tmp')
class NarrowException(unittest.TestCase):
 def test_exact_zero_case_preserves_invalid_and_missing(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r);z=assemble([p],r/'out',S,E,pin(p));rows=list(csv.DictReader((r/'out/observations.csv').open()));self.assertEqual(len(rows),4);self.assertEqual(z['explicit_missing_seconds'],2);self.assertEqual(rows[0]['reason'],'bad');self.assertEqual(rows[1]['reason'],'missing_recording_second');self.assertEqual(rows[1]['bid'],'')
 def test_unlisted_failure_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r)
   with self.assertRaisesRegex(ValueError,'Unapproved'):assemble([p],r/'out',S,E,{})
 def test_positive_valid_case_rejected_even_if_pinned(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r,valid=1)
   with self.assertRaisesRegex(ValueError,'Unapproved'):assemble([p],r/'out',S,E,pin(p))
 def test_changed_bytes_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r);w=pin(p);f=p/'collection/observations.csv';f.write_bytes(f.read_bytes()+b'\n')
   with self.assertRaisesRegex(ValueError,'checksum'):assemble([p],r/'out',S,E,w)
 def test_incomplete_raw_rejected_even_if_pinned(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r);f=p/'collection/raw.jsonl.gz';f.write_bytes(f.read_bytes()[:-8])
   with self.assertRaisesRegex(ValueError,'Incomplete raw'):assemble([p],r/'out',S,E,pin(p))
 def test_duplicate_timestamps_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r,'a','completed');q=make(r,'b','completed')
   with self.assertRaises(sqlite3.IntegrityError):assemble([p,q],r/'out',S,E)
 def test_exclusive_end(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r,status='completed',ticks=(0,4));z=assemble([p],r/'out',S,E);self.assertEqual(z['rows'],1)
 def test_partial_csv_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   r=pathlib.Path(t);p=make(r);f=p/'collection/observations.csv';f.write_bytes(f.read_bytes().rstrip(b'\r\n'));m=json.loads((p/'collection/metadata.json').read_text());m['observation_sha256']=sha(f);(p/'collection/metadata.json').write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,'Partial'):assemble([p],r/'out',S,E,pin(p))
if __name__=='__main__':unittest.main(verbosity=2)

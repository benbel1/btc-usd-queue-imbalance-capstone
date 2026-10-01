import csv,datetime as dt,gzip,json,pathlib,tempfile,unittest
from assemble_segments import assemble,sha
from cloud_service import Tail

FIELDS=['timestamp','bid','ask','bid_qty','ask_qty','valid','session_id','reason']
class OpsTests(unittest.TestCase):
    def make(self,root,name,seconds):
        p=root/name;p.mkdir();rows=[]
        for sec in seconds: rows.append(dict(zip(FIELDS,[f'2026-10-02T00:00:{sec:02d}+00:00',1,2,1,1,1,'same',''])))
        with (p/'observations.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
        with gzip.open(p/'raw.jsonl.gz','wt') as f:f.write('{}\n')
        (p/'metadata.json').write_text(json.dumps({'status':'completed','seconds':len(rows),'valid_seconds':len(rows),'observation_sha256':sha(p/'observations.csv')}))
        return p
    def test_gap_and_session_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            r=pathlib.Path(t);a=self.make(r,'a',[1,2]);b=self.make(r,'b',[5,6]);out=r/'out'
            q=assemble([a,b],out,dt.datetime.fromisoformat('2026-10-02T00:00:00+00:00'),dt.datetime.fromisoformat('2026-10-02T00:01:00+00:00'))
            self.assertEqual(q['rows'],4)
            with (out/'observations.csv').open() as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),60);self.assertEqual(rows[3]['valid'],'0');self.assertEqual(rows[3]['bid'],'');self.assertNotEqual(rows[2]['session_id'],rows[5]['session_id'])
    def test_duplicates_rejected(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as t:
            r=pathlib.Path(t);a=self.make(r,'a',[1]);b=self.make(r,'b',[1])
            with self.assertRaises(sqlite3.IntegrityError):assemble([a,b],r/'out',dt.datetime(2026,10,2,tzinfo=dt.timezone.utc),dt.datetime(2026,10,3,tzinfo=dt.timezone.utc))
    def test_incomplete_gzip_preserved_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            r=pathlib.Path(t);a=self.make(r,'a',[1]);p=a/'raw.jsonl.gz';p.write_bytes(p.read_bytes()[:-8]);before=sha(p)
            with self.assertRaises(ValueError):assemble([a],r/'out',dt.datetime(2026,10,2,tzinfo=dt.timezone.utc),dt.datetime(2026,10,3,tzinfo=dt.timezone.utc))
            self.assertEqual(before,sha(p))
    def test_valid_freshness_partial_line(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t)/'x.csv';p.write_text(','.join(FIELDS)+'\n2026-10-02T00:00:01+00:00,1,2,1,1,1,s,\n2026-10-02T00:00:02+00:00,,,,,0,s,missing')
            tail=Tail(p);tail.update();self.assertEqual(tail.latest,tail.valid)
            with p.open('a') as f:f.write('\n')
            tail.update();self.assertEqual(tail.latest-tail.valid,1)

if __name__=='__main__':unittest.main()


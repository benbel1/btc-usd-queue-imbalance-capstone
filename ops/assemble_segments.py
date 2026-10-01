"""Audit and assemble an explicit prospective UTC window, without model scoring.

Incomplete gzip is retained unchanged and rejected unless --allow-incomplete is
explicitly supplied after review. Complete CSV lines only; duplicates are fatal.
Missing timestamps remain gaps for the unchanged feature builder to reindex.
"""
import argparse,csv,datetime as dt,gzip,hashlib,json,pathlib,sqlite3,tempfile

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()

def assemble(segments,out,start,end,allow_incomplete=False):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);reports=[]
    with tempfile.TemporaryDirectory() as tmp:
        con=sqlite3.connect(str(pathlib.Path(tmp)/'rows.db'))
        con.execute('create table rows(t text primary key, row text)')
        header=None
        for segment in segments:
            segment=pathlib.Path(segment);p=segment/'collection';p=p if p.is_dir() else segment
            meta=json.loads((p/'metadata.json').read_text());observations=p/'observations.csv'
            if meta.get('status') not in ('completed','interrupted') and not allow_incomplete:
                raise ValueError('Unsealed segment requires explicit integrity review: '+str(p))
            actual=sha(observations);expected=meta.get('observation_sha256')
            if expected and actual!=expected:raise ValueError('Observation checksum mismatch: '+str(p))
            gzip_ok=True;error=None;raw_rows=0
            try:
                with gzip.open(p/'raw.jsonl.gz','rt') as f:
                    for line in f:json.loads(line);raw_rows+=1
            except (EOFError,OSError,ValueError) as exc:gzip_ok=False;error=str(exc)
            if not gzip_ok and not allow_incomplete:raise ValueError('Incomplete raw evidence, preserved for review: '+str(p)+': '+str(error))
            rows=valid=selected=0;partial=False
            with observations.open('rb') as f:
                h=next(csv.reader([f.readline().decode().strip()]))
                if header is not None and h!=header:raise ValueError('CSV schema mismatch')
                header=h
                for line in f:
                    if not line.endswith(b'\n'):partial=True;break
                    values=next(csv.reader([line.decode().strip()]));r=dict(zip(h,values))
                    if len(values)!=len(h):raise ValueError('Malformed CSV row')
                    t=dt.datetime.fromisoformat(r['timestamp']);rows+=1;valid+=r['valid']=='1'
                    if t.microsecond or t.utcoffset()!=dt.timedelta(0):raise ValueError('Non-UTC-second timestamp')
                    if start<=t<end:
                        # Segment prefix prevents accidental continuity across restarts.
                        r['session_id']=segment.name+':'+r['session_id'] if r['session_id'] else ''
                        con.execute('insert into rows values (?,?)',(t.isoformat(),json.dumps(r)));selected+=1
            if meta.get('status') in ('completed','interrupted'):
                if rows!=meta.get('seconds') or valid!=meta.get('valid_seconds'):raise ValueError('Metadata count mismatch')
            reports.append(dict(segment=str(segment),rows=rows,valid=valid,selected=selected,sha256=actual,gzip_ok=gzip_ok,gzip_error=error,raw_records=raw_rows,partial_csv_tail_excluded=partial,metadata_status=meta.get('status')))
        con.commit()
        with (out/'observations.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=header);w.writeheader()
            tick=start;missing=0
            def gap(t):
                r=dict.fromkeys(header,'');r.update(timestamp=t.isoformat(),valid='0',reason='missing_recording_second');return r
            for (row,) in con.execute('select row from rows order by t'):
                r=json.loads(row);t=dt.datetime.fromisoformat(r['timestamp'])
                while tick<t:w.writerow(gap(tick));missing+=1;tick+=dt.timedelta(seconds=1)
                w.writerow(r);tick=t+dt.timedelta(seconds=1)
            while tick<end:w.writerow(gap(tick));missing+=1;tick+=dt.timedelta(seconds=1)
        save={'window_start_inclusive':start.isoformat(),'window_end_exclusive':end.isoformat(),'segments':reports,'rows':con.execute('select count(*) from rows').fetchone()[0],'observation_sha256':sha(out/'observations.csv'),'gaps':'Retained; unchanged build_features reindexes missing seconds as invalid.','rules':'No scoring; preserve existing causal features, 71-point same-session eligibility, and chronological label purging.'}
        save['explicit_missing_seconds']=missing
        save['gaps']='Missing seconds explicitly marked valid=0 with empty prices/session and reason missing_recording_second; no continuity or prices imputed.'
        (out/'assembly.json').write_text(json.dumps(save,indent=2));con.close()
        return save

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('segments',nargs='+',type=pathlib.Path);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--start',required=True);ap.add_argument('--end',required=True);ap.add_argument('--allow-incomplete',action='store_true');a=ap.parse_args()
    print(json.dumps(assemble(a.segments,a.out,dt.datetime.fromisoformat(a.start),dt.datetime.fromisoformat(a.end),a.allow_incomplete),indent=2))

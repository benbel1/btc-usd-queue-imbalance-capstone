"""Handoff implementation fix, 2026-11-02: nine SHA-pinned zero-valid failures only. No general incomplete-file override; all gzip, CSV, counts and duplicate checks remain strict."""
import contextlib,argparse,csv,datetime as dt,gzip,hashlib,json,pathlib,sqlite3,tempfile

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()

def assemble(segments,out,start,end,verified_zero_valid=None):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False);reports=[]
    with tempfile.TemporaryDirectory() as tmp:
        with contextlib.closing(sqlite3.connect(str(pathlib.Path(tmp)/'rows.db'))) as con:
            con.execute('create table rows(t text primary key, row text)')
            header=None
            for segment in segments:
                segment=pathlib.Path(segment);p=segment/'collection';p=p if p.is_dir() else segment
                meta=json.loads((p/'metadata.json').read_text());observations=p/'observations.csv'
                exception=(verified_zero_valid or {}).get(segment.name)
                if meta.get('status') not in ('completed','interrupted'):
                    if not (exception and meta.get('status')=='failed_no_market_data' and meta.get('valid_seconds')==0 and meta.get('seconds')==exception['rows']):
                        raise ValueError('Unapproved failed segment: '+str(p))
                    for name in ['metadata.json','observations.csv','raw.jsonl.gz']:
                        if sha(p/name)!=exception['sha256'][name]:raise ValueError('Pinned exception checksum mismatch: '+str(p/name))
                elif exception:raise ValueError('Exception status changed: '+str(p))
                actual=sha(observations);expected=meta.get('observation_sha256')
                if not expected or actual!=expected:raise ValueError('Observation checksum mismatch: '+str(p))
                gzip_ok=True;error=None;raw_rows=0;feed_rows=0;error_rows=0;unknown_rows=0
                try:
                    with gzip.open(p/'raw.jsonl.gz','rt') as f:
                        for line in f:
                            obj=json.loads(line);raw_rows+=1
                            if 'raw' in obj:feed_rows+=1
                            elif 'connection_error' in obj:error_rows+=1
                            else:unknown_rows+=1
                except (EOFError,OSError,ValueError) as exc:gzip_ok=False;error=str(exc)
                if not gzip_ok:raise ValueError('Incomplete raw evidence, preserved for review: '+str(p)+': '+str(error))
                if feed_rows!=meta.get('messages') or error_rows!=len(meta.get('connection_errors',[])) or unknown_rows:raise ValueError('Raw feed/error count mismatch: '+str(p))
                rows=valid=selected=0;partial=False;previous=None
                with observations.open('rb') as f:
                    h=next(csv.reader([f.readline().decode().strip()]))
                    if header is not None and h!=header:raise ValueError('CSV schema mismatch')
                    header=h
                    for line in f:
                        if not line.endswith(b'\n'):raise ValueError('Partial CSV row: '+str(p))
                        values=next(csv.reader([line.decode().strip()]));r=dict(zip(h,values))
                        if len(values)!=len(h):raise ValueError('Malformed CSV row')
                        t=dt.datetime.fromisoformat(r['timestamp']);rows+=1;valid+=r['valid']=='1'
                        if t.microsecond or t.utcoffset()!=dt.timedelta(0):raise ValueError('Non-UTC-second timestamp')
                        if previous is not None and t<=previous:raise ValueError('Non-increasing timestamp: '+str(p))
                        previous=t
                        if r['valid'] not in ('0','1'):raise ValueError('Invalid validity flag')
                        if start<=t<end:
                            # Segment prefix prevents accidental continuity across restarts.
                            r['session_id']=segment.name+':'+r['session_id'] if r['session_id'] else ''
                            con.execute('insert into rows values (?,?)',(t.isoformat(),json.dumps(r)));selected+=1
                if meta.get('status') in ('completed','interrupted','failed_no_market_data'):
                    if rows!=meta.get('seconds') or valid!=meta.get('valid_seconds'):raise ValueError('Metadata count mismatch')
                if exception and valid!=0:raise ValueError('Exception has valid observations')
                if len(reports)%25==0:print('AUDITED_SEGMENTS',len(reports)+1,flush=True)
                reports.append(dict(segment=str(segment),rows=rows,valid=valid,selected=selected,sha256=actual,gzip_ok=gzip_ok,gzip_error=error,raw_records=raw_rows,feed_records=feed_rows,error_records=error_rows,verified_zero_valid_exception=bool(exception),partial_csv_tail_excluded=partial,metadata_status=meta.get('status')))
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


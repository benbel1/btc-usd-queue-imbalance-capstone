"""Immutable closed-segment backups with verified downloads and a 4 GiB cap.
Uses only the VM's bucket-scoped service account; no stored keys.
Never deletes local or cloud evidence. Backs up incomplete gzip unchanged and
flags it for review; assembly separately refuses it unless explicitly accepted.
"""
import argparse,base64,datetime as dt,gzip,hashlib,json,pathlib,urllib.request,urllib.parse,urllib.error,uuid,fcntl

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1048576),b''):h.update(c)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=pathlib.Path,required=True);ap.add_argument('--bucket',required=True);a=ap.parse_args()
    lock=(a.data/'backup.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stamp=lambda:dt.datetime.now(dt.timezone.utc).isoformat()
    state={'checked_utc':stamp(),'healthy':False,'verified_files':0}
    def status():
        tmp=a.data/'backup-status.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(a.data/'backup-status.json')
    token=None
    def api(url,method='GET',data=None,headers=None):
        nonlocal token
        if token is None:
            req=urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'})
            with urllib.request.urlopen(req,timeout=15) as r:token=json.load(r)['access_token']
        req=urllib.request.Request(url,data=data,method=method,headers={'Authorization':'Bearer '+token,**(headers or {})})
        return urllib.request.urlopen(req,timeout=120)
    try:
        base='https://storage.googleapis.com/storage/v1/b/'+a.bucket+'/o';existing={};page=''
        while True:
            with api(base+'?maxResults=1000'+('&pageToken='+urllib.parse.quote(page) if page else '')) as r:listing=json.load(r)
            for x in listing.get('items',[]):existing[x['name']]=x
            page=listing.get('nextPageToken');
            if not page:break
        total=sum(int(x['size']) for x in existing.values());cap=4*1024**3;warnings=[]
        for segment in sorted(a.data.glob('segment-*')):
            outcome=segment/'segment-outcome.json'
            if not outcome.exists() and not (segment/'recovery-review.json').exists():continue
            marker=segment/'backup-verified.json'
            if marker.exists():
                warnings.extend(json.loads(marker.read_text()).get('warnings',[]));continue
            segment_warnings=[]
            raw=segment/'collection/raw.jsonl.gz'
            try:
                with gzip.open(raw,'rb') as f:
                    for line in f:json.loads(line)
            except (EOFError,OSError,ValueError) as exc:
                segment_warnings.append({'segment':segment.name,'incomplete_raw':str(exc)});warnings.extend(segment_warnings)
            records=[]
            for p in sorted(segment.rglob('*')):
                if not p.is_file() or p.name.startswith('backup-'):continue
                name=str(p.relative_to(a.data));digest=sha(p);size=p.stat().st_size
                if name not in existing:
                    if total+size>cap:raise RuntimeError('4 GiB backup cap reached; originals preserved; approval or another backup destination required')
                    boundary='capstone'+uuid.uuid4().hex
                    metadata=json.dumps({'name':name,'metadata':{'sha256':digest}}).encode()
                    body=b'--'+boundary.encode()+b'\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'+metadata+b'\r\n--'+boundary.encode()+b'\r\nContent-Type: application/octet-stream\r\n\r\n'+p.read_bytes()+b'\r\n--'+boundary.encode()+b'--\r\n'
                    with api('https://storage.googleapis.com/upload/storage/v1/b/'+a.bucket+'/o?uploadType=multipart&ifGenerationMatch=0','POST',body,{'Content-Type':'multipart/related; boundary='+boundary}) as r:x=json.load(r)
                    existing[name]=x;total+=size
                x=existing[name]
                if int(x['size'])!=size or x.get('metadata',{}).get('sha256')!=digest:raise RuntimeError('Existing cloud object differs: '+name)
                h=hashlib.sha256()
                with api(base+'/'+urllib.parse.quote(name,safe='')+'?alt=media&generation='+x['generation']) as r:
                    while chunk:=r.read(1048576):h.update(chunk)
                if h.hexdigest()!=digest:raise RuntimeError('Backup download checksum mismatch: '+name)
                records.append({'path':name,'sha256':digest,'generation':x['generation'],'bytes':size});state['verified_files']+=1
            marker.write_text(json.dumps({'verified_utc':stamp(),'bucket':a.bucket,'objects':records,'warnings':segment_warnings},indent=2))
        state.update(healthy=total<3.5*1024**3 and not warnings,reason='integrity_review_needed' if warnings else 'verified' if total<3.5*1024**3 else 'backup_near_4GiB_cap',bucket_bytes=total,cap_bytes=cap,warnings=warnings)
    except Exception as exc:state['reason']=str(exc)
    finally:status()
    if not state['healthy']:raise SystemExit(1)

if __name__=='__main__':main()

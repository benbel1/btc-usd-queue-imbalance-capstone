"""Operational supervision only; collect.py and research rules are unchanged."""
import argparse, csv, datetime as dt, fcntl, hashlib, json, logging
from logging.handlers import RotatingFileHandler
import os, pathlib, shutil, signal, subprocess, sys, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UTC=dt.timezone.utc
def utc(): return dt.datetime.now(UTC).isoformat()
def save(p, value):
    tmp=p.with_suffix('.tmp'); tmp.write_text(json.dumps(value,indent=2)); tmp.replace(p)
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

class Tail:
    def __init__(self,p): self.p=p; self.offset=0; self.pending=b''; self.latest=None; self.valid=None
    def update(self):
        if not self.p.exists():return
        with self.p.open('rb') as f:
            f.seek(self.offset)
            while chunk:=f.read(65536):
                self.offset=f.tell(); lines=(self.pending+chunk).split(b'\n');self.pending=lines.pop()
                for line in lines:
                    row=next(csv.reader([line.decode().strip()]))
                    if not row or row[0]=='timestamp':continue
                    t=dt.datetime.fromisoformat(row[0]).timestamp();self.latest=t
                    if row[5]=='1':self.valid=t

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=pathlib.Path,required=True)
    ap.add_argument('--data',type=pathlib.Path,required=True);ap.add_argument('--segment-seconds',type=int,default=3600)
    ap.add_argument('--require-backup',action='store_true')
    ap.add_argument('--end',required=True);ap.add_argument('--port',type=int,default=8080)
    ap.add_argument('--min-free-gib',type=float,default=3);a=ap.parse_args()
    end=dt.datetime.fromisoformat(a.end).timestamp();a.data.mkdir(parents=True,exist_ok=True)
    lock=(a.data/'collector.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    state={'healthy':False,'reason':'starting','updated_utc':utc()}
    class Health(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path!='/healthz':self.send_error(404);return
            fresh=time.time()-dt.datetime.fromisoformat(state['updated_utc']).timestamp()<30
            ok=state['healthy'] and fresh
            body=json.dumps({'healthy':ok,'reason':state['reason']}).encode()
            self.send_response(200 if ok else 503);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*_):pass
    server=ThreadingHTTPServer(('0.0.0.0',a.port),Health)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    logger=logging.getLogger('collector');logger.setLevel(logging.INFO)
    handler=RotatingFileHandler(a.data/'service.log',maxBytes=1048576,backupCount=5);logger.addHandler(handler)
    # Never rewrite a crashed segment: mark it separately for integrity review.
    for d in a.data.glob('segment-*'):
        if not (d/'segment-outcome.json').exists():
            save(d/'recovery-review.json',{'detected_utc':utc(),'status':'unsealed_after_process_loss','warning':'Preserve raw gzip even if incomplete. Audit before assembly or backup acceptance.'})
    def publish(reason,healthy=False,**kw):
        nonlocal state
        state=dict(updated_utc=utc(),reason=reason,healthy=healthy,**kw);save(a.data/'health.json',state)
    try:
        while not stop.is_set() and time.time()<end:
            free=shutil.disk_usage(a.data).free
            if free<a.min_free_gib*1024**3:
                publish('disk_space_low',free_bytes=free);stop.wait(30);continue
            name='segment-'+dt.datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:8]
            d=a.data/name;d.mkdir();out=d/'collection';duration=min(a.segment_seconds,end-time.time())
            save(d/'provenance.json',{'started_request_utc':utc(),'duration_seconds':duration,'source_hashes':{p.name:digest(p) for p in a.project.glob('*.py')},'supervisor_pid':os.getpid()})
            child=subprocess.Popen([sys.executable,'-B','-u',str(a.project/'collect.py'),'--hours',str(duration/3600),'--out',str(out)],cwd=a.project,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
            def drain():
                for line in child.stdout:logger.info('%s %s',name,line.rstrip())
            reader=threading.Thread(target=drain,daemon=True);reader.start();tail=Tail(out/'observations.csv');started=time.time();reason='running'
            while child.poll() is None:
                tail.update();now=time.time();age=now-(tail.valid or started);free=shutil.disk_usage(a.data).free
                reason='disk_space_low' if free<a.min_free_gib*1024**3 else 'stale_valid_observations' if age>60 else 'starting' if tail.valid is None else 'healthy'
                if reason=='healthy' and a.require_backup:
                    try:
                        backup=json.loads((a.data/'backup-status.json').read_text())
                        if not backup['healthy'] or now-dt.datetime.fromisoformat(backup['checked_utc']).timestamp()>7200:reason='backup_requires_attention'
                    except (OSError,ValueError,KeyError):reason='backup_status_missing'
                publish(reason,reason=='healthy',collector_pid=child.pid,segment=name,valid_age_seconds=age,latest_valid_utc=dt.datetime.fromtimestamp(tail.valid,UTC).isoformat() if tail.valid else None,free_bytes=free)
                if stop.is_set() or free<a.min_free_gib*1024**3 or now>=end:
                    child.send_signal(signal.SIGINT)
                    try:child.wait(timeout=60)
                    except subprocess.TimeoutExpired:child.kill();child.wait();reason='forced_kill_integrity_review'
                    break
                stop.wait(5)
            reader.join(5)
            save(d/'segment-outcome.json',{'ended_utc':utc(),'exit_code':child.returncode,'reason':reason,'metadata_present':(out/'metadata.json').exists(),'integrity':'pending audit'})
            publish('between_segments',False,last_exit_code=child.returncode)
            if child.returncode!=0 and not stop.is_set():stop.wait(15)
        publish('study_window_finished' if time.time()>=end else 'stopped')
    finally:server.shutdown()

if __name__=='__main__':main()

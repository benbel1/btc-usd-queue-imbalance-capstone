"""Record a public Coinbase feed with causal UTC-second sampling.
Run on a machine with WebSocket access. No account or trading key is used.
"""
import argparse, asyncio, csv, gzip, hashlib, json, math, platform, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import websockets
from book import OrderBook

URL = 'wss://ws-feed.exchange.coinbase.com'
FIELDS = ['timestamp','bid','ask','bid_qty','ask_qty','valid','session_id','reason']

def utc(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat()

class Sampler:
    def __init__(self, writer, start):
        self.writer = writer
        self.next_tick = math.floor(start) + 1
        self.book = OrderBook()
        self.session = ''
        self.heartbeat = None
        self.active = False
        self.rows = 0
        self.valid_rows = 0

    def invalidate(self):
        self.active = False
        self.book = OrderBook()
        self.heartbeat = None

    def emit_due(self, now):
        # Called BEFORE applying each received message. The state at tick t
        # therefore never contains a message received after t.
        while self.next_tick <= now:
            t = self.next_tick
            row = dict.fromkeys(FIELDS, '')
            row.update(timestamp=utc(t), valid=0, session_id=self.session)
            try:
                if not self.active:
                    raise ValueError('disconnected_or_no_snapshot')
                if self.heartbeat is None or t - self.heartbeat > 5:
                    raise ValueError('heartbeat_timeout')
                row.update(zip(['bid','ask','bid_qty','ask_qty'], self.book.best()))
                row.update(valid=1, reason='')
                self.valid_rows += 1
            except ValueError as e:
                row['reason'] = str(e)
            self.writer.writerow(row)
            self.rows += 1
            self.next_tick += 1

async def collect(out, hours):
    out.mkdir(parents=True, exist_ok=False)
    start = time.time()
    stop = start + hours * 3600
    meta = {'started_utc':utc(start),'planned_hours':hours,'product':'BTC-USD',
            'channels':['level2_batch','heartbeat'],'endpoint':URL,
            'sample_interval_seconds':1,'python':sys.version,'platform':platform.platform(),
            'websockets_version':websockets.__version__,'time_basis':'local UTC receipt',
            'clock_requirement':'Synchronize the host clock before collection',
            'status':'running'}
    (out/'metadata.json').write_text(json.dumps(meta,indent=2))
    raw = gzip.open(out/'raw.jsonl.gz','wt',encoding='utf-8')
    samples = open(out/'observations.csv','w',newline='',encoding='utf-8')
    writer = csv.DictWriter(samples,fieldnames=FIELDS)
    writer.writeheader()
    sampler = Sampler(writer,start)
    errors = []
    messages = 0
    def record(obj):
        raw.write(json.dumps(obj,separators=(',',':'))+'\n')
    try:
        while time.time() < stop:
            sampler.invalidate()
            sampler.session = uuid.uuid4().hex
            try:
                timeout = max(.1,min(15,stop-time.time()))
                async with websockets.connect(URL,open_timeout=timeout,max_size=32*1024*1024,
                                              ping_interval=20,ping_timeout=20) as ws:
                    await ws.send(json.dumps({'type':'subscribe','product_ids':['BTC-USD'],
                                               'channels':['level2_batch','heartbeat']}))
                    connected = time.time()
                    while time.time() < stop:
                        now = time.time()
                        sampler.emit_due(now)
                        if now - (sampler.heartbeat or connected) > 5:
                            raise ValueError('heartbeat_timeout')
                        try:
                            msg = await asyncio.wait_for(ws.recv(),timeout=max(.01,min(.5,stop-now)))
                        except asyncio.TimeoutError:
                            samples.flush()
                            continue
                        received = time.time()
                        sampler.emit_due(min(received,stop))
                        if received > stop:
                            break
                        # Preserve even messages that fail JSON parsing.
                        record({'receipt_time':utc(received),'session_id':sampler.session,'raw':msg})
                        messages += 1
                        m = json.loads(msg)
                        if m.get('type') == 'error':
                            raise ValueError('exchange_error: '+str(m.get('message')))
                        if m.get('product_id') not in (None,'BTC-USD'):
                            continue
                        if m['type'] == 'heartbeat':
                            sampler.heartbeat = received
                        elif m['type'] in ('snapshot','l2update'):
                            sampler.book.apply(m)
                            sampler.active = True
                        if messages % 100 == 0:
                            raw.flush(); samples.flush()
            except (Exception,) as e:
                sampler.invalidate()
                entry = {'utc':utc(time.time()),'error':type(e).__name__+': '+str(e)}
                errors.append(entry)
                record({'connection_error':entry,'session_id':sampler.session})
                print(entry,flush=True)
                sampler.emit_due(min(time.time(),stop))
                if len(errors) >= 3 and sampler.valid_rows == 0:
                    break
                await asyncio.sleep(max(0,min(2,stop-time.time())))
        sampler.emit_due(min(time.time(),stop))
        meta['status'] = 'completed' if sampler.valid_rows else 'failed_no_market_data'
    except (KeyboardInterrupt,asyncio.CancelledError):
        meta['status'] = 'interrupted'
        raise
    finally:
        raw.close(); samples.close()
        meta.update(ended_utc=utc(time.time()),messages=messages,seconds=sampler.rows,
                    valid_seconds=sampler.valid_rows,connection_errors=errors,
                    observation_sha256=hashlib.sha256((out/'observations.csv').read_bytes()).hexdigest())
        (out/'metadata.json').write_text(json.dumps(meta,indent=2))
        print(json.dumps({k:meta[k] for k in ['status','seconds','valid_seconds','messages']},indent=2))

    return sampler.valid_rows > 0

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours',type=float,default=48)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    if args.hours <= 0:
        ap.error('--hours must be positive')
    sys.exit(0 if asyncio.run(collect(args.out,args.hours)) else 1)

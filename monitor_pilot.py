"""Local collector supervisor with independent process monitoring."""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
# Default to the checkout containing this script; no user-specific paths.
PROJECT = ROOT


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def event(run, kind, **fields):
    entry = dict(time_utc=utc(), event=kind, **fields)
    with (run / 'monitor.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(entry) + '\n')
    print(json.dumps(entry), flush=True)


class Observations:
    """Read only appended complete CSV lines, with bounded memory."""
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.pending = b''
        self.header = None
        self.latest = None
        self.valid = None

    def update(self):
        if not self.path.exists():
            return
        with self.path.open('rb') as stream:
            stream.seek(self.offset)
            while chunk := stream.read(65536):
                self.offset = stream.tell()
                lines = (self.pending + chunk).split(b'\n')
                self.pending = lines.pop()
                for line in lines:
                    values = next(csv.reader([line.decode('utf-8').strip()]))
                    if self.header is None:
                        self.header = values
                        continue
                    row = dict(zip(self.header, values))
                    stamp = datetime.fromisoformat(row['timestamp']).timestamp()
                    self.latest = stamp
                    if row.get('valid') == '1':
                        self.valid = stamp


def monitor(process, run, started, interval, stale_seconds):
    observations = Observations(run / 'collection' / 'observations.csv')
    previous = None
    while True:
        observations.update()
        now = time.time()
        code = process.poll()
        age = now - (observations.latest if observations.latest is not None else started)
        valid_age = now - (observations.valid if observations.valid is not None else started)
        health = 'stale_observations' if age > stale_seconds else (
            'stale_valid_observations' if valid_age > stale_seconds else (
                'healthy' if observations.valid is not None else 'starting'))
        state = dict(updated_utc=utc(), supervisor_pid=os.getpid(), collector_pid=process.pid,
                     collector_running=code is None, collector_exit_code=code,
                     health=health, observation_age_seconds=round(age, 2),
                     valid_observation_age_seconds=round(valid_age, 2))
        save(run / 'status.json', state)
        if health != previous:
            event(run, health, **state)
            previous = health
        if code is not None:
            event(run, 'collector_terminated', exit_code=code)
            return code
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours', type=float, default=48)
    parser.add_argument('--poll-seconds', type=float, default=5)
    parser.add_argument('--stale-seconds', type=float, default=60)
    parser.add_argument('--project-dir', type=Path, default=PROJECT, help='Checkout containing collect.py, analyze.py and tests')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data', help='Writable parent for new run folders')
    args = parser.parse_args()
    project = args.project_dir.expanduser().resolve()
    for required in ('collect.py', 'analyze.py', 'requirements.txt', 'tests'):
        if not (project / required).exists():
            parser.error(f'Missing {required} in project directory: {project}')
    if not all(math.isfinite(v) and v > 0 for v in (args.hours, args.poll_seconds, args.stale_seconds)):
        parser.error('hours and monitoring intervals must be finite and positive')
    if args.stale_seconds <= args.poll_seconds:
        parser.error('stale-seconds must exceed poll-seconds')
    run = args.data_dir.expanduser().resolve() / ('pilot-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir(parents=True, exist_ok=False)
    # Keep Python bytecode and matplotlib cache writes out of Documents.
    environment = os.environ.copy()
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['MPLCONFIGDIR'] = str(run / 'matplotlib-cache')
    environment['PYTHONUNBUFFERED'] = '1'
    configuration = dict(project=str(project), python=sys.executable, hours=args.hours,
                         poll_seconds=args.poll_seconds, stale_seconds=args.stale_seconds,
                         output=str(run), started_utc=utc(), supervisor_pid=os.getpid())
    save(run / 'run.json', configuration)
    print('Run folder: ' + str(run), flush=True)
    process = None
    stage = 'preflight'
    try:
        with (run / 'preflight.log').open('w', encoding='utf-8') as log:
            for command in ([sys.executable, '-B', '-m', 'pip', 'check'],
                            [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v']):
                result = subprocess.run(command, cwd=project, env=environment,
                                        stdout=log, stderr=subprocess.STDOUT)
                if result.returncode:
                    raise RuntimeError('Preflight failed; see preflight.log')
        stage = 'collection'
        started = time.time()
        with (run / 'collector.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-B', '-u', str(project / 'collect.py'),
                                        '--hours', str(args.hours), '--out', str(run / 'collection')],
                                       cwd=project, env=environment, stdout=log, stderr=subprocess.STDOUT)
            event(run, 'collector_started', collector_pid=process.pid, hours=args.hours)
            code = monitor(process, run, started, args.poll_seconds, args.stale_seconds)
        metadata_path = run / 'collection' / 'metadata.json'
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        if code != 0 or metadata.get('status') != 'completed' or metadata.get('valid_seconds', 0) <= 0:
            raise RuntimeError('Collector failed or stopped without valid completion; see collector.log')
        if time.time() - started + 2 < args.hours * 3600:
            raise RuntimeError('Collector terminated before its requested duration')
        stage = 'analysis'
        event(run, 'analysis_started')
        with (run / 'analysis.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([sys.executable, '-B', '-u', str(project / 'analyze.py'),
                                     '--input', str(run / 'collection' / 'observations.csv'),
                                     '--out', str(run / 'results'), '--mode', 'pilot'],
                                    cwd=project, env=environment, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError('Analysis failed; see analysis.log')
        summary = json.loads((run / 'results' / 'summary.json').read_text())
        save(run / 'outcome.json', dict(status='completed', ended_utc=utc(), collector_exit_code=code,
                                      evaluation=summary.get('evaluation')))
        event(run, 'run_completed', evaluation=summary.get('evaluation'))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=15)
            event(run, 'collector_terminated', exit_code=process.returncode, reason='supervisor_stopped')
        save(run / 'outcome.json', dict(status='failed', stage=stage, ended_utc=utc(), error=str(exc)))
        event(run, 'run_failed', stage=stage, error=str(exc))
        return 1


if __name__ == '__main__':
    sys.exit(main())

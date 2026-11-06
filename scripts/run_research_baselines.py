import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def external_backtests(owned):
    return [p.info['pid'] for p in psutil.process_iter(['pid', 'name', 'cmdline'])
            if p.info['pid'] not in owned
            and 'python' in (p.info['name'] or '').lower()
            and any(Path(arg.replace('\\', '/')).name == 'backtest_corrected.py'
                    for arg in (p.info['cmdline'] or []))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--start', default='2000-01-03')
    parser.add_argument('--end', default='2025-12-31')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--reserve-gb', type=float, default=1.5)
    parser.add_argument('--worker-gb', type=float, default=3.0)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.workers < 1 or args.workers > max(1, (os.cpu_count() or 1) - 2):
        parser.error('workers must leave at least two logical CPUs unused')
    if args.reserve_gb < 1 or args.worker_gb < 1:
        parser.error('memory reserve and per-worker budget must each be at least 1GB')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    jobs = [('v81', 'engine', 'v8.1'), ('freedom', 'freedom', 'v8.1'),
            ('v89', 'engine', 'v8.9')]
    snapshot = args.snapshot.resolve()
    if not (snapshot / 'manifest.json').is_file():
        parser.error('snapshot manifest missing')
    cache = ROOT / 'data/research/indicator_cache'
    commands = []
    for name, strategy, version in jobs:
        command = [sys.executable, '-u', str(ROOT / 'scripts/backtest_corrected.py'),
                   '--snapshot', str(snapshot), '--start', args.start, '--end', args.end,
                   '--strategy', strategy, '--version', version, '--slippage-bps', '5',
                   '--max-cached-frames', '64', '--indicator-cache', str(cache),
                   '--tag', f'{args.tag}_{name}']
        commands.append((name, command))
    if args.dry_run:
        print(json.dumps(commands, indent=2))
        return 0
    report = ROOT / 'reports' / f'research_baselines_{args.tag}.json'
    if report.exists():
        parser.error('campaign tag already exists; choose a new tag to preserve results')
    active, finished = {}, []
    environment = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                       MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    pending = list(commands)
    last_status, quiet_until = 0.0, 0.0
    attempts, interrupted = {}, []
    memory_budget = args.worker_gb
    try:
        while pending or active:
            for name, state in list(active.items()):
                process = state['process']
                code = process.poll()
                if code is not None:
                    state['handle'].close()
                    finished.append({'name': name, 'exit_code': code,
                                     'peak_rss_gb': state['peak'],
                                     'elapsed_seconds': time.monotonic() - state['start'],
                                     'log': str(state['log'])})
                    del active[name]
                    logger.info('%s finished: exit=%s peak_rss=%.2fGB', name, code, state['peak'])
                    if code != 0:
                        raise RuntimeError(f'{name} failed; inspect {state["log"]}')
                    continue
                memory = psutil.Process(process.pid).memory_info()
                state['peak'] = max(state['peak'], memory.rss / 2**30)
                state['peak_private'] = max(state['peak_private'],
                                             getattr(memory, 'private', memory.rss) / 2**30)
                with state['log'].open(encoding='utf-8', errors='replace') as stream:
                    stream.seek(state['offset'])
                    chunk = state['tail'] + stream.read()
                    state['offset'] = stream.tell()
                state['tail'] = chunk[-200:]
                state['ready'] = state['ready'] or 'day 0/' in chunk
                if any(marker in chunk for marker in ('Traceback (most recent call last)',
                                                       ' ERROR ', ' CRITICAL ')):
                    raise RuntimeError(f'{name} logged an error; inspect {state["log"]}')
            available = psutil.virtual_memory().available / 2**30
            external = external_backtests({s['process'].pid for s in active.values()})
            if external:
                quiet_until = time.monotonic() + 60
            if active and (external or available < args.reserve_gb):
                reason = 'external backtest active' if external else 'RAM reserve breached'
                for name, state in list(active.items()):
                    state['process'].terminate()
                    state['process'].wait()
                    state['handle'].close()
                    memory_budget = max(memory_budget, state['peak_private'] * 1.25)
                    interrupted.append({'name': name, 'reason': reason, 'log': str(state['log'])})
                    pending.insert(0, (name, state['command']))
                    del active[name]
                quiet_until = time.monotonic() + 60
                logger.warning('Own workers requeued: %s; external PIDs=%s', reason, external)
            estimated = max([memory_budget] + [s['peak_private'] * 1.3 for s in active.values()])
            ready = all(s['ready'] for s in active.values())
            if pending and len(active) < args.workers and ready and not external \
                    and time.monotonic() >= quiet_until \
                    and available >= args.reserve_gb + estimated:
                name, command = pending.pop(0)
                attempts[name] = attempts.get(name, 0) + 1
                log = ROOT / 'logs' / f'research_{args.tag}_{name}_attempt{attempts[name]}.log'
                handle = log.open('x', encoding='utf-8')
                process = subprocess.Popen(command, cwd=ROOT, stdout=handle,
                                           stderr=subprocess.STDOUT, env=environment,
                                           creationflags=getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0))
                active[name] = {'process': process, 'handle': handle, 'log': log,
                                'start': time.monotonic(), 'peak': 0.0, 'ready': False,
                                'peak_private': 0.0, 'command': command,
                                'offset': 0, 'tail': ''}
                logger.info('started %s pid=%s; free RAM=%.2fGB', name, process.pid, available)
            payload = {'pending': [name for name, _ in pending], 'finished': finished,
                       'active': {name: {'pid': s['process'].pid, 'peak_rss_gb': s['peak'],
                                         'ready': s['ready'], 'log': str(s['log'])}
                                  for name, s in active.items()},
                       'available_ram_gb': available, 'external_backtest_pids': external,
                       'memory_budget_gb': memory_budget, 'interrupted': interrupted}
            temporary = report.with_suffix('.tmp')
            temporary.write_text(json.dumps(payload, indent=2), encoding='utf-8')
            os.replace(temporary, report)
            if time.monotonic() - last_status >= 30:
                logger.info('active=%s pending=%s free RAM=%.2fGB', list(active),
                            [name for name, _ in pending], available)
                last_status = time.monotonic()
            time.sleep(2)
    except Exception:
        logger.exception('baseline campaign stopped')
        raise
    finally:
        for state in active.values():
            state['process'].terminate()
            state['process'].wait()
            state['handle'].close()
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Retire the original workflow only at a fully verified child-free boundary."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import point_guided_replayed_provenance as P
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files
from retire_qualified_redundant_hybrid import process, same, terminal, argument

BASE = ROOT/'out/research/n010-comparison-readiness'
WORK = BASE/'point-guided-replayed-reference-ladders-v1'
PLAN = RESULTS.parent/'experiments/039-operational-cpu-budget-continuation.md'
LOCK = RESULTS/'026-dynamic-execution-state-lock.json'
OWNED = (
    (1347641, '12891240', 'launch_replayed_point_guided_qualification.py',
     BASE/'point-guided-replayed-qualification-queue-v1'),
    (1362414, '12978277', 'qualify_point_guided_replayed_references.py', WORK),
    (1349762, '12903907', 'finish_replayed_readiness.py', BASE/'continuation-replayed-point-guided-v1'),
    (1370691, '13049296', 'retire_qualified_redundant_hybrid.py', BASE/'qualified-reference-quiescence-transition-v1'),
)
NEW_SOURCES = ('budget_reference_provenance.py', 'qualify_budget_references.py',
    'retire_point_guided_at_boundary.py', 'launch_budget_continuation.py',
    'finish_budget_readiness.py', 'readiness_preflight_budget.py', 'retire_budget_redundant_hybrid.py',
    'audit_budget_capability.py')


def children(pid):
    found = []
    for path in (Path('/proc')/str(pid)/'task').glob('*/children'):
        for value in path.read_text().split():
            child = process(int(value))
            if child and child['state'] != 'Z':
                found.append(child)
    return found


def clean_boundary():
    candidate = WORK/'C1_T_B8/qualification.json'
    try:
        first = json.loads(candidate.read_text())
        last = first['levels'][-1]['spp']
        if last > 65536:
            raise ValueError('clean transition window passed; do not interrupt high-level work')
        if last < 32768 or children(1362414):
            return None
        rows = []
        for directory in sorted(WORK.iterdir()):
            if not directory.is_dir() or directory.name not in P.SELECTED:
                raise ValueError('unexpected original acquisition root entry')
            raw = (directory/'qualification.json').read_bytes()
            q = json.loads(raw)
            allowed = {'qualification.json', 'scene.n008'}
            for level in q['levels']:
                spp = level['spp']
                attempt = json.loads((directory/f'n{spp}.attempt.json').read_text())
                if not attempt.get('pass') or attempt.get('returncode') != 0:
                    return None
                allowed |= set(level['all_payload_sha256']) | {
                    f'n{spp}.attempt.json', f'n{spp}.meta.json', f'n{spp}.stdout.json',
                    f'n{spp}.stderr.log', f'screen-n{spp}.json'}
            if {path.name for path in directory.iterdir()} != allowed:
                return None
            rows.append((directory, raw))
        return rows
    except (FileNotFoundError, json.JSONDecodeError, IndexError):
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing transition')
    ctypes.CDLL(None).prctl(15, b'n010_budget_cut', 0, 0, 0)
    inputs = {}
    P.prerequisites(inputs)
    capability = read(RESULTS/'141-operational-budget-capability-and-program-assembly.json', inputs)
    if not capability.get('complete') or not capability.get('all_pass'):
        raise ValueError('operational capability/program assembly proof incomplete')
    check_files(capability['inputs'], inputs)
    lock = read(LOCK, inputs)
    for path in (PLAN, *(Path(__file__).with_name(name) for name in NEW_SOURCES)):
        inputs[str(path.resolve())] = sha(path)
    originals = []
    for pid, start, script, work in OWNED:
        value = process(pid)
        if (not value or value['start_ticks'] != start or value['uid'] != os.getuid()
                or not any(Path(word).name == script for word in value['command'])
                or argument(value['command'], '--queue' if pid == 1347641 else '--work') != work):
            raise ValueError('original workflow identity differs: '+str(pid))
        originals.append(value)
    if originals[1]['ppid'] != originals[0]['pid']:
        raise ValueError('original queue/qualifier relationship differs')
    check_files(inputs, {})
    source_inputs = {path: digest for path, digest in inputs.items() if Path(path).suffix in ('.py', '.md')}
    args.work.mkdir(parents=True)
    record = {'schema': 'n010-operational-cpu-budget-boundary-transition/1',
        'complete': False, 'all_pass': False, 'gpu_run': False, 'pid': os.getpid(),
        'work': str(WORK), 'phase': 'WAITING_FOR_COMPLETE_CHILD_FREE_BOUNDARY',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'input_sha256': inputs, 'original_processes': originals, 'signal_targets': [],
        'imported_prefixes': [], 'native_processes_interrupted': 0,
        'scientific_gates_changed': False, 'cap_failure_claimed': False,
        'original_processes_terminal': False, 'power_settings_changed': False}
    def save():
        record['updated_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (args.work/'status.json').write_text(json.dumps(record, indent=2)+'\n')
    save()
    stopped = []
    try:
        last_check = 0
        while True:
            if not all(same(value) and not terminal(value) for value in originals):
                raise ValueError('original workflow terminated before a verified boundary')
            if time.monotonic()-last_check > 5:
                check_files(source_inputs, {})
                last_check = time.monotonic()
            boundary = clean_boundary()
            if boundary is None:
                time.sleep(.05)
                continue
            for value in originals[:2]:
                if not same(value) or process(value['pid'])['command'] != value['command']:
                    raise ValueError('workflow identity changed before STOP')
                os.kill(value['pid'], signal.SIGSTOP)
                stopped.append(value)
            time.sleep(.03)
            boundary = clean_boundary()
            if boundary is not None:
                break
            # A native won the race. Resume parents and keep the native untouched.
            for value in reversed(stopped):
                if same(value):
                    os.kill(value['pid'], signal.SIGCONT)
            stopped.clear()
            record['safe_boundary_race_misses'] = record.get('safe_boundary_race_misses', 0)+1
            save()
        for value in originals[2:]:
            if children(value['pid']):
                raise ValueError('expected an idle child-free original waiter')
            if not same(value) or process(value['pid'])['command'] != value['command']:
                raise ValueError('idle workflow identity changed')
            os.kill(value['pid'], signal.SIGSTOP)
            stopped.append(value)
        old_statuses = (
            BASE/'point-guided-replayed-qualification-queue-v1/status.json',
            RESULTS/'128-replayed-point-guided-reference-qualification.json',
            BASE/'continuation-replayed-point-guided-v1/status.json',
            BASE/'qualified-reference-quiescence-transition-v1/status.json')
        driver_status = json.loads(old_statuses[2].read_text())
        watcher_status = json.loads(old_statuses[3].read_text())
        if driver_status.get('jobs') or driver_status['phase'] != 'WAITING_FOR_FULL_REFERENCES':
            raise ValueError('old comparison driver is no longer idle')
        if watcher_status.get('signal_targets') or watcher_status['phase'] != 'WAITING_FOR_COMPLETE_SELECTED_QUALIFICATION':
            raise ValueError('old hybrid retirement worker is no longer waiting')
        for index, path in enumerate(old_statuses):
            target = args.work/f'retained-workflow-{index}-{path.name}'
            target.write_bytes(path.read_bytes())
            inputs[str(target.resolve())] = sha(target)
            record.setdefault('retained_workflow_bytes', []).append({
                'source': str(path), 'archive': str(target.resolve()), 'sha256': sha(target)})
        record['phase'] = 'VERIFYING_COMPLETE_IMPORTED_PREFIXES'
        save()
        for directory, raw in boundary:
            qpath = directory/'qualification.json'
            archive = args.work/f'retained-{directory.name}-qualification.json'
            archive.write_bytes(raw)
            q = json.loads(raw)
            cell, text = directory.name.rsplit('_T_B', 1)
            proof = P.verify_reference(directory, cell, int(text), lock['cells'][cell], inputs, require_eligible=False)
            if qpath.read_bytes() != raw or inputs.pop(str(qpath.resolve())) != sha(archive):
                raise ValueError('imported qualification changed during frozen audit')
            inputs[str(archive.resolve())] = sha(archive)
            record['imported_prefixes'].append({'name': directory.name, 'archive': str(archive.resolve()),
                'sha256': sha(archive), 'levels': [level['spp'] for level in q['levels']], 'provenance': proof})
        if children(1362414):
            raise ValueError('native child appeared inside frozen boundary')
        check_files(inputs, {})
        record['signal_targets'] = originals
        record['phase'] = 'VERIFIED_COMPLETE_BOUNDARY_RETIRING_ORIGINAL_WORKFLOW'
        save()
        for value in reversed(originals):
            if not same(value):
                raise ValueError('verified target identity changed before TERM')
            os.kill(value['pid'], signal.SIGTERM)
    except (ValueError, OSError, KeyError, AssertionError) as error:
        record['failure'] = str(error)
    finally:
        for value in reversed(stopped):
            if same(value):
                try:
                    os.kill(value['pid'], signal.SIGCONT)
                except ProcessLookupError:
                    pass
    if record['signal_targets'] and not record.get('failure'):
        deadline = time.monotonic()+10
        while not all(terminal(value) for value in originals) and time.monotonic()<deadline:
            time.sleep(.1)
        record['original_processes_terminal'] = all(terminal(value) for value in originals)
        if not record['original_processes_terminal']:
            record['failure'] = 'verified original workflow has not terminated; no continuation dispatch'
    if not record.get('failure'):
        record['retained_complete_file_inventory'] = [{
            'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path),
            'qualification_mutable_on_future_continuation': path.name == 'qualification.json'}
            for path in sorted(WORK.rglob('*')) if path.is_file()]
        record['all_pass'] = True
        record['phase'] = 'COMPLETE_PREFIX_BOUNDARY_RETIRED_ORIGINAL_WORKFLOW'
    else:
        record['phase'] = 'RETAINED_BOUNDARY_TRANSITION_REFUSAL_OR_FAILURE'
    record['complete'] = True
    save()
    args.output.write_text(json.dumps(record, indent=2)+'\n')
    print(record['phase'], flush=True)
    raise SystemExit(0 if record['all_pass'] else 2)

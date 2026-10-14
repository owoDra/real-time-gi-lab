#!/usr/bin/env python3
"""Retire only an owned, idle continuation-v3, preserving every source/output."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files
from calibrate_renderer import shader_hashes


def process(pid):
    p = Path('/proc')/str(pid)
    fields = (p/'stat').read_text().rsplit(')', 1)[1].split()
    words = [w.decode() for w in (p/'cmdline').read_bytes().split(b'\0') if w]
    return {'pid': pid, 'uid': p.stat().st_uid, 'start_ticks': fields[19],
        'state': fields[0], 'command': words}


def children(pid):
    found = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            fields = (p/'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[1]) == pid:
                found.append(process(int(p.name)))
        except (OSError, ProcessLookupError):
            pass
    return found


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse prior retirement record')
    continuation = ROOT/'out/research/n010-comparison-readiness/continuation-v3'
    original = process(a.pid)
    words = original['command']
    if (original['uid'] != os.getuid() or not any(Path(w).name == 'finish_readiness.py' for w in words)
        or Path(words[words.index('--work')+1]).resolve() != continuation
        or Path(words[words.index('--references')+1]).resolve() != ROOT/'out/research/n010-comparison-readiness/reference-view-recovery-v1'
        or Path(words[words.index('--reference-view-record')+1]).resolve() != RESULTS/'067-recovery-reference-view.json'
        or Path(words[words.index('--lock')+1]).resolve() != RESULTS/'026-dynamic-execution-state-lock.json'):
        raise ValueError('unexpected driver UID/command/work identity')
    reserved = [RESULTS/name for name in ('029-full-renderer-calibration.json', '043-c1-b8-pt-quality-ladder.json',
        '044-c1-complete-pt-quality-ladder.json', '046-calibration-quiet-sizing.json',
        '047-readiness-preflight.json', '048-sponza-dynamic-cohort.json')]
    status_path = continuation/'status.json'
    before = json.loads(status_path.read_text())
    if before['phase'] != 'WAITING_FOR_ELIGIBLE_REFERENCES' or before['jobs'] or before['complete']:
        raise ValueError('driver is not idle waiting with zero executed jobs')
    check_files(before['input_sha256'], {})
    if shader_hashes() != before['shader_sha256'] or any(p.exists() for p in reserved) or children(a.pid):
        raise ValueError('shader/output/child state differs; refuse retirement')
    a.work.mkdir(parents=True)
    record = {'schema': 'n010-idle-comparison-driver-retirement/1', 'complete': False, 'gpu_run': False,
        'phase': 'INSPECTING_IDLE_OWNED_DRIVER', 'original_process': original,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'script_sha256': sha(Path(__file__)),
        'plan_sha256': sha(RESULTS.parent/'experiments/034-parallel-hybrid-acquisition-and-driver-retirement.md'),
        'scope': 'Workflow retirement only; no CPU/GPU acquisition killed or completed; no quiet-calibration claim'}
    stopped = False
    try:
        os.kill(a.pid, signal.SIGSTOP)
        stopped = True
        deadline = time.monotonic()+5
        while process(a.pid)['state'] not in ('T', 't'):
            if time.monotonic() > deadline:
                raise ValueError('parent stop not confirmed')
            time.sleep(.05)
        now = process(a.pid)
        raw = status_path.read_bytes()
        last = json.loads(raw)
        if (now['start_ticks'] != original['start_ticks'] or now['command'] != words
            or last['phase'] != 'WAITING_FOR_ELIGIBLE_REFERENCES' or last['jobs'] or last['complete']
            or children(a.pid) or any(p.exists() for p in reserved)):
            raise ValueError('driver changed or a job/output exists; resume without retiring')
        check_files(last['input_sha256'], {})
        if shader_hashes() != last['shader_sha256']:
            raise ValueError('shader changed during inspection')
        (a.work/'retained-driver-status.json').write_bytes(raw)
        record.update(last_status_sha256=sha(a.work/'retained-driver-status.json'),
            last_status_path=str((a.work/'retained-driver-status.json').resolve()),
            frozen_input_sha256=last['input_sha256'], shader_sha256=last['shader_sha256'],
            reserved_outputs_absent=[str(p) for p in reserved], children_at_retirement=[])
        os.kill(a.pid, signal.SIGTERM)
        os.kill(a.pid, signal.SIGCONT)
        stopped = False
        deadline = time.monotonic()+60
        while True:
            try:
                terminal = process(a.pid)['state'] == 'Z'
            except (FileNotFoundError, ProcessLookupError):
                terminal = True
            if terminal:
                break
            if time.monotonic() > deadline:
                raise ValueError('driver termination not confirmed')
            time.sleep(.1)
        check_files(last['input_sha256'], {})
        if sha(status_path) != record['last_status_sha256'] or any(p.exists() for p in reserved):
            raise ValueError('retained status/output changed during retirement')
        record.update(complete=True, phase='RETIRED_IDLE_WAITING_DRIVER', original_pipeline_completed=False,
            driver_terminal_confirmed=True, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    except (ValueError, OSError, KeyError, AssertionError) as error:
        record.update(complete=True, phase='RETIREMENT_REFUSED_OR_UNCONFIRMED', failure=str(error))
    finally:
        if stopped:
            os.kill(a.pid, signal.SIGCONT)
    a.output.write_text(json.dumps(record, indent=2)+'\n')
    print(record['phase'], flush=True)
    raise SystemExit(0 if record['phase'] == 'RETIRED_IDLE_WAITING_DRIVER' else 2)

#!/usr/bin/env python3
"""After one verified completed boundary, launch the explicit replacement workflow."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import point_guided_replayed_provenance as P
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files
from retire_qualified_redundant_hybrid import process
from retire_point_guided_at_boundary import NEW_SOURCES, PLAN, WORK

BASE = ROOT/'out/research/n010-comparison-readiness'
SCRIPTS = ROOT/'scripts/research/n010_comparison_readiness'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists():
        raise ValueError('refuse existing budget workflow launch')
    args.work = args.work.resolve()
    outputs = {n: RESULTS/name for n, name in {
        138: '138-operational-cpu-budget-boundary-transition.json',
        139: '139-operational-budget-workflow-launch.json',
        140: '140-budget-point-guided-reference-qualification.json',
        142: '142-qualified-budget-reference-quiescence-transition.json'}.items()}
    if any(path.exists() for path in outputs.values()):
        raise ValueError('refuse retained budget workflow outputs')
    ctypes.CDLL(None).prctl(15, b'n010_budget_acq', 0, 0, 0)
    inputs = {}
    P.prerequisites(inputs)
    capability_path = RESULTS/'141-operational-budget-capability-and-program-assembly.json'
    capability = json.loads(capability_path.read_text())
    if not capability.get('complete') or not capability.get('all_pass'):
        raise ValueError('operational capability/program assembly proof incomplete')
    check_files(capability['inputs'], inputs)
    inputs[str(capability_path)] = sha(capability_path)
    for path in (PLAN, *(SCRIPTS/name for name in NEW_SOURCES)):
        inputs[str(path)] = sha(path)
    check_files(inputs, {})
    source_inputs = {path: digest for path, digest in inputs.items() if Path(path).suffix in ('.py', '.md')}
    args.work.mkdir(parents=True)
    status = {'schema': 'n010-operational-budget-workflow-launch/1', 'complete': False,
        'all_pass': False, 'gpu_run': False, 'pid': os.getpid(), 'input_sha256': inputs,
        'phase': 'WAITING_FOR_VERIFIED_COMPLETED_BOUNDARY', 'children': [],
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'scope': 'Operational launch only; no sample/quality/timing gate passed by this record'}
    def save():
        status['updated_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (args.work/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    save()
    python = str(BASE/'venv/bin/python')
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [env.get('NIX_LD_LIBRARY_PATH'), env.get('LD_LIBRARY_PATH')]))
    try:
        command = [python, str(SCRIPTS/'retire_point_guided_at_boundary.py'),
            '--work', str(args.work/'boundary'), '--output', str(outputs[138])]
        status['boundary_command'] = command
        save()
        with (args.work/'boundary.stdout.log').open('w') as stdout, (args.work/'boundary.stderr.log').open('w') as stderr:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
            status['boundary_pid'] = child.pid
            save()
            while child.poll() is None:
                check_files(source_inputs, {})
                time.sleep(5)
        status['boundary_returncode'] = child.returncode
        if child.returncode:
            raise ValueError('retained completed-boundary transition refused; no continuation dispatch')
        transition = json.loads(outputs[138].read_text())
        if not transition['complete'] or not transition['all_pass'] or not transition['original_processes_terminal']:
            raise ValueError('actual completed-boundary PASS missing')
        check_files(inputs, {})
        inputs[str(outputs[138])] = sha(outputs[138])
        status['phase'] = 'LAUNCHING_EXPLICIT_REPLACEMENT_WORKFLOW'
        save()
        commands = [
            ('qualification', [python, str(SCRIPTS/'qualify_budget_references.py'),
                '--lock', str(RESULTS/'026-dynamic-execution-state-lock.json'), '--work', str(WORK), '--output', str(outputs[140])]),
            ('retirement', [python, str(SCRIPTS/'retire_budget_redundant_hybrid.py'),
                '--work', str(args.work/'qualified-retirement'), '--output', str(outputs[142])]),
            ('comparison', [python, str(SCRIPTS/'finish_budget_readiness.py'),
                '--work', str(args.work/'comparison'), '--references', str(BASE/'reference-view-replayed-point-guided-v1'),
                '--reference-view-record', str(RESULTS/'127-replayed-point-guided-reference-view.json'),
                '--lock', str(RESULTS/'026-dynamic-execution-state-lock.json')])]
        for name, command in commands:
            check_files(inputs, {})
            with (args.work/(name+'.stdout.log')).open('w') as stdout, (args.work/(name+'.stderr.log')).open('w') as stderr:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            current = process(child.pid)
            if not current:
                raise ValueError('new workflow process exited before identity capture: '+name)
            status['children'].append({'name': name, 'process': current, 'command': command})
            save()
        status['all_pass'] = True
        status['phase'] = 'REPLACEMENT_WORKFLOW_LAUNCHED_NOT_QUALIFICATION'
    except (ValueError, OSError, KeyError, AssertionError) as error:
        status['failure'] = str(error)
        status['phase'] = 'RETAINED_LAUNCH_REFUSAL_OR_FAILURE'
    status['complete'] = True
    save()
    outputs[139].write_text(json.dumps(status, indent=2)+'\n')
    print(status['phase'], flush=True)
    raise SystemExit(0 if status['all_pass'] else 2)

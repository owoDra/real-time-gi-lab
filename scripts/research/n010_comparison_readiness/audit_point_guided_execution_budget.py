#!/usr/bin/env python3
"""Retain second-level provenance and observed offline CPU budget risk."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import point_guided_replayed_provenance as P
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files


def process(pid):
    base = Path('/proc') / str(pid)
    raw = {name: (base/name).read_bytes() for name in ('stat', 'cmdline', 'limits', 'status')}
    fields = raw['stat'].decode().rsplit(')', 1)[1].split()
    return raw, fields


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing audit')
    directory = ROOT/'out/research/n010-comparison-readiness/point-guided-replayed-reference-ladders-v1/C1_T_B8'
    qpath = directory/'qualification.json'
    qbytes = qpath.read_bytes()
    q = json.loads(qbytes)
    if [level['spp'] for level in q['levels']] != [8192, 16384]:
        raise ValueError('expected the first two completed levels')
    args.work.mkdir(parents=True)
    archive = args.work/'retained-second-qualification.json'
    archive.write_bytes(qbytes)
    inputs = {str(Path(__file__).resolve()): sha(Path(__file__)), str(archive.resolve()): sha(archive)}
    result = {'schema': 'n010-point-guided-second-level-and-cpu-budget-audit/1',
        'complete': False, 'all_pass': False, 'gpu_run': False, 'native_acquisition_run': False,
        'classification': 'POST_HOC_PROVENANCE_AND_OPERATIONAL_CPU_BUDGET_DIAGNOSIS',
        'eligible_for_references': False, 'scoring_exclusions': 0, 'inputs': inputs,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'observed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'qualification_source': {'path': str(qpath), 'sha256': sha(archive), 'archive': str(archive.resolve())},
        'runtime_conditions_changed': False, 'cap_failure_claimed': False}
    try:
        lock = read(RESULTS/'026-dynamic-execution-state-lock.json', inputs)
        result['provenance'] = P.verify_reference(directory, 'C1', 8, lock['cells']['C1'], inputs,
                                                  require_eligible=False)
        if qpath.read_bytes() != qbytes or inputs.pop(str(qpath.resolve())) != sha(archive):
            raise ValueError('qualification changed during audit')
        parent = 1362414
        parent_raw, parent_stat = process(parent)
        parent_cmd = parent_raw['cmdline'].split(b'\0')
        if (parent_stat[19] != '12978277' or parent_stat[1] != '1347641'
                or not any(Path(word.decode()).name == 'qualify_point_guided_replayed_references.py'
                           for word in parent_cmd if word)):
            raise ValueError('original qualifier process identity differs')
        children = (Path('/proc')/str(parent)/'task'/str(parent)/'children').read_text().split()
        if len(children) != 1:
            raise ValueError('expected exactly one ongoing next-level native invocation')
        native = int(children[0])
        native_raw, native_stat = process(native)
        command = [word.decode() for word in native_raw['cmdline'].split(b'\0') if word]
        if (native_stat[1] != str(parent) or Path(command[0]) != P.BINARY
                or command[command.index('--spp')+1] != '32768'
                or command[command.index('--threads')+1] != '16'
                or command[command.index('--scene')+1] != str(directory/'scene.n008')):
            raise ValueError('current native is not the original next-level acquisition')
        for pid, raw in ((parent, parent_raw), (native, native_raw)):
            for name, data in raw.items():
                target = args.work/f'proc-{pid}-{name}.snapshot'
                target.write_bytes(data)
                inputs[str(target.resolve())] = sha(target)
        if 'Max cpu time              172800               172800' not in native_raw['limits'].decode():
            raise ValueError('observed CPU guard differs')
        ticks_per_second = os.sysconf('SC_CLK_TCK')
        waited_cpu_seconds = (int(parent_stat[13])+int(parent_stat[14]))/ticks_per_second
        # Includes small reaped bookkeeping children; not a pure renderer cost.
        projected = waited_cpu_seconds*(262144-131072)/16384
        result['observed_execution'] = {'qualifier_pid': parent, 'qualifier_start_ticks': parent_stat[19],
            'current_native_pid': native, 'native_start_ticks': native_stat[19],
            'current_spp': 32768, 'ticks_per_second': ticks_per_second,
            'waited_children_cpu_seconds': waited_cpu_seconds,
            'completed_native_intervals': [[0, 8192], [8192, 16384]],
            'scope': 'Aggregate reaped child CPU includes both complete native invocations and bookkeeping; current native is excluded'}
        result['operational_budget_diagnostic'] = {'cpu_guard_seconds': 172800,
            'elapsed_guard_seconds': 43200, 'threads': 16,
            'cpu_guard_elapsed_equivalent_at_16_busy_threads': 172800/16,
            'linear_projected_final_interval_cpu_seconds': projected,
            'projection_exceeds_cpu_guard': projected > 172800,
            'projection_assumption': 'Equal aggregate CPU per new sample at the same C1 B8 state; not an observed future runtime',
            'interpretation': 'Potential operational interruption before the final sample cap. No statistical cap-failure conclusion or runtime limit change.',
            'next_action': 'Resolve the operational budget prospectively before a conflicting high-level invocation; retain complete prefixes and all failures, unchanged scientific gates and no automatic retry.'}
        result['statistical_screen'] = q['levels'][-1]['screen']
        result['qualification_classification'] = q['classification']
        check_files(inputs, {})
        result['inputs_unchanged_after_audit'] = True
        result['all_pass'] = True
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result.get(key) for key in ('all_pass', 'failure', 'observed_execution', 'operational_budget_diagnostic')}))
    raise SystemExit(0 if result['all_pass'] else 2)

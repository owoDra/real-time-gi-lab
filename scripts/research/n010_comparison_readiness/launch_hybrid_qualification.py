#!/usr/bin/env python3
"""Complementary plan-034 GPU acquisition after complete hybrid proof."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files

SELECTED = ('C4_T_B2', 'C4_T_B8', 'C5_T_B2', 'C5_T_B8', 'C6_T_B2', 'C6_T_B8',
            'C1_T_B8', 'C2_T_B8', 'C3_T_B8')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--queue', type=Path, required=True)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.queue.exists() or a.work.exists() or a.output.exists():
        raise ValueError('refuse prior hybrid queue/acquisition')
    ctypes.CDLL(None).prctl(15, b'n010_hyb_acq', 0, 0, 0)
    scripts = Path(__file__).parent
    paths = [Path(__file__), a.lock,
        RESULTS.parent/'experiments/029-hybrid-reference-acquisition.md',
        RESULTS.parent/'experiments/034-parallel-hybrid-acquisition-and-driver-retirement.md']
    paths += [scripts/name for name in ('qualify_hybrid_references.py', 'hybrid_reference_provenance.py',
        'qualify_references.py', 'validate_hybrid_reference_prefix.py', 'validate_hybrid_reference_controls.py')]
    paths += list((ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1').iterdir())
    paths += list((ROOT/'out/research/n010-comparison-readiness/hybrid-prefix-build-v1').iterdir())
    # Resolve every path now: missing prospective inputs must refuse startup.
    inputs = {str(p.resolve()): sha(p) for p in paths}
    a.queue.mkdir(parents=True)
    status = {'schema': 'n010-hybrid-qualification-queue/1', 'complete': False,
        'phase': 'WAITING_FOR_COMPLETE_HYBRID_PROOFS', 'gpu_run': False,
        'pid': os.getpid(), 'input_sha256': inputs, 'attempts': [],
        'selected_transports': list(SELECTED),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
    def save():
        (a.queue/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    save()
    try:
        proofs = [RESULTS/name for name in ('098-hybrid-full-numerical-conformance.json',
            '099-hybrid-physical-controls.json', '101-hybrid-all-state-and-prefix.json')]
        while True:
            check_files(inputs, {})
            ready = True
            for path in proofs:
                if not path.exists():
                    ready = False
                    continue
                try:
                    proof = json.loads(path.read_text())
                except json.JSONDecodeError:
                    ready = False
                    continue
                if proof.get('complete') and not proof.get('all_pass'):
                    raise ValueError('completed hybrid dependency failed: '+path.name)
                ready = ready and proof.get('complete') and proof.get('all_pass')
            if ready:
                break
            time.sleep(30)
        command = [sys.executable, str(scripts/'qualify_hybrid_references.py'),
            '--lock', str(a.lock), '--transports', *SELECTED, '--work', str(a.work), '--output', str(a.output)]
        status['phase'] = 'EXECUTING_SINGLE_FRESH_HYBRID_ACQUISITION'
        status['gpu_run'] = True
        attempt = {'command': command}
        status['attempts'].append(attempt)
        save()
        with (a.queue/'stdout.log').open('w') as out, (a.queue/'stderr.log').open('w') as err:
            proc = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err)
        attempt['returncode'] = proc.returncode
        check_files(inputs, {})
        if proc.returncode:
            raise ValueError('single hybrid acquisition failed/refused; no retry')
        status['phase'] = 'HYBRID_ACQUISITION_FINISHED_PENDING_VIEW_PROVENANCE_TRANSITION'
    except (ValueError, OSError, KeyError, AssertionError) as error:
        status.update(phase='TERMINAL_FAILURE_NO_RETRY', failure=str(error))
    status['complete'] = True
    save()
    print(status['phase'], flush=True)
    raise SystemExit(0 if status['phase'] == 'HYBRID_ACQUISITION_FINISHED_PENDING_VIEW_PROVENANCE_TRANSITION' else 2)

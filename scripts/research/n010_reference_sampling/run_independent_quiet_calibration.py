#!/usr/bin/env python3
"""Plan 042: unchanged quiet sizing/accepted calibration, once and in order."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
import calibrate_renderer as C
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

PLAN = RESULTS.parent/'experiments/042-prospective-independent-quiet-calibration.md'
CALIBRATOR_SHA = '64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    args = ap.parse_args()
    args.work = args.work.resolve()
    sizing, accepted = (RESULTS/name for name in ('046-calibration-quiet-sizing.json', '029-full-renderer-calibration.json'))
    if args.work.exists() or sizing.exists() or accepted.exists():
        raise ValueError('refuse existing calibration attempt; no retry/overwrite')
    # This is a waiting supervisor, not a computing worker; the unchanged
    # quiescence detector must continue to see every real acquisition child.
    ctypes.CDLL(None).prctl(15, b'gi_timing_queue', 0, 0, 0)
    calibrator = SCRIPTS/'calibrate_renderer.py'
    if sha(calibrator) != CALIBRATOR_SHA:
        raise ValueError('frozen calibrator changed')
    inputs = {str(p.resolve()): sha(p) for p in (PLAN, Path(__file__), calibrator,
        ROOT/'build/n009/phos-n010-capture', ROOT/'build/n009/phos-n010-pixel-pt',
        ROOT/'build/n009/n010-neutral-work-verify',
        ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract',
        ROOT/'research/lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md',
        ROOT/'research/lanes/n010-comparison-readiness/experiments/009-timing-calibration-execution.md',
        ROOT/'research/lanes/n010-comparison-readiness/experiments/012-amendment-5-sizing-probe-range.md')}
    lock_path = RESULTS/'026-dynamic-execution-state-lock.json'
    lock = read(lock_path, inputs)
    for spec in lock['cells'].values():
        for path in (ROOT/spec['state_directory']).iterdir():
            if path.is_file():
                inputs[str(path.resolve())] = sha(path)
    for directory in (ROOT/'build/n009/shaders',
        ROOT/'assets/Vulkan-Samples-Assets/scenes/sponza',
        ROOT/'out/research/n008-hdr-oracle/phase-b-states/n004-scenes'):
        for path in directory.rglob('*'):
            if path.is_file():
                inputs[str(path.resolve())] = sha(path)
    stopped = read(RESULTS/'147-light-surface-bounded-feasibility.json', inputs)
    if not stopped['complete'] or stopped['classification'] != 'BOUNDED_FEASIBILITY_FAIL_STOP':
        raise ValueError('current candidate terminal stop required')
    sequence = ROOT/'out/research/n010-comparison-readiness/light-surface-sequence-v1/status.json'
    old = read(sequence, inputs)
    if not old.get('complete') or old['phase'] != 'STOPPED_NO_RETRY':
        raise ValueError('reference sequence must actually stop')
    pid = old['pid']
    if (Path('/proc')/str(pid)).exists():
        stat = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
        if int(stat[19]) == old['start_ticks'] and stat[0] != 'Z':
            raise ValueError('reference sequence process still live')
    C.quiescent()
    args.work.mkdir(parents=True)
    record = {'schema': 'n010-independent-quiet-calibration-sequence/1', 'complete': False,
        'all_pass': False, 'scope': 'Calibration capability only; no reference or comparison admission',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'input_sha256': inputs, 'phase': 'INITIAL_QUIESCENCE_PASS', 'steps': []}
    def save():
        record['observed_utc'] = datetime.now(timezone.utc).isoformat()
        (args.work/'status.json').write_text(json.dumps(record, indent=2)+'\n')
    save()
    try:
        for mode, output in (('sizing', sizing), ('accepted', accepted)):
            check_files(inputs, {})
            C.quiescent()
            command = [sys.executable, str(calibrator), '--mode', mode, '--lock', str(lock_path),
                       '--work', str(args.work/mode), '--output', str(output)]
            if mode == 'accepted':
                plan = read(sizing, inputs)
                if not plan['complete'] or not plan['all_pass'] or len(plan['rows']) != 16:
                    raise ValueError('complete full-boundary sizing PASS required')
                command += ['--plan', str(sizing)]
            step = {'command': command, 'returncode': None}
            record['steps'].append(step)
            record['phase'] = mode.upper()
            save()
            stdout, stderr = (args.work/(mode+suffix) for suffix in ('.stdout.log', '.stderr.log'))
            with stdout.open('wb') as out, stderr.open('wb') as err:
                child = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err, start_new_session=True)
                step['pid'] = child.pid
                step['start_ticks'] = int((Path('/proc')/str(child.pid)/'stat').read_text().rsplit(')', 1)[1].split()[19])
                save()
                step['returncode'] = child.wait()
            step.update(stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
            save()
            if step['returncode'] != 0:
                raise ValueError('calibration runtime failure; retained without retry')
            value = read(output, inputs)
            if not value['complete'] or not value['all_pass'] or len(value['rows']) != 16:
                raise ValueError('calibration gate failure; retained without retry')
            check_files(inputs, {})
        record.update(phase='CALIBRATION_COMPLETE_NO_COMPARISON_ADMISSION', complete=True, all_pass=True)
    except (ValueError, OSError, KeyError, AssertionError) as error:
        record.update(phase='STOPPED_NO_RETRY', complete=True, failure=str(error))
    save()
    raise SystemExit(0 if record['all_pass'] else 2)

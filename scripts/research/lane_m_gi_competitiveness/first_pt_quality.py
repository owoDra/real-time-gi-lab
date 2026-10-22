#!/usr/bin/env python3
"""Prepare on CPU, or owner-execute exactly H01/B2 pixel PT 1 spp. No queue."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tarfile

import reference_step as R
from audit_h01_evidence import memory
from score_hdr import score
from score_retained import reference

PLAN = R.ROOT / 'out/m001-h01-b2-pt-n1-plan.json'
WORK = R.BASE / 'H01_T_B2/pixel-pt-n1'
ARCHIVE = R.ROOT / 'out/m001-h01-b2-pt-n1-quality.tar'
BINARY = R.ROOT / 'build/n009/phos-n010-pixel-pt'
BINARY_SHA = 'b96880ba40c8466b4210d9e5af0dad80855c96416496a6c47ad9dc7670d60ea0'
SHADER = R.ROOT / 'build/n009/shaders/n010_pixel_pt.spv'
SHADER_SHA = 'e8e03c3e7438159f9b0a4a5d4e4e61e841d054c06aab442d80c613face199069'


def command():
    return ['bash', str(R.ROOT / 'scripts/run_with_vulkan.sh'), str(BINARY),
            '--state', str(R.LANE / 'capture/M001-H01-hwrt'),
            '--out', str(WORK / 'capture'), '--family', 'pixel-pt',
            '--vertices', '2', '--spp', '1', '--seed', '305419896', '--frames', '1']


def prepare():
    state, audit, inputs = R.preflight('H01', 2)
    ref = reference('H01', 2)
    spec = {'state_directory': str((R.LANE / 'capture/M001-H01-hwrt').relative_to(R.ROOT)),
            'state_sha256': state['sha256']}
    verification = R.P.verify_reference(ref, 'H01', 2, spec, inputs)
    for p, digest in ((BINARY, BINARY_SHA), (SHADER, SHADER_SHA)):
        R.require(R.sha(p) == digest, 'original native binary/shader changed')
    R.require(not WORK.exists() and not ARCHIVE.exists(), 'existing native output/partial/archive')
    paths = [BINARY, SHADER, Path(__file__).resolve(),
             R.ROOT / 'scripts/run_with_vulkan.sh',
             R.ROOT / 'src/research/n010_comparison_readiness/pixel_pt_main.cpp',
             R.ROOT / 'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl',
             Path(R.__file__), R.ROOT / 'scripts/research/lane_m_gi_competitiveness/score_retained.py']
    inputs.update({str(p): R.sha(p) for p in paths})
    return {'schema': 'lane-m-m001-first-pt-quality-plan/1', 'command': command(),
            'scope': 'H01/T_B2 only, pixel-pt 1 spp, original seed 305419896, one static frame',
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip(),
            'reference_verification': verification, 'input_sha256': inputs,
            'source_state_audit': audit, 'gpu_executed': False,
            'accepted_timing': False, 'next': 'Owner may execute this single case; stop and audit before another budget.'}


def execute():
    # This entry point is for the owner's explicit command, not an automatic task.
    R.require(PLAN.is_file(), 'prepare and review exact plan first')
    planned = R.read(PLAN)
    current = prepare()
    R.require(planned['command'] == current['command']
              and planned['input_sha256'] == current['input_sha256'], 'prepared CPU plan drifted')
    WORK.mkdir(parents=True)
    R.write_new(WORK / 'started.json', {'plan_sha256': R.sha(PLAN), 'plan': planned})
    result = {'schema': 'lane-m-m001-first-pt-quality-result/1', 'complete': False,
              'plan_sha256': R.sha(PLAN), 'command': command(), 'gpu_executed': True,
              'accepted_timing': False, 'classification': 'FAILED_RETAIN_PARTIAL_NO_RETRY'}

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))

    native = None
    try:
        env = os.environ.copy()
        env.pop('PHOS_N010_CALIBRATION_DOSE', None)
        native = subprocess.Popen(command(), cwd=R.ROOT, env=env, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  start_new_session=True, preexec_fn=limits)
        try:
            stdout, stderr = native.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(native.pid, signal.SIGTERM)
            try:
                stdout, stderr = native.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(native.pid, signal.SIGKILL)
                stdout, stderr = native.communicate()
            (WORK / 'native.stdout.txt').write_text(stdout)
            (WORK / 'native.stderr.txt').write_text(stderr)
            raise ValueError('180 second operational timeout; no automatic retry')
        (WORK / 'native.stdout.txt').write_text(stdout)
        (WORK / 'native.stderr.txt').write_text(stderr)
        result['returncode'] = native.returncode
        R.require(native.returncode == 0, 'native failed; retain original partial outputs')
        for p, digest in planned['input_sha256'].items():
            R.require(R.sha(Path(p)) == digest, 'frozen input changed during execution: ' + p)
        capture = WORK / 'capture'
        state = R.Q.L.read_state(capture)
        R.require(state['sha256'] == R.CAPTURE_SHA['H01'], 'captured physical state differs')
        frames = R.read(capture / 'frames.json')
        R.require((frames['family'], frames['spp'], frames['vertices'], frames['seed'],
                   frames['width'], frames['height'], len(frames['frames'])) ==
                  ('pixel-pt', 1, 2, 305419896, 320, 180, 1), 'native budget/frame metadata differs')
        for name in ('geometry-state.bin', 'frame-state.bin', 'direct.pfm', 'indirect.pfm', 'total.pfm'):
            R.require(R.sha(capture / name) == R.sha(capture / 'frames/0' / name),
                      'one-frame/native root output differs: ' + name)
        result['memory'] = memory(R.read(capture / 'allocation-ledger.json'))
        ref = reference('H01', 2)
        result['quality'] = score(capture, R.read(ref / 'qualification.json'), ref, WORK / 'quality.json')
        result['reference_qualification_sha256'] = R.sha(ref / 'qualification.json')
        result['timing'] = {'classification': 'DIAGNOSTIC_UNCALIBRATED_NO_SPEED_CLAIM', 'native': frames}
        result['complete'] = True
        result['classification'] = 'PASS' if result['quality']['pilot_quality_target'] == 'PASS' else 'QUALITY_FAIL'
    except Exception as e:
        result['error'] = str(e)
    result['payload_sha256'] = {str(p.relative_to(WORK)): R.sha(p)
                                for p in sorted(WORK.rglob('*')) if p.is_file()}
    R.write_new(WORK / 'result.json', result)
    with ARCHIVE.open('xb') as handle:
        with tarfile.open(fileobj=handle, mode='w') as tar:
            tar.add(WORK / 'result.json', arcname='result.json')
            tar.add(PLAN, arcname='plan.json')
    return {'classification': result['classification'], 'complete': result['complete'],
            'archive': str(ARCHIVE.relative_to(R.ROOT)), 'accepted_timing': False,
            'next': 'STOP: return archive and audit before another budget/cell.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'execute'))
    args = parser.parse_args()
    if args.action == 'prepare':
        report = prepare()
        R.write_new(PLAN, report)
        print(json.dumps({'classification': 'CPU_PREPARATION_COMPLETE_GPU_NOT_RUN',
                          'plan': str(PLAN.relative_to(R.ROOT)), 'plan_sha256': R.sha(PLAN),
                          'command': report['command']}, indent=2))
    else:
        print(json.dumps(execute(), indent=2))

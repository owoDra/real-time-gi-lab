#!/usr/bin/env python3
"""One named frozen M001 PT/dense quality unit: prepare, execute, or independent CPU audit."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tarfile
from dataclasses import dataclass

import audit_first_pt_quality as A

import reference_step as R
from audit_h01_evidence import memory
from score_hdr import score
from score_retained import reference

LADDER = (1, 4, 16, 64, 256, 1024)
BINARY = R.ROOT / 'build/n009/phos-n010-pixel-pt'
BINARY_SHA = 'b96880ba40c8466b4210d9e5af0dad80855c96416496a6c47ad9dc7670d60ea0'
SHADERS = {'pixel-pt': ('n010_pixel_pt.spv', 'e8e03c3e7438159f9b0a4a5d4e4e61e841d054c06aab442d80c613face199069'),
           'dense-rc': ('n010_dense_rc.spv', '78404906bffd1d144e2411970159a4d27a8fff0585293e74d0c645fb805cfb7e')}

@dataclass(frozen=True)
class Case:
    cell: str
    bounce: int
    spp: int
    family: str = 'pixel-pt'

    def __post_init__(self):
        R.target(self.cell, self.bounce)
        R.require(self.family in SHADERS and
                  (self.spp in LADDER if self.family == 'pixel-pt' else self.spp == 1),
                  'unregistered family/budget')
        R.require((self.cell, self.bounce, self.spp, self.family) != ('H01', 2, 1, 'pixel-pt'),
                  'first PT case has original runner/auditor; never repeat it')

    @property
    def tag(self):
        return f'm001-{self.cell.lower()}-b{self.bounce}-{self.family}-n{self.spp}'

    @property
    def PLAN(self):
        return R.ROOT / f'out/{self.tag}-plan.json'

    @property
    def WORK(self):
        return R.target(self.cell, self.bounce) / f'{self.family}-n{self.spp}'

    @property
    def ARCHIVE(self):
        return R.ROOT / f'out/{self.tag}-quality.tar'

    @property
    def SHADER(self):
        return R.ROOT / 'build/n009/shaders' / SHADERS[self.family][0]

    reference = staticmethod(reference)
    memory = staticmethod(memory)


def previous_audit(case):
    if case.family != 'pixel-pt' or case.spp == 1:
        return None
    prior_spp = LADDER[LADDER.index(case.spp) - 1]
    if (case.cell, case.bounce, prior_spp) == ('H01', 2, 1):
        report = A.audit()
    else:
        from audit_quality_step import audit
        report = audit(Case(case.cell, case.bounce, prior_spp))
    R.require(report['quality_evidence_valid'] and report['classification'] == 'QUALITY_FAIL',
              'previous frozen budget must be independently audited QUALITY_FAIL; stop after PASS/incomplete')
    return {'spp': prior_spp, 'result_sha256': report['result_sha256'],
            'classification': report['classification']}


def command(case):
    return ['bash', str(R.ROOT / 'scripts/run_with_vulkan.sh'), str(BINARY),
            '--state', str(R.LANE / f'capture/M001-{case.cell}-hwrt'),
            '--out', str(case.WORK / 'capture'), '--family', case.family,
            '--vertices', str(case.bounce), '--spp', str(case.spp), '--seed', '305419896', '--frames', '1']


def prepare(case):
    state, audit, inputs = R.preflight(case.cell, case.bounce)
    ref = reference(case.cell, case.bounce)
    spec = {'state_directory': str((R.LANE / f'capture/M001-{case.cell}-hwrt').relative_to(R.ROOT)),
            'state_sha256': state['sha256']}
    verification = R.P.verify_reference(ref, case.cell, case.bounce, spec, inputs)
    for p, digest in ((BINARY, BINARY_SHA), (case.SHADER, SHADERS[case.family][1])):
        R.require(R.sha(p) == digest, 'original native binary/shader changed')
    R.require(not case.WORK.exists() and not case.ARCHIVE.exists(), 'existing native output/partial/archive')
    paths = [BINARY, case.SHADER, Path(__file__).resolve(),
             R.ROOT / 'scripts/run_with_vulkan.sh',
             R.ROOT / 'src/research/n010_comparison_readiness/pixel_pt_main.cpp',
             R.ROOT / 'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl',
             Path(R.__file__), R.ROOT / 'scripts/research/lane_m_gi_competitiveness/score_retained.py',
             R.ROOT / 'scripts/research/lane_m_gi_competitiveness/audit_quality_step.py',
             R.ROOT / 'scripts/research/lane_m_gi_competitiveness/audit_first_pt_quality.py',
             R.ROOT / 'scripts/research/lane_m_gi_competitiveness/first_pt_quality.py']
    inputs.update({str(p): R.sha(p) for p in paths})
    return {'schema': 'lane-m-m001-frozen-quality-plan/1', 'command': command(case),
            'scope': {'cell': case.cell, 'bounce': case.bounce, 'spp': case.spp, 'family': case.family},
            'previous_budget_audit': previous_audit(case),
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip(),
            'reference_verification': verification, 'input_sha256': inputs,
            'source_state_audit': audit, 'gpu_executed': False,
            'accepted_timing': False, 'next': 'User authorized agent GPU execution without settings changes; audit before another unit.'}


def execute(case):
    R.require(case.PLAN.is_file(), 'prepare and review exact plan first')
    planned = R.read(case.PLAN)
    current = prepare(case)
    R.require(planned['command'] == current['command']
              and planned['input_sha256'] == current['input_sha256']
              and planned['scope'] == current['scope']
              and planned['previous_budget_audit'] == current['previous_budget_audit'], 'prepared CPU plan drifted')
    case.WORK.mkdir(parents=True)
    R.write_new(case.WORK / 'started.json', {'plan_sha256': R.sha(case.PLAN), 'plan': planned})
    result = {'schema': 'lane-m-m001-frozen-quality-result/1', 'complete': False,
              'plan_sha256': R.sha(case.PLAN), 'command': command(case), 'gpu_executed': True,
              'accepted_timing': False, 'classification': 'FAILED_RETAIN_PARTIAL_NO_RETRY'}

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))

    native = None
    try:
        env = os.environ.copy()
        env.pop('PHOS_N010_CALIBRATION_DOSE', None)
        native = subprocess.Popen(command(case), cwd=R.ROOT, env=env, text=True,
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
            (case.WORK / 'native.stdout.txt').write_text(stdout)
            (case.WORK / 'native.stderr.txt').write_text(stderr)
            raise ValueError('180 second operational timeout; no automatic retry')
        (case.WORK / 'native.stdout.txt').write_text(stdout)
        (case.WORK / 'native.stderr.txt').write_text(stderr)
        result['returncode'] = native.returncode
        R.require(native.returncode == 0, 'native failed; retain original partial outputs')
        for p, digest in planned['input_sha256'].items():
            R.require(R.sha(Path(p)) == digest, 'frozen input changed during execution: ' + p)
        capture = case.WORK / 'capture'
        state = R.Q.L.read_state(capture)
        R.require(state['sha256'] == R.CAPTURE_SHA[case.cell], 'captured physical state differs')
        frames = R.read(capture / 'frames.json')
        R.require((frames['family'], frames['spp'], frames['vertices'], frames['seed'],
                   frames['width'], frames['height'], len(frames['frames'])) ==
                  (case.family, case.spp, case.bounce, 305419896, 320, 180, 1), 'native budget/frame metadata differs')
        for name in ('geometry-state.bin', 'frame-state.bin', 'direct.pfm', 'indirect.pfm', 'total.pfm'):
            R.require(R.sha(capture / name) == R.sha(capture / 'frames/0' / name),
                      'one-frame/native root output differs: ' + name)
        result['memory'] = memory(R.read(capture / 'allocation-ledger.json'))
        ref = reference(case.cell, case.bounce)
        result['quality'] = score(capture, R.read(ref / 'qualification.json'), ref, case.WORK / 'quality.json')
        result['reference_qualification_sha256'] = R.sha(ref / 'qualification.json')
        result['timing'] = {'classification': 'DIAGNOSTIC_UNCALIBRATED_NO_SPEED_CLAIM', 'native': frames}
        result['complete'] = True
        result['classification'] = 'PASS' if result['quality']['pilot_quality_target'] == 'PASS' else 'QUALITY_FAIL'
    except Exception as e:
        result['error'] = str(e)
    result['payload_sha256'] = {str(p.relative_to(case.WORK)): R.sha(p)
                                for p in sorted(case.WORK.rglob('*')) if p.is_file()}
    R.write_new(case.WORK / 'result.json', result)
    with case.ARCHIVE.open('xb') as handle:
        with tarfile.open(fileobj=handle, mode='w') as tar:
            tar.add(case.WORK / 'result.json', arcname='result.json')
            tar.add(case.PLAN, arcname='plan.json')
    return {'classification': result['classification'], 'complete': result['complete'],
            'archive': str(case.ARCHIVE.relative_to(R.ROOT)), 'accepted_timing': False,
            'next': 'STOP: return archive and audit before another budget/cell.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'execute', 'audit'))
    parser.add_argument('--cell', choices=('H01', 'H02', 'H03'), required=True)
    parser.add_argument('--bounce', type=int, choices=(2, 8), required=True)
    parser.add_argument('--spp', type=int, required=True)
    parser.add_argument('--family', choices=tuple(SHADERS), default='pixel-pt')
    args = parser.parse_args()
    case = Case(args.cell, args.bounce, args.spp, args.family)
    if args.action == 'prepare':
        R.require(not case.PLAN.exists(), 'refuse existing CPU plan')
        report = prepare(case)
        R.write_new(case.PLAN, report)
        print(json.dumps({'classification': 'CPU_PREPARATION_COMPLETE_GPU_NOT_RUN',
                          'plan': str(case.PLAN.relative_to(R.ROOT)), 'plan_sha256': R.sha(case.PLAN),
                          'command': report['command']}, indent=2))
    elif args.action == 'execute':
        print(json.dumps(execute(case), indent=2))
    else:
        from audit_quality_step import audit
        report = audit(case)
        output = R.ROOT / f'out/{case.tag}-independent-audit.json'
        R.write_new(output, report)
        print(json.dumps(report, indent=2))

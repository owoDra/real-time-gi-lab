#!/usr/bin/env python3
"""One named M001 vanilla/software capture: CPU plan, native execution, independent intake."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tarfile

import numpy as np
import audit_first_pt_quality as A
import frozen_quality_step as F
import score_hdr as S
from m001_first_capture import CONTRACT

R = F.R
BINARY = R.ROOT / 'build/n009/phos-n010-capture'
BINARY_SHA = 'cc6d7802a45d68d5074a13bbdd5c2cc94310d2f7fa5c303ee890508dae7535ab'
class ReferenceStateMismatch(ValueError):
    pass


REQUIRED = {'allocation-ledger.json', 'geometry-state.bin', 'capture.json', 'frame-state.bin',
            'renderer-timings.jsonl', 'gpu/probe-contributions.bin', 'gpu/direct.pfm',
            'gpu/composite-lookup.bin', 'gpu/indirect.pfm', 'gpu/probe-hits.bin',
            'gpu/hits.bin', 'gpu/total.pfm', 'gpu/probe-work.bin'}

@dataclass(frozen=True)
class Case:
    cell: str
    role: str
    def __post_init__(self):
        R.target(self.cell, 2)
        R.require(self.role in ('vanilla', 'software'), 'unregistered RC role')
    @property
    def tag(self): return f'm001-{self.cell.lower()}-fixed-{self.role}'
    @property
    def work(self): return R.BASE / 'fixed-controls' / f'{self.cell}-{self.role}'
    @property
    def plan(self): return R.ROOT / f'out/{self.tag}-plan.json'
    @property
    def archive(self): return R.ROOT / f'out/{self.tag}-quality.tar'
    @property
    def capture(self): return self.work / 'capture'


def command(c):
    return ['bash', str(R.ROOT / 'scripts/run_with_vulkan.sh'), str(BINARY),
            '--scene', str(R.LANE / f'assets/M001-{c.cell}.gltf'), '--scenario', 'static',
            '--backend', c.role, '--direct-profile', 'ulp4', '--spp', '512', '--out', str(c.capture)]


def references(c):
    inputs, verifications = {}, {}
    for bounce in (2, 8):
        state, _, proof = R.preflight(c.cell, bounce)
        spec = {'state_directory': str((R.LANE / f'capture/M001-{c.cell}-hwrt').relative_to(R.ROOT)),
                'state_sha256': state['sha256']}
        inputs.update(proof)
        verifications[str(bounce)] = R.P.verify_reference(F.reference(c.cell, bounce), c.cell, bounce, spec, inputs)
    return inputs, verifications


def prepare(c):
    R.require(not c.work.exists() and not c.archive.exists(), 'existing RC output/partial/archive')
    inputs, refs = references(c)
    R.require(R.sha(BINARY) == BINARY_SHA, 'original RC binary changed')
    original = R.read(R.LANE / 'result.json')
    R.require(R.sha(CONTRACT) == original['preflight']['contract_sha256'], 'original capture contract changed')
    paths = [BINARY, CONTRACT, Path(__file__).resolve(), Path(A.__file__), Path(F.__file__),
             Path(R.__file__), Path(S.__file__), R.LANE / 'assets/manifest.json',
             R.LANE / f'assets/M001-{c.cell}.gltf', R.LANE / f'assets/M001-{c.cell}.bin',
             R.ROOT / 'scripts/run_with_vulkan.sh',
             R.ROOT / 'scripts/research/n010_comparison_readiness/generate_capture.py']
    paths += sorted((R.ROOT / 'build/n009/shaders').glob('*.spv'))
    R.require(len(paths) >= 40, 'native shader inputs missing')
    inputs.update({str(p): R.sha(p) for p in paths})
    return {'schema': 'lane-m-m001-fixed-rc-plan/1', 'scope': {'cell': c.cell, 'role': c.role},
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip(),
            'command': command(c), 'references': refs, 'input_sha256': inputs,
            'contract': str(CONTRACT), 'gpu_executed': False, 'accepted_timing': False,
            'budget': 'unchanged fixed RC GPU estimator; capture metadata spp512; no GPU retuning'}


def validate_capture(c):
    actual = {str(p.relative_to(c.capture)) for p in c.capture.rglob('*') if p.is_file()}
    expected = REQUIRED | ({'gpu/primary-geometry.bin'} if c.role == 'software' else set())
    R.require(actual == expected, 'missing/extra native RC capture payload')
    meta = R.read(c.capture / 'capture.json')
    R.require((meta['scenario'], meta['backend'], meta['target_state'], meta['frame_id'], meta['spp'],
               meta['width'], meta['height'], meta['triangles'], meta['work_overflow']) ==
              ('static', c.role, False, 1, 512, 320, 180, 1248 if c.cell == 'H03' else 1224, 0),
              'native fixed RC metadata differs')
    state = R.Q.L.read_state(c.capture)
    if state['sha256'] != R.CAPTURE_SHA[c.cell]:
        raise ReferenceStateMismatch('RC control state differs from frozen heldout')
    for bounce in (2, 8):
        R.require(hashlib.sha256(R.Q.scene_for_state(state, bounce).text().encode()).hexdigest()
                  == R.CORRECTED_SHA[c.cell][bounce], 'RC complete physical scene differs')
    return F.memory(R.read(c.capture / 'allocation-ledger.json'))


def execute(c):
    R.require(c.plan.is_file(), 'prepare exact named RC plan first')
    plan = R.read(c.plan)
    current = prepare(c)
    R.require(all(plan[k] == current[k] for k in ('scope', 'command', 'references', 'input_sha256')),
              'prepared RC plan drifted')
    c.work.mkdir(parents=True)
    R.write_new(c.work / 'started.json', {'plan_sha256': R.sha(c.plan), 'plan': plan})
    result = {'schema': 'lane-m-m001-fixed-rc-result/1', 'plan_sha256': R.sha(c.plan),
              'complete': False, 'classification': 'FAILED_RETAIN_PARTIAL_NO_RETRY',
              'gpu_executed': True, 'accepted_timing': False, 'quality': {}}
    def limits(): resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    try:
        env = dict(os.environ)
        for key in ('PHOS_N010_CALIBRATION_DOSE', 'PHOS_N010_CALIBRATION'): env.pop(key, None)
        env['PHOS_N009_CONTRACT'] = str(CONTRACT)
        env['PHOS_N010_MEMORY_LEDGER'] = str(c.capture / 'allocation-ledger.json')
        p = subprocess.Popen(command(c), cwd=R.ROOT, env=env, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True, preexec_fn=limits)
        try:
            stdout, stderr = p.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGTERM)
            try: stdout, stderr = p.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                stdout, stderr = p.communicate()
            (c.work / 'native.stdout.txt').write_text(stdout)
            (c.work / 'native.stderr.txt').write_text(stderr)
            raise ValueError('native180s operational timeout; preserve and stop')
        (c.work / 'native.stdout.txt').write_text(stdout)
        (c.work / 'native.stderr.txt').write_text(stderr)
        result['returncode'] = p.returncode
        R.require(p.returncode == 0, 'native RC failed; no retry')
        R.require(all(R.sha(Path(p)) == h for p, h in plan['input_sha256'].items()), 'RC frozen input changed')
        result['memory'] = validate_capture(c)
        for bounce in (2, 8):
            ref = F.reference(c.cell, bounce)
            result['quality'][str(bounce)] = S.score(c.capture, R.read(ref / 'qualification.json'), ref,
                                                   c.work / f'quality-b{bounce}.json')
        result['complete'] = True
        result['classification'] = 'FIXED_RC_TWO_REFERENCE_TARGETS_SCORED'
    except ReferenceStateMismatch as error:
        result['classification'] = 'REFERENCE_INELIGIBLE_RETAINED_NO_RETRY'
        result['error'] = str(error)
    except Exception as error:
        result['error'] = str(error)
    result['payload_sha256'] = {str(p.relative_to(c.work)): R.sha(p) for p in sorted(c.work.rglob('*')) if p.is_file()}
    R.write_new(c.work / 'result.json', result)
    with c.archive.open('xb') as handle:
        with tarfile.open(fileobj=handle, mode='w') as tar:
            tar.add(c.work / 'result.json', arcname='result.json')
            tar.add(c.plan, arcname='plan.json')
    return {'classification': result['classification'], 'complete': result['complete'],
            'archive': str(c.archive.relative_to(R.ROOT)), 'error': result.get('error'),
            'quality': {b: q['pilot_quality_target'] for b, q in result['quality'].items()}}


def audit(c):
    members = A.archive_members(c.archive)
    R.require(members['plan.json'] == c.plan.read_bytes()
              and members['result.json'] == (c.work / 'result.json').read_bytes(), 'RC archive/local mismatch')
    plan, result = R.read(c.plan), R.read(c.work / 'result.json')
    R.require(result['plan_sha256'] == R.sha(c.plan) and result['accepted_timing'] is False
              and plan['scope'] == {'cell': c.cell, 'role': c.role} and plan['command'] == command(c), 'RC plan scope mismatch')
    A.validate_inventory(c.work, result['payload_sha256'])
    R.require(R.read(c.work / 'started.json') == {'plan_sha256': R.sha(c.plan), 'plan': plan}, 'RC started mismatch')
    if not result['complete']:
        R.require(result['classification'] in ('FAILED_RETAIN_PARTIAL_NO_RETRY', 'REFERENCE_INELIGIBLE_RETAINED_NO_RETRY'), 'incomplete RC classified as complete')
        return {'classification': 'REFERENCE_INELIGIBLE' if result['classification'].startswith('REFERENCE_INELIGIBLE') else 'OPERATIONAL_FAILURE_RETAINED_NOT_QUALITY_DECISION',
                'quality_evidence_valid': False, 'error': result.get('error'), 'accepted_timing': False}
    R.require(result['gpu_executed'] is True and result['returncode'] == 0, 'native success absent')
    inputs, refs = references(c)
    R.require(refs == plan['references'], 'RC reference qualification drifted')
    for path, h in plan['input_sha256'].items(): R.require(R.sha(Path(path)) == h, 'RC pinned input drifted')
    source = plan['source_commit']
    R.require(len(source) == 40 and all(x in '0123456789abcdef' for x in source)
              and subprocess.run(['git', 'merge-base', '--is-ancestor', source, 'HEAD'], cwd=R.ROOT).returncode == 0,
              'RC plan source not reachable')
    rel = str(Path(__file__).resolve().relative_to(R.ROOT))
    R.require(subprocess.check_output(['git', 'show', source + ':' + rel], cwd=R.ROOT) == Path(__file__).read_bytes(),
              'RC driver differs from committed capture source')
    mem = validate_capture(c)
    R.require(mem == result['memory'], 'RC independent owned ledger mismatch')
    rows = []
    for bounce in (2, 8):
        q = result['quality'][str(bounce)]
        ref = F.reference(c.cell, bounce)
        qual = R.read(ref / 'qualification.json')
        n = qual['levels'][-1]['spp']
        means = np.mean([R.Q.L.read_sidecar(ref / f'o.n{n}.s{i}.f64')['mean'] for i in range(4)], axis=0)
        R.require(q['cell'] == c.cell and q['transport'] == f'T_B{bounce}'
                  and q['state_sha256'] == R.CAPTURE_SHA[c.cell] and q['scoring_exclusions'] == 0
                  and q['complete_oracle_scene_sha256'] == R.CORRECTED_SHA[c.cell][bounce]
                  and q['state_bytes_equal'] and q['complete_physical_scene_bytes_equal'], 'RC quality scope differs')
        components = {}
        for component in ('direct', 'indirect', 'total'):
            image = c.capture / 'gpu' / f'{component}.pfm'
            R.require(R.sha(image) == q['capture_payload_sha256'][f'{component}.pfm'], 'RC scored image changed')
            gpu = R.Q.L.read_pfm(image) @ S.LUMA
            expected = means[..., R.Q.L.COMPONENTS.index(component), :] @ S.LUMA
            components[component] = S.metrics(gpu, expected)
            R.require(components[component] == q['components'][component]
                      and np.array_equal(np.load(c.work / f'quality-b{bounce}.{component}.error.npy', allow_pickle=False), gpu - expected),
                      'RC metric/error map independent replay differs')
        passed = A.quality_pass(components)
        R.require(q['pilot_quality_target'] == ('PASS' if passed else 'FAIL'), 'RC classifier differs')
        rows.append({'cell': c.cell, 'role': c.role, 'transport': f'T_B{bounce}',
                     'classification': 'PASS' if passed else 'QUALITY_FAIL', 'components': components,
                     'finite_depth_equivalent': False})
    return {'schema': 'lane-m-m001-fixed-rc-independent-audit/1', 'quality_evidence_valid': True,
            'result_sha256': R.sha(c.work / 'result.json'), 'plan_sha256': R.sha(c.plan),
            'archive_sha256': R.sha(c.archive), 'raw_payloads_rehashed': len(result['payload_sha256']),
            'references': refs, 'memory': mem, 'rows': rows, 'accepted_timing': False,
            'gpu_executed_by_auditor': False}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('prepare', 'execute', 'audit'))
    ap.add_argument('--cell', required=True, choices=('H01', 'H02', 'H03'))
    ap.add_argument('--role', required=True, choices=('vanilla', 'software'))
    a = ap.parse_args(); c = Case(a.cell, a.role)
    if a.action == 'prepare':
        R.require(not c.plan.exists(), 'refuse existing RC CPU plan')
        report = prepare(c); R.write_new(c.plan, report)
        print(json.dumps({'plan': str(c.plan), 'sha256': R.sha(c.plan), 'command': report['command']}, indent=2))
    elif a.action == 'execute': print(json.dumps(execute(c), indent=2))
    else:
        output = R.ROOT / f'out/{c.tag}-independent-audit.json'
        R.require(not output.exists(), 'refuse existing RC audit')
        report = audit(c); R.write_new(output, report)
        print(json.dumps(report, indent=2))

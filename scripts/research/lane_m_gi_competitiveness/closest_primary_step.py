#!/usr/bin/env python3
"""013 one explicit acquisition: CPU plan, raw capture, then separate CPU audit."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tarfile

import closest_primary as C
import closest_primary_cases as K
import reference_step as R

RESULTS = C.ROOT / 'research/lanes/lane-m-gi-competitiveness/results'
WORK = K.BASE / 'm001-closest-primary-validation-v1'
SCORES = K.BASE / 'm001-closest-primary-validation-scores-v1'
BUILD = K.BASE / 'm001-closest-primary-build-v3'
PROCESS_GATE = RESULTS / '093-closest-primary-process-cpu-preparation.json'


@dataclass(frozen=True)
class Paths:
    case: K.Case

    @property
    def work(self): return WORK / self.case.name
    @property
    def capture(self): return self.work / 'capture'
    @property
    def scores(self): return SCORES / self.case.name
    @property
    def plan(self): return C.ROOT / f'out/m001-closest-primary-{self.case.name}-plan.json'
    @property
    def archive(self): return C.ROOT / f'out/m001-closest-primary-{self.case.name}.tar'


def rehash(inputs):
    for name, digest in inputs.items():
        R.require(C.sha(Path(name)) == digest, '013 input drift: ' + name)


def build_and_cpu(inputs):
    for name in ('086-closest-primary-isolated-cpu-build.json',
                 '087-closest-primary-cpu-tests-and-native-contracts.json',
                 '090-closest-primary-all-pixel-metrics-cpu-tests.json'):
        path = RESULTS / name
        inputs[str(path)] = C.sha(path)
    proof = R.read(RESULTS / '086-closest-primary-isolated-cpu-build.json')
    R.require(proof['complete'] and not proof['gpu_executed']
              and proof['host_translation_units_recompiled'] == 13, '013 CPU build unavailable')
    inputs.update(proof['input_sha256'])
    inputs.update(proof['dependency_sha256'])
    binary = Path(proof['executable'])
    inputs[str(binary)] = proof['executable_sha256']
    inputs.update({str(BUILD / 'shaders' / name): h for name, h in proof['private_shader_sha256'].items()})
    raw_build = BUILD / 'result.json'
    inputs[str(raw_build)] = proof['raw_receipt_sha256']
    cpu = R.read(RESULTS / '087-closest-primary-cpu-tests-and-native-contracts.json')
    R.require(cpu['current_actual_cpu_tests'] == 12 and cpu['actual_native_cpu_contracts'] == 8
              and cpu['native_contract_record']['complete'], '013 CPU contract gates incomplete')
    for item in cpu['test_receipts']:
        inputs[item['receipt']] = item['receipt_sha256']
        R.require(item['record']['returncode'] == 0, '013 prior CPU test failed')
    # Bind current successful source/case suite; earlier successful source
    # versions remain provenance, rather than current-source assertions.
    inputs.update(cpu['test_receipts'][-1]['record']['input_sha256'])
    native = cpu['native_contract_record']
    inputs[cpu['native_contract_receipt']] = cpu['native_contract_receipt_sha256']
    inputs.update({str(Path(cpu['native_contract_receipt']).parent / p): h
                   for p, h in native['payload_sha256'].items()})
    R.require([x['name'] for x in native['rows']] == [K.Case(*x).name for x in K.TARGETS]
              and all(x['pass_'] and x['returncode'] != 0 for x in native['rows']), '013 native CPU cases differ')
    metrics = R.read(RESULTS / '090-closest-primary-all-pixel-metrics-cpu-tests.json')
    R.require(metrics['returncode'] == 0 and metrics['actual_new_metric_tests'] == 16,
              '013 all-pixel CPU tests unavailable')
    inputs[metrics['raw_receipt']] = metrics['raw_receipt_sha256']
    inputs.update(metrics['input_sha256'])
    rehash(inputs)
    return binary


def process_gate(inputs):
    R.require(PROCESS_GATE.is_file(), '013 process/independent-auditor CPU gate not yet admitted')
    gate = R.read(PROCESS_GATE)
    R.require(gate['all_pass'] is True and gate['gpu_executed'] is False,
              '013 process CPU evidence failed')
    inputs[str(PROCESS_GATE)] = C.sha(PROCESS_GATE)
    inputs[gate['raw_receipt']] = gate['raw_receipt_sha256']
    inputs.update(gate['input_sha256'])
    rehash(inputs)


def reference_inputs(case, inputs):
    from score_retained import reference
    refs = {}
    if case.cell == 'C1':
        historical = C.ROOT / 'research/lanes/n010-comparison-readiness/results/011-rc-correctness-pilot.json'
        row = next(x for x in R.read(historical)['rows'] if (x['cell'], x['backend']) == ('C1', case.backend))
        capture = Path(row['command'][row['command'].index('--out') + 1])
        for name, digest in row['payload_sha256'].items():
            inputs[str(capture / name)] = digest
        inputs[str(historical)] = C.sha(historical)
        state = R.Q.L.read_state(capture)
        ref = C.ROOT / 'out/research/n010-comparison-readiness/references-v1/C1_T_B2'
        R.P.physical_proof(inputs)
        spec = dict(state_directory=str(capture.relative_to(C.ROOT)), state_sha256=state['sha256'])
        proof = R.P.verify_reference(ref, 'C1', 2, spec, inputs)
        R.require(proof['levels'] == [8192, 16384, 32768], 'Original C1 reference prefix differs')
        refs['2'] = proof
    else:
        for depth in (2, 8):
            state, _, original_inputs = R.preflight(case.cell, depth)
            inputs.update(original_inputs)
            spec = dict(state_directory=str((R.LANE / f'capture/M001-{case.cell}-hwrt').relative_to(C.ROOT)),
                        state_sha256=state['sha256'])
            proof = R.P.verify_reference(reference(case.cell, depth), case.cell, depth, spec, inputs)
            R.require(proof['levels'] == [8192, 16384], 'Original M001 reference prefix differs')
            refs[str(depth)] = proof
    rehash(inputs)
    return refs


def next_case(reports):
    names = [K.Case(*x).name for x in K.TARGETS]
    R.require(set(reports) <= set(names), 'Unregistered013history')
    for index, pair in enumerate(K.TARGETS):
        case = K.Case(*pair)
        if case.name not in reports:
            R.require(not (set(names[index+1:]) & set(reports)), '013 evidence after a missing case')
            return case
        row = reports[case.name]
        R.require(row['correctness_evidence_valid'] is True and row['classification'] == 'PASS',
                  '013 STOP: invalid, operational or correctness failure; never retry/advance')
    return None


def history():
    import closest_primary_audit as A
    reports = {}
    for pair in K.TARGETS:
        case = K.Case(*pair)
        p = Paths(case)
        if p.work.exists() or p.archive.exists() or p.scores.exists():
            R.require(case == next_case(reports), '013 history order differs')
            R.require((p.scores / 'result.json').is_file(), '013 terminal independent audit required before selection')
            reports[case.name] = A.audit(case)
    next_case(reports)
    return reports


def prepare(case):
    p = Paths(case)
    R.require(not p.work.exists() and not p.archive.exists() and not p.scores.exists(), 'Existing013output/partial/archive/audit; no overwrite')
    reports = history()
    R.require(case == next_case(reports), 'Not the next registered013case')
    R.require(subprocess.check_output(['git', 'branch', '--show-current'], cwd=C.ROOT, text=True).strip()
              == 'research-lane-m-gi-competitiveness', 'Wrong research branch')
    R.require(not subprocess.check_output(['git', 'diff', 'HEAD', '--', 'scripts', 'src', 'shaders'], cwd=C.ROOT),
              'Commit executable source before013preparation')
    R.quiet()
    inputs = {}
    binary = build_and_cpu(inputs)
    process_gate(inputs)
    refs = reference_inputs(case, inputs)
    tracked = subprocess.check_output(['git', 'ls-files', '--', 'scripts/research'], cwd=C.ROOT, text=True).splitlines()
    paths = [C.ROOT / name for name in tracked if name.endswith('.py')]
    paths += [K.CONTRACT, C.ROOT / 'scripts/run_with_vulkan.sh']
    paths += [C.ROOT / 'research/lanes/lane-m-gi-competitiveness/experiments' / name for name in
              ('013-closest-primary-development-validation.md', '014-closest-primary-pre-acquisition-numerical-clarification.md')]
    cmd = K.command(case, binary, p.capture)
    scene = Path(cmd[cmd.index('--scene') + 1])
    paths.append(scene)
    # Resolve every external scene buffer from the exact source asset; textures
    # are not consumed by this BF-P geometry loader.
    for buffer in R.read(scene)['buffers']:
        uri = buffer['uri']
        R.require(not uri.startswith('data:') and not Path(uri).is_absolute() and '..' not in Path(uri).parts,
                  'Unexpected physical scene buffer URI')
        paths.append(scene.parent / uri)
    inputs.update({str(path): C.sha(path) for path in paths})
    R.require(shutil.disk_usage(C.ROOT / 'out').free >= 16*1024**3, '013 requires16GiB free disk')
    plan = dict(schema='m001-closest-primary-plan/1', source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=C.ROOT, text=True).strip(),
                scope=dict(cell=case.cell, backend=case.backend), command=cmd, input_sha256=inputs,
                reference_verification=refs, previous_audits={name: r['derived_record_sha256'] for name, r in reports.items()},
                contract=str(K.CONTRACT), gpu_executed=False, accepted_timing=False)
    R.require(len(json.dumps(plan).encode()) <= 1024**2, 'Compact013proof plan too large')
    return plan


def run_native(command, env, stdout_path, stderr_path, timeout=180):
    def limits(): resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    native = subprocess.Popen(command, cwd=C.ROOT, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True, preexec_fn=limits)
    timed_out = False
    try:
        stdout, stderr = native.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(native.pid, signal.SIGTERM)
        try:
            stdout, stderr = native.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(native.pid, signal.SIGKILL)
            stdout, stderr = native.communicate()
    finally:
        # communicate drains before writing; all partial output survives timeout.
        if 'stdout' in locals(): stdout_path.write_text(stdout)
        if 'stderr' in locals(): stderr_path.write_text(stderr)
    return dict(returncode=native.returncode, timed_out=timed_out)


def execute(case):
    p = Paths(case)
    R.require(p.plan.is_file(), 'Freeze CPU plan before013execution')
    plan = R.read(p.plan)
    current = prepare(case)
    for key in ('scope', 'command', 'input_sha256', 'reference_verification', 'previous_audits', 'contract'):
        R.require(plan[key] == current[key], 'Prepared013plan drift: ' + key)
    p.work.mkdir(parents=True)
    R.write_new(p.work / 'started.json', dict(plan_sha256=C.sha(p.plan), plan=plan))
    result = dict(schema='m001-closest-primary-result/1', complete=False, gpu_executed=True,
                  classification='OPERATIONAL_FAILURE_RETAINED_STOP', plan_sha256=C.sha(p.plan),
                  command=plan['command'], accepted_timing=False)
    try:
        env = dict(os.environ)
        for key in ('PHOS_N010_CALIBRATION', 'PHOS_N010_CALIBRATION_DOSE', 'PHOS_N010_DIRECT_PROFILE'):
            env.pop(key, None)
        env.update(PHOS_N009_CONTRACT=plan['contract'], PHOS_N010_MEMORY_LEDGER=str(p.capture / 'allocation-ledger.json'))
        result.update(run_native(plan['command'], env, p.work / 'native.stdout.txt', p.work / 'native.stderr.txt'))
        R.require(not result['timed_out'] and result['returncode'] == 0, 'Native013operational failure; stop')
        rehash(plan['input_sha256'])
        result.update(complete=True, classification='RAW_CAPTURE_RETAINED_INDEPENDENT_AUDIT_REQUIRED')
    except Exception as exc:
        result['error'] = repr(exc)
    result['payload_sha256'] = {str(path.relative_to(p.work)): C.sha(path)
                               for path in sorted(p.work.rglob('*')) if path.is_file()}
    R.write_new(p.work / 'result.json', result)
    with p.archive.open('xb') as handle:
        with tarfile.open(fileobj=handle, mode='w') as tar:
            tar.add(p.plan, arcname='plan.json')
            tar.add(p.work / 'result.json', arcname='result.json')
    return dict(complete=result['complete'], classification=result['classification'], archive=str(p.archive),
                next='STOP; independent CPU terminal audit before another named case')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['prepare', 'execute'])
    ap.add_argument('--cell', required=True, choices=['C1', 'H01', 'H02', 'H03'])
    ap.add_argument('--backend', required=True, choices=['hwrt', 'software'])
    args = ap.parse_args()
    case = K.Case(args.cell, args.backend)
    if args.action == 'prepare':
        p = Paths(case)
        R.require(not p.plan.exists(), 'Existing013plan; never overwrite')
        plan = prepare(case)
        R.write_new(p.plan, plan)
        print(json.dumps(dict(plan=str(p.plan), command=plan['command'], inputs=len(plan['input_sha256']), gpu_executed=False), indent=2))
    else:
        print(json.dumps(execute(case), indent=2))

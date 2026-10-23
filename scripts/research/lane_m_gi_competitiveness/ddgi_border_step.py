#!/usr/bin/env python3
"""011 one named corrected DDGI process. CPU plan, explicit execute, CPU audit."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tarfile

import ddgi_border_cases as F
import ddgi_quality_step as Q
from audit_quality_step import validate_inventory

R = F.R
CPU_RECEIPTS = (
    F.BUILD / 'result.json', F.SHADERS / 'result.json',
    F.BASE / 'm001-ddgi-border-correction-tests-v1/result.json',
    F.BASE / 'm001-ddgi-border-compiler-context-tests-v1/result.json',
    F.BASE / 'm001-ddgi-border-input-tests-v1/result.json',
    F.CPU / 'result.json',
    F.BASE / 'm001-ddgi-border-process-tests-v1/result.json',
)


def validate_previous(case, reports):
    """A missing/failed/extra predecessor cannot authorize another process."""
    i = F.CASES.index(case)
    expected = [c.name for c in F.CASES[:i]]
    R.require(list(reports) == expected, '011 predecessor inventory/order differs')
    R.require(all(r.get('semantic_pass') is True and r.get('classification') == 'BORDER_CONTROL_PASS' for r in reports.values()),
              '011 predecessor failed/ineligible; stop')


def tracked_sources():
    return [Path(__file__).resolve(), Path(__file__).with_name('ddgi_border_requalification_audit.py'),
            Path(F.__file__).resolve(), Path(__file__).with_name('ddgi_border_copy_check.py'),
            Path(__file__).with_name('ddgi_border_overlay.py'), Path(__file__).with_name('test_ddgi_border_step.py'), F.PROTOCOL]


def prepare(case):
    R.require(not case.work.exists() and not case.archive.exists(), 'Existing011 work/partial/tar; never retry')
    i = F.CASES.index(case)
    R.require(not any(c.work.exists() or c.archive.exists() for c in F.CASES[i + 1:]), '011 out-of-order evidence exists')
    import ddgi_border_requalification_audit as A
    previous = {c.name: A.audit(c) for c in F.CASES[:i]}
    validate_previous(case, previous)
    inputs = {}
    inputs.update(A.old_identity_inputs(case))
    for c in F.CASES[:i]:
        inputs[str(c.plan)] = R.sha(c.plan)
        inputs[str(c.archive)] = R.sha(c.archive)
        inputs[str(c.work / 'result.json')] = R.sha(c.work / 'result.json')
        inputs.update({str(c.work / p): h for p, h in R.read(c.work / 'result.json')['payload_sha256'].items()})
    references = Q.verify_references(inputs)
    dynamic_states = F.D.audit_states()
    dynamic_direct = {kind: F.D.audit_oracle(kind) for kind in ('light', 'geometry')}
    for receipt in CPU_RECEIPTS:
        report = R.read(receipt)
        R.require(report['all_pass'] and report['gpu_executed'] is False, '011 CPU preparation failed/not CPU-only: ' + str(receipt))
        inputs[str(receipt)] = R.sha(receipt)
        for field in ('input_sha256', 'compiled_dependency_sha256'):
            for path, h in report.get(field, {}).items():
                R.require(R.sha(Path(path)) == h, '011 CPU dependency drift: ' + path)
                inputs[path] = h
        if 'payload_sha256' in report:
            validate_inventory(receipt.parent, report['payload_sha256'])
            for path, h in report['payload_sha256'].items():
                inputs[str(receipt.parent / path)] = h
    # All20 actual native CPU contracts were completed before the first GPU unit.
    cpu_manifest = R.read(F.CPU / 'result.json')
    R.require([x['name'] for x in cpu_manifest['rows']] == [c.name for c in F.CASES], '011 native CPU manifest incomplete')
    for c in F.CASES:
        cp = F.CPU / c.name / 'result.json'
        R.require(R.sha(cp) == next(x['sha256'] for x in cpu_manifest['rows'] if x['name'] == c.name), '011 native CPU receipt changed')
        F.cpu_contract(c)  # Read-only rehash; refuses existing failed/drifted receipt.
        inputs[str(cp)] = R.sha(cp)
    dynamic_root = F.D.WORK
    for p in sorted(dynamic_root.rglob('*')):
        if p.is_file():
            inputs[str(p)] = R.sha(p)
    # Original adapter/reduction dependency identities are still those actually compiled.
    for p, h in R.read(F.S.paths('direct')[0])['input_sha256'].items():
        R.require(R.sha(Path(p)) == h, 'Original adapter/SDK/physical pin drift: ' + p)
        inputs[p] = h
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip()
    for p in tracked_sources():
        raw = subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(R.ROOT))], cwd=R.ROOT)
        R.require(raw == p.read_bytes(), 'Commit011 runner/auditor/test/protocol before prepare')
        inputs[str(p)] = R.sha(p)
    inputs[str(R.ROOT / 'scripts/run_with_vulkan.sh')] = R.sha(R.ROOT / 'scripts/run_with_vulkan.sh')
    R.require(shutil.disk_usage(R.ROOT / 'out').free >= 16 * 1024**3, '011 free disk below16GiB')
    return dict(schema='m001-ddgi-separated-border-control-plan/1', name=case.name, case=asdict(case), command=F.command(case),
                source_commit=commit, input_sha256=inputs, reference_verification=references, dynamic_states=dynamic_states,
                dynamic_direct_controls=dynamic_direct,
                previous_control_audits={n: dict(result_sha256=r['result_sha256'], archive_sha256=r['archive_sha256']) for n, r in previous.items()},
                gpu_executed=False, quality_scoring=False, accepted_timing=False)


def execute(case):
    R.require(case.plan.is_file(), 'Prepare exact011 CPU plan first')
    frozen = R.read(case.plan)
    current = prepare(case)
    for key in ('name', 'case', 'command', 'input_sha256', 'reference_verification', 'dynamic_states', 'dynamic_direct_controls', 'previous_control_audits'):
        R.require(frozen[key] == current[key], 'Prepared011 plan drift: ' + key)
    case.work.mkdir(parents=True)
    R.write_new(case.work / 'started.json', dict(plan_sha256=R.sha(case.plan), plan=frozen))
    result = dict(schema='m001-ddgi-separated-border-control-result/1', name=case.name, command=F.command(case),
                  plan_sha256=R.sha(case.plan), complete=False, gpu_executed=False, accepted_timing=False,
                  semantic_admission=False, quality_admission=False, classification='OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY')
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    native = None
    try:
        native = subprocess.Popen(F.command(case), cwd=R.ROOT, env=dict(os.environ), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, start_new_session=True, preexec_fn=limits, text=True)
        result['gpu_executed'] = True
        try:
            stdout, stderr = native.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(native.pid, signal.SIGTERM)
            try:
                stdout, stderr = native.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(native.pid, signal.SIGKILL)
                stdout, stderr = native.communicate()
            (case.work / 'native.stdout.txt').write_text(stdout)
            (case.work / 'native.stderr.txt').write_text(stderr)
            raise ValueError('011180second timeout; retain partial and stop, never retry')
        (case.work / 'native.stdout.txt').write_text(stdout)
        (case.work / 'native.stderr.txt').write_text(stderr)
        result['returncode'] = native.returncode
        R.require(native.returncode == 0 and R.read(case.work / 'capture/complete.json')['capture_complete'], '011 native incomplete')
        result.update(complete=True, classification='RAW_BORDER_CONTROL_RETAINED_AUDIT_REQUIRED')
    except Exception as error:
        result['error'] = str(error)
    result['payload_sha256'] = {str(p.relative_to(case.work)): R.sha(p) for p in sorted(case.work.rglob('*')) if p.is_file()}
    R.write_new(case.work / 'result.json', result)
    with case.archive.open('xb') as f:
        with tarfile.open(fileobj=f, mode='w') as t:
            t.add(case.plan, arcname='plan.json')
            t.add(case.work / 'result.json', arcname='result.json')
    return dict(name=case.name, complete=result['complete'], classification=result['classification'], archive=str(case.archive),
                next='STOP; independent terminal CPU audit before another explicitly named GPU process')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('prepare', 'execute', 'audit'))
    ap.add_argument('--name', choices=[c.name for c in F.CASES], required=True)
    args = ap.parse_args()
    case = F.get_case(args.name)
    if args.action == 'prepare':
        report = prepare(case)
        R.write_new(case.plan, report)
        print(json.dumps(dict(command=report['command'], plan=str(case.plan), gpu_executed=False), indent=2))
    elif args.action == 'execute':
        print(json.dumps(execute(case), indent=2))
    else:
        import ddgi_border_requalification_audit as A
        print(json.dumps(A.audit(case), indent=2))

#!/usr/bin/env python3
"""012 CPU plan, one explicit corrected DDGI acquisition, independent CPU score."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tarfile

import ddgi_corrected_quality_cases as C
import ddgi_quality_step as Old
from audit_quality_step import archive_members, validate_inventory

R, B = C.R, C.B
ROOT, PROTOCOL = C.ROOT, C.PROTOCOL
Case, TARGETS, BUDGETS = C.Case, C.TARGETS, C.BUDGETS
command, cpu_contract, verify_references = C.command, C.cpu_contract, Old.verify_references
TESTS = B.BASE / 'm001-ddgi-border-quality-process-tests-v1'


def next_case(reports):
    """Same010 first-PASS order; failed/invalid evidence cannot escalate."""
    consumed = set()
    for cell, depth in TARGETS:
        for rung in range(3):
            case = Case(cell, depth, rung)
            if case.name not in reports:
                R.require(set(reports) == consumed, 'Out-of-order/extra012 acquisition')
                return case
            row = reports[case.name]
            consumed.add(case.name)
            R.require(row.get('quality_evidence_valid') is True and row.get('classification') in ('PASS', 'QUALITY_FAIL'),
                      'Invalid/operational012 result stops cohort; no escalation')
            if row['classification'] == 'PASS':
                break
    R.require(set(reports) == consumed, '012 acquisition after first PASS or exhausted cohort')
    return None


def source_paths():
    return [Path(__file__).resolve(), Path(C.__file__).resolve(), PROTOCOL,
            Path(__file__).with_name('ddgi_corrected_quality_audit.py'),
            Path(__file__).with_name('test_ddgi_corrected_quality_step.py'),
            Path(__file__).with_name('test_ddgi_corrected_quality_cases.py')]


def validate_qualification_proof(proof):
    R.require(proof['registered_requalification_complete'] is True and proof['all_existing_evidence_valid'] is True
              and proof['controls_pass'] == proof['native_acquisitions'] == proof['controls_required'] == 20
              and [row['name'] for row in proof['rows']] == [c.name for c in B.CASES], 'Incomplete/failed011 replay')
    R.require(all(row['audit']['semantic_pass'] is True and row['audit']['classification'] == 'BORDER_CONTROL_PASS'
                  for row in proof['rows']), 'Failed011 row blocks012')


def requalification(inputs):
    """Rehash complete20controls against their committed full independent replay.

    Scientific predicates were independently recomputed in that replay. This
    admission rehashes every raw byte, source/input, plan and saved audit without
    redundantly recomputing identical reference statistics twenty times.
    """
    index = R.ROOT / 'research/lanes/lane-m-gi-competitiveness/results/index.json'
    entry = R.read(index)['experiments'][0]
    R.require(entry.get('ddgi_border_runtime_requalified') is True, '011 full requalification not admitted')
    replay = index.parent.parent / entry['ddgi_border_controls_raw_replay']
    outcome = index.parent.parent / entry['ddgi_border_controls_outcome']
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip()
    for p in (replay, outcome):
        R.require(subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(R.ROOT))], cwd=R.ROOT)
                  == p.read_bytes(), 'Commit complete011 replay/outcome before012')
        inputs[str(p)] = R.sha(p)
    proof = R.read(replay)
    validate_qualification_proof(proof)
    cache = {}
    def checked(path, expected):
        path = Path(path)
        key = str(path)
        if key not in cache:
            cache[key] = R.sha(path)
        R.require(cache[key] == expected, '011 evidence/input drift: ' + key)
    for case, row in zip(B.CASES, proof['rows']):
        audit = B.BASE / 'm001-ddgi-border-audits-v1' / case.name / 'result.json'
        checked(audit, row['audit_sha256'])
        saved = R.read(audit)
        R.require(saved == row['audit'] and saved['semantic_pass'] is True
                  and saved['classification'] == 'BORDER_CONTROL_PASS', '011 terminal audit differs')
        inputs[str(audit)] = row['audit_sha256']
        checked(case.archive, saved['archive_sha256'])
        checked(case.work / 'result.json', saved['result_sha256'])
        members = archive_members(case.archive)
        R.require(members['plan.json'] == case.plan.read_bytes()
                  and members['result.json'] == (case.work / 'result.json').read_bytes(), '011 proof archive differs')
        result, plan = R.read(case.work / 'result.json'), R.read(case.plan)
        checked(case.plan, result['plan_sha256'])
        validate_inventory(case.work, result['payload_sha256'])
        for path, expected in plan['input_sha256'].items():
            checked(path, expected)
        R.require(subprocess.run(['git', 'merge-base', '--is-ancestor', plan['source_commit'], 'HEAD'],
                                cwd=R.ROOT, capture_output=True).returncode == 0, '011 source no longer reachable')
    return dict(replay=str(replay), replay_sha256=R.sha(replay), outcome=str(outcome), outcome_sha256=R.sha(outcome),
                controls=20, all_raw_payloads_rehashed=True, all_original_plan_inputs_rehashed=True,
                scope='Committed independent full replay predicates, preserved by exact complete evidence identity')


def history(case):
    import ddgi_corrected_quality_audit as A
    reports = {}
    for cell, depth in TARGETS:
        for rung in range(3):
            prior = Case(cell, depth, rung)
            if prior.work.exists() or prior.archive.exists():
                reports[prior.name] = A.audit(prior)
    R.require(next_case(reports) == case, 'Name exactly next012 acquisition')
    return {n: {k: r[k] for k in ('classification', 'quality_evidence_valid', 'result_sha256', 'derived_record_sha256')}
            for n, r in reports.items()}


def prepare(case):
    R.require(not case.work.exists() and not case.archive.exists(), 'Existing012 work/partial/tar; never retry')
    R.require(shutil.disk_usage(R.ROOT / 'out').free >= 16 * 1024**3, '012 free disk below16GiB')
    inputs = {}
    qualification = requalification(inputs)
    previous = history(case)
    refs = verify_references(inputs)
    # Build/source dependency manifests, shader payloads, and CPU-only tests.
    receipts = (B.BUILD / 'result.json', B.SHADERS / 'result.json', C.CPU / 'result.json',
                B.BASE / 'm001-ddgi-border-quality-input-tests-v1/result.json', TESTS / 'result.json')
    for p in receipts:
        report = R.read(p)
        R.require(report['all_pass'] is True and report['gpu_executed'] is False, '012 CPU preparation failed: ' + str(p))
        inputs[str(p)] = R.sha(p)
        for field in ('input_sha256', 'compiled_dependency_sha256'):
            for path, expected in report.get(field, {}).items():
                R.require(R.sha(Path(path)) == expected, '012 CPU dependency drift: ' + path)
                inputs[path] = expected
        if 'payload_sha256' in report:
            validate_inventory(p.parent, report['payload_sha256'])
            inputs.update({str(p.parent / path): h for path, h in report['payload_sha256'].items()})
    manifest = R.read(C.CPU / 'result.json')
    R.require([row['name'] for row in manifest['rows']] == [Case(c, d, q).name for c, d in TARGETS for q in range(3)],
              '012 CPU contract manifest incomplete/order differs')
    for cell, depth in TARGETS:
        for rung in range(3):
            c = Case(cell, depth, rung)
            current = cpu_contract(c)
            R.require(dict(name=c.name, **current) == next(row for row in manifest['rows'] if row['name'] == c.name),
                      '012 matching actual CPU contract changed')
            inputs[current['path']] = current['sha256']
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip()
    for p in source_paths():
        R.require(subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(R.ROOT))], cwd=R.ROOT)
                  == p.read_bytes(), 'Commit012 runner/auditor/tests before preparation')
        inputs[str(p)] = R.sha(p)
    # Bind every Python dependency in this research tree, including imported
    # original immutable scorers/protocol helpers; no implicit mutable imports.
    for p in sorted((R.ROOT / 'scripts/research').rglob('*.py')):
        relative = str(p.relative_to(R.ROOT))
        tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', relative], cwd=R.ROOT, capture_output=True)
        if tracked.returncode == 0:
            committed = subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=R.ROOT)
            R.require(hashlib.sha256(committed).hexdigest() == R.sha(p), '012 committed dependency differs: ' + relative)
            inputs[str(p)] = R.sha(p)
    return dict(schema='m001-ddgi-corrected-quality-plan/1', scope=case.scope, source_commit=commit,
                command=command(case), input_sha256=inputs, reference_verification=refs,
                previous_quality_audits=previous, native_cpu_contract=cpu_contract(case),
                requalification=qualification, gpu_executed=False, accepted_timing=False, unblinded_cohort=True)


def execute(case):
    R.require(case.plan.is_file(), 'Prepare exact012 CPU plan first')
    plan = R.read(case.plan)
    now = prepare(case)
    for key in ('scope', 'command', 'input_sha256', 'reference_verification', 'previous_quality_audits', 'native_cpu_contract', 'requalification'):
        R.require(plan[key] == now[key], 'Prepared012 plan drift: ' + key)
    case.work.mkdir(parents=True)
    R.write_new(case.work / 'started.json', dict(plan_sha256=R.sha(case.plan), plan=plan))
    result = dict(schema='m001-ddgi-corrected-quality-result/1', scope=case.scope, command=command(case),
                  plan_sha256=R.sha(case.plan), complete=False, gpu_executed=False, accepted_timing=False,
                  quality_admission=False, classification='OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY')
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    try:
        native = subprocess.Popen(command(case), cwd=R.ROOT, env=dict(os.environ), stdout=subprocess.PIPE,
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
            raise ValueError('012180s timeout; retain partial, no retry/escalation')
        (case.work / 'native.stdout.txt').write_text(stdout)
        (case.work / 'native.stderr.txt').write_text(stderr)
        result['returncode'] = native.returncode
        R.require(native.returncode == 0 and R.read(case.work / 'capture/complete.json')['capture_complete'], '012 native incomplete')
        for p, expected in plan['input_sha256'].items():
            R.require(R.sha(Path(p)) == expected, '012 input drift during execution: ' + p)
        result.update(complete=True, classification='RAW_QUALITY_CAPTURE_RETAINED_AUDIT_REQUIRED')
    except Exception as error:
        result['error'] = str(error)
    result['payload_sha256'] = {str(p.relative_to(case.work)): R.sha(p) for p in sorted(case.work.rglob('*')) if p.is_file()}
    R.write_new(case.work / 'result.json', result)
    with case.archive.open('xb') as f:
        with tarfile.open(fileobj=f, mode='w') as archive:
            archive.add(case.plan, arcname='plan.json')
            archive.add(case.work / 'result.json', arcname='result.json')
    return dict(scope=case.scope, complete=result['complete'], classification=result['classification'], archive=str(case.archive),
                next='STOP; independently CPU-audit terminal evidence before selecting another explicit process')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('prepare', 'execute', 'audit'))
    ap.add_argument('--cell', choices=('H01', 'H02', 'H03'), required=True)
    ap.add_argument('--depth', choices=(2, 8), type=int, required=True)
    ap.add_argument('--rung', choices=(0, 1, 2), type=int, required=True)
    args = ap.parse_args()
    case = Case(args.cell, args.depth, args.rung)
    if args.action == 'prepare':
        R.require(not case.plan.exists(), 'Refuse existing012 CPU plan')
        report = prepare(case)
        R.require(len(json.dumps(report, indent=2).encode()) < 1024**2, '012 compact proof plan exceeds archive member limit')
        R.write_new(case.plan, report)
        print(json.dumps(dict(scope=case.scope, plan=str(case.plan), command=report['command'], gpu_executed=False), indent=2))
    elif args.action == 'execute':
        print(json.dumps(execute(case), indent=2))
    else:
        import ddgi_corrected_quality_audit as A
        print(json.dumps(A.audit(case, save=True), indent=2))

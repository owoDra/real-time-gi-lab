#!/usr/bin/env python3
"""013 actual native CLI rejection under an unusable Vulkan ICD. CPU evidence only."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess

import closest_primary as C
import closest_primary_cases as K


def run(build, work):
    work = work.resolve()
    if work.exists() or not work.is_relative_to(C.ROOT / 'out'):
        raise ValueError('New repository/out CPU contract root required')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=C.ROOT, text=True).strip()
    for source in (Path(__file__).resolve(), Path(K.__file__).resolve()):
        if subprocess.check_output(['git', 'show', commit + ':' + str(source.relative_to(C.ROOT))], cwd=C.ROOT) != source.read_bytes():
            raise ValueError('Commit CPU contract source first')
    receipt = build.resolve() / 'result.json'
    proof = json.loads(receipt.read_text())
    if not proof['complete'] or proof['gpu_executed'] or proof['host_translation_units_recompiled'] != 13:
        raise ValueError('Complete CPU private build required')
    binary = Path(proof['executable'])
    if C.sha(binary) != proof['executable_sha256']:
        raise ValueError('Private executable drift')
    for group in ('input_sha256', 'dependency_sha256'):
        if not all(C.sha(Path(p)) == h for p, h in proof[group].items()):
            raise ValueError('Private build input/dependency drift')
    for name, digest in proof['private_shader_sha256'].items():
        if C.sha(build.resolve() / 'shaders' / name) != digest:
            raise ValueError('Private shader drift')
    work.mkdir(parents=True)
    no_icd = work / 'unavailable-driver.json'
    assert not no_icd.exists()
    env = dict(os.environ)
    env.update(VK_ICD_FILENAMES=str(no_icd), VK_DRIVER_FILES=str(no_icd),
               PHOS_N009_CONTRACT=str(K.CONTRACT))
    for name in ('PHOS_N010_CALIBRATION', 'PHOS_N010_CALIBRATION_DOSE', 'PHOS_N010_DIRECT_PROFILE'):
        env.pop(name, None)
    report = dict(schema='m001-closest-primary-native-cpu-contracts/1', source_commit=commit,
                  complete=False, gpu_executed=False, unusable_icd=str(no_icd),
                  build_receipt=str(receipt), build_receipt_sha256=C.sha(receipt),
                  executable_sha256=C.sha(binary), rows=[], runtime_admitted=False,
                  scope='Actual eight native CLI launches must reject unavailable ICD; no physical/runtime PASS')

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (120, 120))

    try:
        for cell, backend in K.TARGETS:
            case = K.Case(cell, backend)
            directory = work / case.name
            directory.mkdir()
            env['PHOS_N010_MEMORY_LEDGER'] = str(directory / 'allocation-ledger.json')
            cmd = K.command(case, binary, directory / 'capture')
            row = dict(name=case.name, command=cmd, returncode=None,
                       stdout='', stderr='', gpu_executed=False, pass_=False)
            report['rows'].append(row)
            try:
                p = subprocess.run(cmd, cwd=C.ROOT, env=env, capture_output=True, text=True,
                                   timeout=180, preexec_fn=limits)
            except subprocess.TimeoutExpired as exc:
                row['stdout'] = exc.stdout.decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
                row['stderr'] = exc.stderr.decode(errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
                row['timed_out'] = True
                raise
            row.update(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
            # Expected Vulkan instance rejection; a scene/CLI/loader-library
            # failure is different evidence and cannot count as this contract.
            message = (p.stdout + p.stderr).lower()
            row['pass_'] = p.returncode != 0 and ('vulkan instance' in message or 'instance creation' in message or 'createinstance' in message)
            if not row['pass_']:
                raise ValueError('Native did not reach expected unavailable-ICD rejection: ' + case.name)
        report['complete'] = True
    except Exception as exc:
        report['error'] = repr(exc)
    finally:
        report['payload_sha256'] = {str(p.relative_to(work)): C.sha(p)
                                    for p in sorted(work.rglob('*')) if p.is_file()}
        with (work / 'result.json').open('x') as f:
            json.dump(report, f, indent=2)
            f.write('\n')
    if not report['complete']:
        raise ValueError('CPU contract failure retained: ' + report.get('error', 'unknown'))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.build, args.out)
    print(json.dumps(dict(complete=result['complete'], cases=len(result['rows']),
                          all_pass=all(x['pass_'] for x in result['rows']), gpu_executed=False), indent=2))

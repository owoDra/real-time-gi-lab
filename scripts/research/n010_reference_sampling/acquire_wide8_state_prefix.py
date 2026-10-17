#!/usr/bin/env python3
"""Plan109: one explicit whole-frame state/prefix validation step; no queue."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN = D.RESULTS.parent / 'experiments/109-wide8-state-prefix-checkpoints.md'
BASE = D.OUT / 'wide8-state-prefix-v1'
SUMMARY = D.RESULTS / '351-wide8-all-state-prefix-summary.json'
COUNTERS = ('primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed')
ADDITIVE = ('proposal_bvh_queries', 'component_attempts', 'component_nulls', 'own_checks')
MAXIMA = ('max_own_log_error', 'max_conditioned_error_fraction', 'max_unconditioned_error_fraction')
SUFFIXES = tuple(f'.s{i}.{kind}' for i in range(4)
                 for kind in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')) + ('.hits',)


def paths(case, phase):
    label = f'case{case:02d}-phase{phase}'
    return D.RESULTS / f'{273+3*case+phase:03d}-wide8-state-prefix-{label}.json', BASE / label


def terminal(case, phase):
    output, _ = paths(case, phase)
    data = json.loads(D.checked(output))
    if not (data['complete'] and data['all_pass'] and data['native_terminal']
            and data['returncode'] == 0 and data['case_index'] == case and data['phase'] == phase):
        raise ValueError('prior state/prefix step incomplete or failed')
    for path, digest in data['payload_sha256'].items():
        D.checked(Path(path), digest)
    receipt = json.loads(D.checked(Path(data['resource_receipt'])))
    proc = Path('/proc') / str(receipt['pid']) / 'stat'
    if proc.exists():
        fields = proc.read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) == receipt['start_ticks'] and fields[0] != 'Z':
            raise ValueError('same prior native remains live')
    return data


def original_slots():
    original = json.loads(D.checked(D.RESULTS / '078-all-state-cpu-port-controls.json'))
    lock = json.loads(D.checked(D.RESULTS / '016-corpus-state-lock.json'))
    expected = {(cell, depth) for cell in lock['cells'] for depth in (2, 8)}
    if (not original['complete'] or not original['all_pass'] or len(original['rows']) != 24
            or {(r['cell'], r['vertices']) for r in original['rows']} != expected
            or original['spp'] != 16 or original['seeds'] != list(D.SEEDS)):
        raise ValueError('original locked all24 scope differs')
    return original, lock


def selected_slot(original, case):
    if case < 24:
        return original['rows'][case]
    return next(r for r in original['rows'] if r['cell'] == 'C7' and r['vertices'] == 2+6*(case-24))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-index', type=int, choices=range(26))
    parser.add_argument('--phase', type=int, choices=range(3))
    parser.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    if args.summarize:
        if args.case_index is not None or args.phase is not None or SUMMARY.exists():
            raise ValueError('summary requires no case/phase and an absent result')
    elif args.case_index is None or args.phase is None:
        parser.error('--case-index and --phase are required')
    case, phase = args.case_index, args.phase
    if not args.summarize:
        output, work = paths(case, phase)
        if output.exists() or work.exists():
            raise ValueError('refuse existing state/prefix step; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for path in (Path(__file__).resolve(), PLAN, Path(C.__file__), Path(D.__file__),
                 D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(path)
    for stem in ('225', '226', '231', '237', '252', '253', '258', '262', '266',
                 '270', '271', '254', '257', '272'):
        proof = C.pinned_result(stem)
        if not proof['all_pass']:
            raise ValueError('required physical/backend/prefix record failed: ' + stem)
        if stem in ('262', '266', '270') and not proof['full_four_seed_physical_pass']:
            raise ValueError('full four-seed physical gate required')
        for path, digest in proof['input_sha256'].items():
            D.checked(Path(path), digest)
    if args.summarize:
        resource.setrlimit(resource.RLIMIT_CPU, (600,) * 2)
        original, _ = original_slots()
        records = [terminal(c, p) for c in range(26) for p in range(3)]
        for record in records:
            c, p = record['case_index'], record['phase']
            slot = selected_slot(original, c)
            small, full = (8, 16) if c < 24 else (8192, 16384)
            if ((record['cell'], record['vertices'], record['spp'], record['begin_spp'])
                    != (slot['cell'], slot['vertices'], small if p == 1 else full, small if p == 2 else 0)
                    or (p == 2 and not record['all21_payloads_scored_counters_and_interval_audits_exact'])):
                raise ValueError('summary record does not cover its registered case/interval')
            for path, digest in record['input_sha256'].items():
                D.checked(Path(path), digest)
        result = dict(schema='n010-wide8-all-state-prefix-summary/1', complete=True,
                      all_pass=True, gpu_run=False, reference_admission=False,
                      classification='ALL24_STATE_AND_TWO_ACTUAL_PREFIX_CASES_COMPLETE_NO_ADMISSION',
                      native_invocations=78, low_dose_cases=24, actual_prefix_cases=2,
                      records=[str(paths(c, p)[0]) for c in range(26) for p in range(3)],
                      input_sha256=D.INPUTS,
                      source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                      tests='NOT_RUN; scientific evidence aggregation only')
        SUMMARY.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        print(result['classification'])
        return
    previous = [terminal(case, p) for p in range(phase)]
    if case:
        prior_case = terminal(case-1, 2)
        for path, digest in prior_case['input_sha256'].items():
            D.checked(Path(path), digest)
    for part in previous:
        for path, digest in part['input_sha256'].items():
            D.checked(Path(path), digest)
    sys.path.insert(0, str(D.HERE.parent / 'n010_comparison_readiness'))
    import qualify_references as Q
    for module in (Q, Q.L):
        D.checked(Path(module.__file__))
    for imported in list(sys.modules.values()):
        path = getattr(imported, '__file__', None)
        if path and Path(path).suffix == '.py' and Path(path).resolve().is_relative_to(D.ROOT):
            D.checked(Path(path).resolve())
    original, lock = original_slots()
    slot = selected_slot(original, case)
    cell, vertices = slot['cell'], slot['vertices']
    directory = Path(slot['directory'])
    for name, digest in slot['payload_sha256'].items():
        D.checked(directory / name, digest)
    state_dir = D.ROOT / lock['cells'][cell]['state_directory']
    for path in state_dir.iterdir():
        if path.is_file():
            D.checked(path)
    state = Q.L.read_state(state_dir)
    scene = directory / 'scene.n008'
    if (state['sha256'] != lock['cells'][cell]['state_sha256']
            or state['sha256'] != slot['state_sha256']
            or D.checked(scene, slot['scene_sha256']).decode() != Q.scene_for_state(state, vertices).text()):
        raise ValueError('canonical state/scene differs')
    small, full = (8, 16) if case < 24 else (8192, 16384)
    spp, begin = (small if phase == 1 else full), (small if phase == 2 else 0)
    binary = D.OUT / ('wide8-cpu-bvh-v1/n010_wide8_exporter' if phase == 0
                      else 'wide8-prefix-build-v1/n010_wide8_prefix')
    D.checked(binary)
    net = D.OUT / 'sobol16x262144.bin'
    D.checked(net)
    work.mkdir(parents=True)
    prefix, receipt = work / 'o', work / 'native.resources.json'
    command = [str(binary), '--net', str(net), '--scene', str(scene), '--out', str(prefix),
               '--seeds', ','.join(map(str, D.SEEDS)), '--spp', str(spp), '--threads', '1']
    if phase == 2:
        prior_prefix = paths(case, 1)[1] / 'o'
        # The retained loader has a fifth proposal_null_samples field. This
        # backend never increments it; real proposal nulls are all_split audits.
        command += ['--resume-prefix', str(prior_prefix), '--resume-spp', str(small),
                    '--resume-counters', ';'.join(','.join(str(r[k]) for k in COUNTERS) + ',0'
                        for r in previous[1]['native_metadata']['runs'])]
    result = dict(schema='n010-wide8-state-prefix-step/1', complete=False, all_pass=False,
                  gpu_run=False, reference_admission=False, classification='STATE_PREFIX_NATIVE_ACQUIRING',
                  case_index=case, phase=phase, cell=cell, vertices=vertices, spp=spp, begin_spp=begin,
                  input_sha256=D.INPUTS, command=command, resource_receipt=str(receipt),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  scheduling='One explicit native only; no next-step queue',
                  tests='NOT_RUN; scientific whole-frame state/prefix acquisition')

    def save():
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    def hashes():
        return {str(p): C.sha(p) for p in work.iterdir() if p.is_file()}

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (21600,) * 2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),
            start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
            address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
            command=command)) + '\n')

    save()
    start = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=28800, preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            (work / 'native.stdout').write_bytes(error.stdout or b'')
            (work / 'native.stderr').write_bytes(error.stderr or b'')
            result.update(native_terminal=True, elapsed_seconds=time.monotonic()-start)
            raise ValueError('native elapsed guard; no retry') from error
        (work / 'native.stdout').write_text(proc.stdout)
        (work / 'native.stderr').write_text(proc.stderr)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(returncode=proc.returncode, native_terminal=True,
                      elapsed_seconds=time.monotonic()-start,
                      child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                      payload_sha256=hashes(), classification='STATE_PREFIX_TERMINAL_ANALYSIS_PENDING')
        save()
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [21600]*2 or actual['address_space'] != [4*1024**3]*2
                or actual['affinity'] != [31] or actual['nice'] != 15 or proc.returncode):
            raise ValueError('native/resource failure; no retry')
        resource.setrlimit(resource.RLIMIT_CPU, (600,) * 2)
        meta = json.loads(proc.stdout)
        old_meta = json.loads(D.checked(directory / 'meta.json'))
        for key in ('scene_sha256', 'geometry_sha256', 'width', 'height', 'triangles', 'point_lights', 'ray_offset'):
            if meta[key] != old_meta[key]:
                raise ValueError('output metadata identity differs: ' + key)
        if meta['spp'] != spp or meta['seeds'] != list(D.SEEDS) or len(meta['runs']) != 4:
            raise ValueError('output seed/count differs')
        if phase and (meta.get('prefix_begin') != begin or meta.get('audit_scope') != 'new_sample_interval'):
            raise ValueError('prefix interval diagnostic scope differs')
        if prefix.with_suffix('.hits').read_bytes() != (directory / 'o.hits').read_bytes():
            raise ValueError('original primary-hit records differ')
        sys.path.insert(0, str(D.HERE.parent / 'n008_hdr_oracle'))
        import n008lib as L
        D.checked(Path(L.__file__))
        for i, seed in enumerate(D.SEEDS):
            row = L.read_sidecar(Path(str(prefix) + f'.s{i}.f64'))
            if ((row['width'], row['height'], row['spp'], row['seed'])
                    != (meta['width'], meta['height'], spp, seed)):
                raise ValueError('sidecar shape/count/seed differs')
            for kind in ('mean', 'm2'):
                if not (np.isfinite(row[kind]).all() and (row[kind] >= 0).all()):
                    raise ValueError('sidecar nonfinite/negative')
            for component in ('emission', 'direct', 'indirect', 'total'):
                image = L.read_pfm(Path(str(prefix) + f'.s{i}.{component}.pfm'))
                if (image.shape != (meta['height'], meta['width'], 3)
                        or not (np.isfinite(image).all() and (image >= 0).all())):
                    raise ValueError('PFM nonfinite/negative')
            run, old_run = meta['runs'][i], old_meta['runs'][i]
            if run['seed'] != seed or run['primary_hits']*16 != old_run['primary_hits']*spp:
                raise ValueError('original primary count differs')
            audit = run['all_split']
            if (audit['own_checks'] != audit['component_attempts']-audit['component_nulls']
                    or not np.isfinite([audit[k] for k in MAXIMA]).all()
                    or audit['max_own_log_error'] > 1e-6 or audit['max_conditioned_error_fraction'] > 1):
                raise ValueError('interval proposal/numerical audit failed')
            if case < 24 and phase == 0:
                old = L.read_sidecar(directory / f'o.s{i}.f64')
                for kind in ('mean', 'm2'):
                    if row[kind][..., :2, :].tobytes() != old[kind][..., :2, :].tobytes():
                        raise ValueError('original direct/emission moment bits differ')
                for component in ('emission', 'direct'):
                    suffix = f'.s{i}.{component}.pfm'
                    if Path(str(prefix)+suffix).read_bytes() != (directory / ('o'+suffix)).read_bytes():
                        raise ValueError('original deterministic PFM bits differ')
        if phase == 2:
            uninterrupted = paths(case, 0)[1] / 'o'
            for suffix in SUFFIXES:
                if Path(str(prefix)+suffix).read_bytes() != Path(str(uninterrupted)+suffix).read_bytes():
                    raise ValueError('uninterrupted/restored payload bits differ: ' + suffix)
            for full_run, small_run, run in zip(previous[0]['native_metadata']['runs'],
                                                previous[1]['native_metadata']['runs'], meta['runs']):
                if any(full_run[k] != run[k] for k in COUNTERS):
                    raise ValueError('uninterrupted/restored scored counters differ')
                a, b, c = full_run['all_split'], small_run['all_split'], run['all_split']
                if (any(a[k] != b[k]+c[k] for k in ADDITIVE)
                        or any(a[k] != max(b[k], c[k]) for k in MAXIMA)):
                    raise ValueError('uninterrupted/combined interval proposal audit differs')
            result['all21_payloads_scored_counters_and_interval_audits_exact'] = True
        for path, digest in list(D.INPUTS.items()):
            D.checked(Path(path), digest)
        result.update(complete=True, all_pass=True, native_metadata=meta,
                      classification='WHOLE_FRAME_STATE_PREFIX_STEP_COMPLETE_NO_ADMISSION')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='STATE_PREFIX_FAILURE_PARTIALS_RETAINED', failure=str(error))
    result['payload_sha256'] = hashes()
    save()
    print(json.dumps({k: result.get(k) for k in ('case_index', 'phase', 'complete', 'all_pass',
                                              'classification', 'failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

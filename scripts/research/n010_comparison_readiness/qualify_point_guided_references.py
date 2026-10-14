#!/usr/bin/env python3
"""Acquire the fixed nine unfinished slots only after full sampler proof."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
import qualify_references as Q
import point_guided_reference_provenance as P
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (172800, 172800))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--prerequisites-only', action='store_true')
    ap.add_argument('--audit-archive', type=Path)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists() or (a.audit_archive and a.audit_archive.exists()):
        raise ValueError('refuse existing acquisition/proof attempt')
    inputs = {str(Path(__file__).resolve()): sha(Path(__file__)),
        str(Path(P.__file__).resolve()): sha(Path(P.__file__)),
        str((RESULTS.parent/'experiments/032-point-guided-reference-qualification.md').resolve()):
            sha(RESULTS.parent/'experiments/032-point-guided-reference-qualification.md')}
    result = {'schema': 'n010-point-guided-reference-qualification/1', 'complete': False,
        'all_pass': False, 'gpu_run': False, 'eligible_for_references': False, 'input_sha256': inputs,
        'selected_transports': list(P.SELECTED), 'cells': [], 'process_attempts': [],
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'computational_variant': P.VARIANT, 'threads': 16,
        'limits': {'address_space_bytes': 4*1024**3, 'cpu_seconds': 172800, 'elapsed_seconds': 43200},
        'scope': 'Separate ladders for all nine prospectively selected unfinished slots; no view transition or whole-corpus admission'}
    def save():
        a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    try:
        proofs = P.prerequisites(inputs)
        result['proof_sha256'] = proofs
        lock = read(a.lock, inputs)
        if set(lock['cells']) != {f'C{i}' for i in range(1, 13)}:
            raise ValueError('complete original corpus lock required')
        result['classification'] = 'PREREQUISITES_PASS_NO_ACQUISITION' if a.prerequisites_only else 'ACQUIRING_UNADMITTED'
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result.update(complete=True, classification='PREREQUISITE_REFUSAL_NO_ACQUISITION', failure=str(error))
        # Archive exact read proof bytes: partial producer files may later change.
        if a.audit_archive:
            a.audit_archive.mkdir(parents=True)
            archives = {}
            for source, digest in inputs.items():
                raw = Path(source).read_bytes()
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError('proof changed during refusal archive; retained attempt must be reviewed')
                target = a.audit_archive/(digest+'-'+Path(source).name)
                target.write_bytes(raw)
                if sha(target) != digest:
                    raise ValueError('refusal archive changed bytes')
                archives[source] = {'path': str(target.resolve()), 'sha256': digest}
            result['read_input_archives'] = archives
        save()
        print('GUIDED PREREQUISITES REFUSED; no acquisition', flush=True)
        raise SystemExit(2)
    if a.prerequisites_only:
        check_files(inputs, {})
        result.update(complete=True, all_pass=True)
        save()
        raise SystemExit(0)
    a.work = a.work.resolve()
    a.work.mkdir(parents=True)
    save()
    try:
        for selected in P.SELECTED:
            cell, text = selected.rsplit('_T_B', 1)
            vertices = int(text)
            check_files(inputs, {})
            state = Q.L.read_state(ROOT/lock['cells'][cell]['state_directory'])
            if state['sha256'] != lock['cells'][cell]['state_sha256']:
                raise ValueError('locked state changed')
            for path in (ROOT/lock['cells'][cell]['state_directory']).iterdir():
                if path.is_file():
                    inputs[str(path.resolve())] = sha(path)
            scene = Q.scene_for_state(state, vertices)
            directory = a.work/selected
            directory.mkdir()
            scene_path = directory/'scene.n008'
            scene_path.write_text(scene.text())
            inputs[str(scene_path)] = sha(scene_path)
            levels, manifests, previous = [], [], None
            q = {'cell': cell, 'transport': f'T_B{vertices}', 'state_sha256': state['sha256'],
                'scene_sha256': sha(scene_path), 'computational_variant': P.VARIANT,
                'proof_sha256': proofs, 'levels': levels, 'classification': 'INELIGIBLE'}
            result['cells'].append(q)
            save()
            for spp in Q.LEVELS:
                check_files(inputs, {})
                prefix = directory/f'o.n{spp}'
                command = [str(P.BINARY), '--net', str(Q.NET), '--scene', str(scene_path), '--out', str(prefix),
                    '--seeds', ','.join(map(str, Q.L.N007_SEEDS)), '--spp', str(spp), '--threads', '16']
                prior = {}
                if previous:
                    prior = levels[-1]['all_payload_sha256']
                    check_files({str(directory/name): h for name, h in prior.items()}, inputs)
                    inputs[str(directory/f'n{previous["spp"]}.meta.json')] = sha(directory/f'n{previous["spp"]}.meta.json')
                    command += ['--resume-prefix', str(directory/f'o.n{previous["spp"]}'), '--resume-spp', str(previous['spp']),
                        '--resume-counters', ';'.join(','.join(str(r[k]) for k in P.KEYS) for r in previous['runs'])]
                attempt = {'command': command, 'pass': False, 'input_sha256': dict(inputs), 'proof_sha256': proofs,
                    'sample_interval': [previous['spp'] if previous else 0, spp], 'previous_payload_sha256': prior}
                result['process_attempts'].append(attempt)
                attempt_path = directory/f'n{spp}.attempt.json'
                attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                save()
                started = time.monotonic()
                try:
                    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                        timeout=43200, preexec_fn=limits)
                except subprocess.TimeoutExpired as error:
                    (directory/f'n{spp}.stdout.json').write_bytes(error.stdout or b'')
                    (directory/f'n{spp}.stderr.log').write_bytes(error.stderr or b'')
                    raise ValueError('guided acquisition elapsed guard; partials retained')
                raw_path = directory/f'n{spp}.stdout.json'
                raw_path.write_text(proc.stdout)
                log_path = directory/f'n{spp}.stderr.log'
                log_path.write_text(proc.stderr)
                attempt.update(returncode=proc.returncode, stdout_sha256=sha(raw_path), stderr_sha256=sha(log_path),
                    wall_seconds_diagnostic=time.monotonic()-started)
                attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                save()
                if proc.returncode:
                    raise ValueError('guided acquisition failed; no retry')
                fresh = json.loads(proc.stdout)
                if (fresh['spp'] != spp or fresh['seeds'] != list(Q.L.N007_SEEDS) or len(fresh['runs']) != 4
                    or fresh['scene_sha256'] != sha(scene_path) or fresh['geometry_sha256'] != scene.geometry_sha256()):
                    raise ValueError('guided output scene/seed/count mismatch')
                check_files(inputs, {})
                payloads = {p.name: sha(p) for p in directory.glob(f'o.n{spp}.*')}
                fresh.update(binary_sha256=sha(P.BINARY), net_sha256=sha(Q.NET), scene_sha256=sha(scene_path),
                    computational_variant=P.VARIANT, proof_sha256=proofs, sample_interval=attempt['sample_interval'],
                    previous_payload_sha256=prior, all_payload_sha256=payloads,
                    source_commit=result['source_commit'], wall_seconds_diagnostic=attempt['wall_seconds_diagnostic'])
                if previous:
                    fresh['previous_metadata_sha256'] = sha(directory/f'n{previous["spp"]}.meta.json')
                meta_path = directory/f'n{spp}.meta.json'
                meta_path.write_text(json.dumps(fresh, indent=2)+'\n')
                manifests.append({'spp': spp, 'references': [{'seed': seed,
                    'path': f'o.n{spp}.s{i}.total.pfm', 'sha256': payloads[f'o.n{spp}.s{i}.total.pfm']}
                    for i, seed in enumerate(Q.L.N007_SEEDS)]})
                manifest_path = directory/f'screen-n{spp}.json'
                manifest_path.write_text(json.dumps({'schema_version': 1, 'source_commit': result['source_commit'],
                    'scene_sha256': sha(scene_path), 'frame_state_sha256': state['sha256']['frame'], 'levels': manifests}, indent=2)+'\n')
                screen = Q.assess(manifest_path)
                means = np.stack([Q.L.read_sidecar(directory/f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)])
                levels.append({'spp': spp, 'screen': screen, 'geometry_hash_match': True,
                    'metadata_sha256': sha(meta_path), 'all_payload_sha256': payloads,
                    'components_union_positive': {k: int((means[..., j, :].max(-1)>0).any(0).sum())
                        for j, k in enumerate(Q.L.COMPONENTS)},
                    'replicate_means_se_max': float((means.std(0, ddof=1)/2).max())})
                q['classification'] = 'STATISTICALLY_ELIGIBLE' if screen['status'] == 'statistical-screen-pass' else 'INELIGIBLE'
                (directory/'qualification.json').write_text(json.dumps(q, indent=2, allow_nan=False)+'\n')
                attempt['pass'] = True
                attempt_path.write_text(json.dumps(attempt, indent=2)+'\n')
                # Audit actual complete level outputs before starting another level.
                P.verify_reference(directory, cell, vertices, lock['cells'][cell], {}, require_eligible=False)
                print(selected, spp, q['classification'], flush=True)
                save()
                previous = fresh
                if q['classification'] == 'STATISTICALLY_ELIGIBLE':
                    break
        check_files(inputs, {})
        result['all_pass'] = len(result['cells']) == 9 and all(q['classification'] == 'STATISTICALLY_ELIGIBLE' for q in result['cells'])
        result['classification'] = 'SELECTED_SLOTS_QUALIFIED_UNADMITTED' if result['all_pass'] else 'SELECTED_CAP_FAILURES_UNADMITTED'
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result.update(classification='ACQUISITION_FAILED_PARTIALS_RETAINED', failure=str(error))
    result['complete'] = True
    save()
    raise SystemExit(0 if result['all_pass'] else 2)

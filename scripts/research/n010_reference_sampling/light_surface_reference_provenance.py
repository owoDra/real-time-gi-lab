"""Plan-041 reference admission, preserving every original numerical gate."""
import json
import os
from pathlib import Path
import resource
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
import acquire_light_surface_feasibility as F
import qualify_references as Q
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

VARIANT = 'validated-light-surface-mixture'
BINARY = ROOT/'out/research/n010-comparison-readiness/light-surface-build-v1/prefix/n010_light_surface_prefix'
FEASIBILITY_WORK = ROOT/'out/research/n010-comparison-readiness/light-surface-feasibility-v1'
PLAN = RESULTS.parent/'experiments/041-prospective-light-surface-corpus-admission.md'
PROOFS = ('144-light-surface-proposal-build.json', '145-light-surface-physical-controls.json',
          '146-light-surface-all-state-and-prefix.json', '147-light-surface-bounded-feasibility.json')
SELECTED = ('C1_T_B8', 'C2_T_B8', 'C3_T_B8', 'C4_T_B2', 'C4_T_B8',
            'C5_T_B2', 'C5_T_B8', 'C6_T_B2', 'C6_T_B8')
KEYS = F.KEYS
CPU_SECONDS, AS_BYTES = F.CPU_LIMIT, F.AS_LIMIT


def feasibility(inputs):
    """Check the actual bounded acquisition, not merely its summary's PASS bit."""
    if F.prerequisites(inputs) != BINARY:
        raise ValueError('light-surface prefix identity differs')
    proof = read(RESULTS/PROOFS[-1], inputs)
    if (not proof['complete'] or not proof['all_pass']
        or proof['classification'] != 'BOUNDED_FEASIBILITY_PASS_NOT_ADMITTED'
        or proof['eligible_for_references'] or proof['gpu_run'] or proof['scoring_exclusions'] != 0
        or proof['selected_transport'] != 'C1_T_B8' or proof['threads'] != 16
        or proof['seeds'] != list(Q.L.N007_SEEDS) or proof['binary_sha256'] != sha(BINARY)
        or [r['spp'] for r in proof['levels']] != [8192, 16384]
        or len(proof['process_attempts']) != 2
        or proof['feasibility_threshold'] != {'maximum_absolute_p99_ratio_each_level': 0.75, 'full_signal_support': 1.0}
        or proof['limits'] != {'address_space_bytes': AS_BYTES, 'cpu_seconds': CPU_SECONDS, 'elapsed_seconds': 43200}):
        raise ValueError('bounded feasibility scope/classification differs')
    check_files(proof['input_sha256'], inputs)
    audit = read(RESULTS/'137-second-point-guided-level-and-cpu-budget.json', inputs)
    archive = Path(audit['qualification_source']['archive'])
    if not audit['complete'] or not audit['all_pass'] or sha(archive) != audit['qualification_source']['sha256']:
        raise ValueError('feasibility baseline identity differs')
    baseline = read(archive, inputs)
    if [r['spp'] for r in baseline['levels']] != [8192, 16384]:
        raise ValueError('baseline ladder differs')
    scene_path = FEASIBILITY_WORK/'scene.n008'
    if sha(scene_path) != proof['scene_sha256'] or proof['scene_sha256'] != baseline['scene_sha256']:
        raise ValueError('feasibility/baseline scene differs')
    previous = None
    for level, attempt, old in zip(proof['levels'], proof['process_attempts'], baseline['levels']):
        spp = level['spp']
        prefix = FEASIBILITY_WORK/f'o.n{spp}'
        meta_path = FEASIBILITY_WORK/f'n{spp}.meta.json'
        meta = read(meta_path, inputs)
        command = [str(BINARY), '--net', str(Q.NET), '--scene', str(scene_path), '--out', str(prefix),
                   '--seeds', ','.join(map(str, Q.L.N007_SEEDS)), '--spp', str(spp), '--threads', '16']
        if previous:
            command += ['--resume-prefix', str(FEASIBILITY_WORK/f'o.n{previous["spp"]}'),
                '--resume-spp', str(previous['spp']),
                '--resume-counters', ';'.join(','.join(str(r[k]) for k in KEYS) for r in previous['runs'])]
        if (not attempt['pass'] or attempt['returncode'] != 0 or attempt['command'] != command
            or attempt['sample_interval'] != [previous['spp'] if previous else 0, spp]
            or meta['spp'] != spp or meta['seeds'] != list(Q.L.N007_SEEDS) or len(meta['runs']) != 4
            or not level['primary_direct_emission_exact_to_baseline']
            or set(level['payload_sha256']) != set(F.PAYLOADS)):
            raise ValueError('actual feasibility invocation differs')
        for suffix, digest in level['payload_sha256'].items():
            check_files({str(prefix)+suffix: digest}, inputs)
        raw = FEASIBILITY_WORK/f'n{spp}.stdout.json'
        log = FEASIBILITY_WORK/f'n{spp}.stderr.log'
        if (sha(raw) != attempt['stdout_sha256'] or sha(log) != attempt['stderr_sha256']
            or read(raw, inputs) != meta):
            raise ValueError('actual feasibility stdout/metadata differs')
        inputs[str(log)] = sha(log)
        receipt_path = FEASIBILITY_WORK/f'n{spp}.resource-limits.json'
        receipt = read(receipt_path, inputs)
        if (sha(receipt_path) != level['resource_receipt_sha256']
            or receipt['cpu'] != [CPU_SECONDS]*2 or receipt['address_space'] != [AS_BYTES]*2
            or receipt['command'] != command or not isinstance(receipt['pid'], int) or receipt['pid'] <= 0
            or not isinstance(receipt['start_ticks'], int) or receipt['start_ticks'] <= 0
            or not isinstance(receipt['uid'], int) or receipt['uid'] < 0):
            raise ValueError('actual feasibility resource receipt differs')
        manifest_path = FEASIBILITY_WORK/f'screen-n{spp}.json'
        read(manifest_path, inputs)
        actual = Q.assess(manifest_path)
        ratio = actual['rows'][-1]['max_active_abs_p99']/old['screen']['rows'][-1]['max_active_abs_p99']
        if (actual != level['screen'] or ratio != level['absolute_p99_ratio_to_global_guide']
            or not level['feasibility_pass'] or ratio > 0.75
            or actual['rows'][-1]['active_fraction'] != 1.0
            or (previous and not actual['rows'][-1]['signal_support_stable_vs_previous'])):
            raise ValueError('unchanged bounded feasibility replay differs')
        previous = meta
    check_files(inputs, {})
    return proof


def prerequisites(inputs):
    feasibility(inputs)
    if sha(original) != ORIGINAL_SHA:
        raise ValueError('original reference verifier changed')
    inputs[str(original)] = ORIGINAL_SHA
    for p in (Path(__file__), Path(F.__file__), PLAN,
              Path(__file__).with_name('qualify_light_surface_references.py')):
        inputs[str(p.resolve())] = sha(p)
    return {name: sha(RESULTS/name) for name in PROOFS}


def imported_command(directory, q, cell, vertices, spp, inputs):
    if ((cell, vertices) != ('C1', 8) or spp not in (8192, 16384)
        or q['feasibility_import'] != {'result_sha256': sha(RESULTS/PROOFS[-1]),
            'directory': str(FEASIBILITY_WORK), 'levels': [8192, 16384]}):
        raise ValueError('feasibility import scope differs')
    proof = read(RESULTS/PROOFS[-1], inputs)
    index = (8192, 16384).index(spp)
    source = proof['process_attempts'][index]
    level = proof['levels'][index]
    for suffix, digest in level['payload_sha256'].items():
        if sha(directory/(f'o.n{spp}'+suffix)) != digest:
            raise ValueError('imported payload differs from actual feasibility')
    native_meta = directory/f'n{spp}.imported-native-meta.json'
    original_meta = FEASIBILITY_WORK/f'n{spp}.meta.json'
    if sha(native_meta) != sha(original_meta):
        raise ValueError('native import metadata bytes differ')
    inputs[str(native_meta)] = sha(native_meta)
    for suffix in ('stdout.json', 'stderr.log', 'resource-limits.json'):
        copied = directory/f'n{spp}.{suffix}'
        retained = FEASIBILITY_WORK/f'n{spp}.{suffix}'
        if sha(copied) != sha(retained):
            raise ValueError('actual imported execution bytes differ')
        inputs[str(copied)] = sha(copied)
    attempt = read(directory/f'n{spp}.attempt.json', inputs)
    if attempt.get('imported_from') != {'result_sha256': sha(RESULTS/PROOFS[-1]),
            'attempt_index': index, 'directory': str(FEASIBILITY_WORK)}:
        raise ValueError('copied attempt must retain actual origin')
    return source['command']


def set_limits(prefix, spp, previous):
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    stat = (Path('/proc')/str(os.getpid())/'stat').read_text().rsplit(')', 1)[1].split()
    value = {'schema': 'n010-light-surface-native-resource-receipt/1', 'pid': os.getpid(),
        'ppid': os.getppid(), 'start_ticks': int(stat[19]), 'uid': os.getuid(),
        'cpu': list(resource.getrlimit(resource.RLIMIT_CPU)),
        'address_space': list(resource.getrlimit(resource.RLIMIT_AS)),
        'spp': spp, 'sample_interval': [previous['spp'] if previous else 0, spp],
        'threads': 16, 'elapsed_guard_seconds': 43200, 'policy_sha256': sha(PLAN),
        'implementation_sha256': sha(Path(__file__)),
        'qualifier_sha256': sha(Path(__file__).with_name('qualify_light_surface_references.py'))}
    path = prefix.parent/f'n{spp}.resource-limits.json'
    with path.open('x') as out:
        out.write(json.dumps(value, indent=2)+'\n')


# Adapt only variant/proof/actual-import dispatch. All original payload, scene,
# component, counter, exact prefix, screen and stop checks remain verbatim.
original = SCRIPTS/'point_guided_reference_provenance.py'
ORIGINAL_SHA = 'e22bb5b1e28e3c8463f5ecbb1049305ae6e4b566b9f81c9e6c21a891eba95e91'
if sha(original) != ORIGINAL_SHA:
    raise ValueError('original numerical/provenance verifier changed')
source = original.read_text()
source = once(source, "VARIANT = 'validated-point-guided-mixture'", 'VARIANT = '+repr(VARIANT))
source = once(source,
    "BINARY = ROOT/'out/research/n010-comparison-readiness/point-guided-prefix-build-v1/n010_point_guided_prefix'",
    'BINARY = Path('+repr(str(BINARY))+')')
source = once(source,
    "PROOFS = ('112-point-guided-oracle-build.json', '113-point-guided-physical-controls.json',\n"
    "          '114-point-guided-prefix-build.json', '115-point-guided-all-state-and-prefix.json')",
    'PROOFS = '+repr(PROOFS))
start = source.index('def prerequisites(inputs):\n')
end = source.index('\ndef verify_reference(', start)
source = source[:start]+'def prerequisites(inputs):\n    return _prerequisites(inputs)\n\n'+source[end:]
source = once(source, 'qualify_point_guided_references.py', 'qualify_light_surface_references.py')
source = once(source, "        attempt = read(directory/f'n{spp}.attempt.json', inputs)",
    "        if q.get('feasibility_import') and spp in (8192, 16384):\n"
    "            cmd = _imported_command(directory, q, cell, vertices, spp, inputs)\n"
    "        attempt = read(directory/f'n{spp}.attempt.json', inputs)")
namespace = {'__name__': __name__+'._original_gates', '__file__': __file__,
             '_prerequisites': prerequisites, '_imported_command': imported_command}
exec(compile(source, str(original)+'#plan041', 'exec'), namespace)
original_gates = namespace['verify_reference']


def verify_reference(directory, cell, vertices, spec, inputs, require_eligible=True):
    directory = directory.resolve()
    result = original_gates(directory, cell, vertices, spec, inputs, require_eligible)
    q = read(directory/'qualification.json', inputs)
    if q.get('computational_variant') != VARIANT:
        return result
    inputs[str(original)] = ORIGINAL_SHA
    for level in q['levels']:
        spp = level['spp']
        path = directory/f'n{spp}.resource-limits.json'
        receipt = read(path, inputs)
        meta = read(directory/f'n{spp}.meta.json', inputs)
        attempt = read(directory/f'n{spp}.attempt.json', inputs)
        if (receipt['cpu'] != [CPU_SECONDS]*2 or receipt['address_space'] != [AS_BYTES]*2
            or meta['resource_limits_sha256'] != sha(path) or attempt['resource_limits_sha256'] != sha(path)):
            raise ValueError('reference resource bounds/identity differs')
        if attempt.get('imported_from'):
            original_receipt = FEASIBILITY_WORK/f'n{spp}.resource-limits.json'
            if sha(path) != sha(original_receipt):
                raise ValueError('imported actual native resource receipt differs')
        elif (receipt['spp'] != spp or receipt['sample_interval'] != meta['sample_interval']
            or receipt['threads'] != 16 or receipt['elapsed_guard_seconds'] != 43200
            or receipt['policy_sha256'] != sha(PLAN) or receipt['implementation_sha256'] != sha(Path(__file__))
            or receipt['qualifier_sha256'] != sha(Path(__file__).with_name('qualify_light_surface_references.py'))
            or not isinstance(receipt['pid'], int) or receipt['pid'] <= 0
            or not isinstance(receipt['ppid'], int) or receipt['ppid'] <= 0
            or not isinstance(receipt['start_ticks'], int) or receipt['start_ticks'] <= 0
            or not isinstance(receipt['uid'], int) or receipt['uid'] < 0):
            raise ValueError('fresh native resource receipt differs')
    check_files(inputs, {})
    result['feasibility_imported_levels'] = q.get('feasibility_import', {}).get('levels', [])
    return result

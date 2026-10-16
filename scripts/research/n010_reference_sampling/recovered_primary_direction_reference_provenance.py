"""Plans 047/050: explicit recovered proof dispatch, unchanged numerical gates."""
import json
from pathlib import Path

from primary_direction_recovery_programs import HERE, ROOT, RESULTS, PLAN as RECOVERY_PLAN, sha, once
import recover_primary_direction_physical as R

_BASE = HERE/'primary_direction_reference_provenance.py'
_BASE_SHA = 'b9c992b696fdcc31d9644d55fcd6a3903e71519f04d6b9fcc681b00bbfeca3e9'
_QUALIFIER_BASE = HERE/'qualify_primary_direction_references.py'
_QUALIFIER_SHA = '99bbde9b594dd5e1d9b3363210f225b7f177690ebfbdfa8ac2c86d56b36e784a'
_PHYSICAL = RESULTS/'163-primary-direction-recovered-physical-controls.json'
_PHYSICAL_WORK = ROOT/'out/research/n010-comparison-readiness/primary-direction-physical-recovery-v1'
CONTINUATION_PLAN = RESULTS.parent/'experiments/050-prospective-zero-export-feasibility-recovery.md'


def _verify_recovered_physical(inputs):
    from reference_provenance import read
    from qualify_hybrid_references import check_files
    proof = read(_PHYSICAL, inputs)
    if not proof['complete'] or not proof['all_pass']:
        raise ValueError('recovered physical proof is incomplete/failed')
    retained = R.prepare(inputs)
    partial = read(R.PARTIAL, inputs)
    if (proof['recovery_provenance'] != retained['provenance']
        or proof['frozen_scene_names'] != partial['frozen_scene_names']
        or [r['name'] for r in proof['rows']] != partial['frozen_scene_names']
        or proof['seeds'] != partial['seeds'] or proof['threads'] != 4
        or proof['limits'] != partial['limits'] or proof['scoring_exclusions']
        or proof['gpu_run'] or proof['eligible_for_references']):
        raise ValueError('recovered physical scope/import origin differs')
    controls = ROOT/'out/research/n010-comparison-readiness/sampler-validation-v1/rqmc'
    binary = ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1/standalone/n010_primary_direction_oracle'
    seeds = ','.join(map(str, partial['seeds']))
    new_count = 0
    for row in proof['rows']:
        name = row['name']
        if (row['payload_directory'] != str(_PHYSICAL_WORK) or row['returncode']
            or not all(row[k] for k in ('pass', 'all_finite_nonnegative', 'direct_emission_exact',
                                       'primary_records_exact', 'headers_match', 'null_samples_bounded'))):
            raise ValueError('recovered scene row scope differs')
        meta_path = controls/(name+'.meta.json')
        meta = read(meta_path, inputs)
        expected = [str(binary), '--net', str(ROOT/'out/research/n010-comparison-readiness/sobol16x262144.bin'),
                    '--scene', str(controls/(name+'.n008')), '--out', str(_PHYSICAL_WORK/name),
                    '--seeds', seeds, '--spp', str(meta['spp']), '--threads', '4']
        required = {f'{name}.s{i}.{kind}' for i in range(4)
                    for kind in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')}
        required |= {name+'.hits', name+'.stdout', name+'.stderr', name+'.meta.json'}
        if row['spp'] != meta['spp'] or set(row['payload_sha256']) != required:
            raise ValueError('recovered scene sample/payload scope differs')
        if name in retained['rows']:
            old = retained['rows'][name]
            expected[expected.index('--out')+1] = str(R.OLD_WORK/name)
            if (row['execution_origin'] != 'retained-152-byte-copy' or row['command'] != old['command']
                or row['payload_sha256'] != old['payload_sha256']):
                raise ValueError('imported scene command/payload identity differs')
        else:
            new_count += 1
            if row['execution_origin'] != 'new-native-invocation':
                raise ValueError('fresh scene wrongly labelled as imported')
        if row['command'] != expected:
            raise ValueError('actual recovered physical native command differs')
        check_files({str(_PHYSICAL_WORK/p): h for p, h in row['payload_sha256'].items()}, inputs)
        raw = read(_PHYSICAL_WORK/(name+'.stdout'), inputs)
        saved = read(_PHYSICAL_WORK/(name+'.meta.json'), inputs)
        if raw != saved or raw['seeds'] != partial['seeds'] or raw['spp'] != row['spp']:
            raise ValueError('actual recovered stdout/native metadata differs')
    if new_count != 10:
        raise ValueError('recovery must retain seven and acquire ten scenes')
    check_files(proof['input_sha256'], inputs)


if sha(_BASE) != _BASE_SHA or sha(_QUALIFIER_BASE) != _QUALIFIER_SHA:
    raise ValueError('frozen plan-046 provenance/acquisition source changed')
_source = _BASE.read_text()
for _before, _after in (
    ('import acquire_primary_direction_feasibility as F', 'import acquire_post_stop_primary_direction_feasibility as F'),
    ('primary-direction-feasibility-v1', 'primary-direction-feasibility-recovery-v2'),
    ('152-primary-direction-physical-controls.json', '163-primary-direction-recovered-physical-controls.json'),
    ('153-primary-direction-all-state-and-prefix.json', '164-primary-direction-recovered-all-state-and-prefix.json'),
    ('154-primary-direction-bounded-feasibility.json', '172-primary-direction-post-stop-bounded-feasibility.json')):
    _source = once(_source, _before, _after)
_name = 'qualify_primary_direction_references.py'
if _source.count(_name) != 4:
    raise ValueError('qualifier identity dispatch count differs')
_source = _source.replace(_name, 'qualify_recovered_primary_direction_references.py')
_source = once(_source, '    if F.prerequisites(inputs) != BINARY:',
    '    _verify_recovered_physical(inputs)\n    if F.prerequisites(inputs) != BINARY:')
_source = once(_source, '    for p in (Path(__file__), Path(F.__file__), PLAN,',
    '    for p in (Path(__file__), Path(F.__file__), PLAN, RECOVERY_PLAN, CONTINUATION_PLAN, _BASE, _QUALIFIER_BASE,\n'
    '              Path(R.__file__), HERE/"primary_direction_recovery_programs.py",\n'
    '              HERE/"validate_recovered_primary_direction_prefix.py",')
exec(compile(_source, str(_BASE)+'#plan047-recovered-proof-dispatch', 'exec'), globals())

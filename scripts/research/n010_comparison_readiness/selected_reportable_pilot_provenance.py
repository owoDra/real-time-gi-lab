"""Plan154: full36 raw, quality and owned-memory proof; no acquisition."""
from pathlib import Path

import continuation_quality_provenance as C
from continuation_quality_provenance import P, R
import non_pt_raw_provenance as N
import hybrid_reference_provenance as H

SCOPE = R.RESULTS/'503-selected-reportable-timing-scope.json'
LOCK = R.RESULTS/'026-dynamic-execution-state-lock.json'


def inventory():
    scope = C.read(SCOPE)
    selected = C.read(R.RESULTS/'417-selected-pt-quality-command-description.json')
    non_pt = C.read(R.RESULTS/'511-full-non-pt-raw-intake-description.json')
    pt_cases = [row for row in selected['cases'] if row['spp'] == 1024]
    expected = {(cell,v,False) for cell in ('C1','C7','C8','C9') for v in (2,8)}
    expected |= {(cell,v,True) for cell in C.DYNAMIC for v in (2,8)}
    C.require(len(pt_cases) == 28 and {(r['cell'],r['vertices'],r['dynamic']) for r in pt_cases} == expected,
        'full selected28 PT identity differs')
    rows = []
    for case in pt_cases:
        number = case['retained_capture']
        proof = (R.RESULTS/f'{number}-continuation-pixel-pt-{case["cell"].lower()}.json'
            if number is not None else Path(case['result']))
        boundary = f'{"dynamic" if case["dynamic"] else "static"}-{case["cell"]}-pt-B{case["vertices"]}'
        rows.append(dict(id=boundary,kind='continuation-pt',cell=case['cell'],vertices=case['vertices'],
            dynamic=case['dynamic'],frames=case['frames'],path=str(proof),posthoc_reuse=number is not None,
            record_present=proof.is_file()))
    C.require(len(non_pt['rows']) == 8 and {r['boundary_id'] for r in non_pt['rows']} == set(N.SCOPE),
        'full non-PT8 identity differs')
    for case in non_pt['rows']:
        retained = 'retained_native' in case
        proof = Path(case['retained_native'] if retained else case['future_result'])
        rows.append(dict(id=case['boundary_id'],kind='raw-non-pt',cell=case['cell'],role=case['role'],
            dynamic=case['dynamic'],frames=case['frames'],path=str(proof),posthoc_reuse=retained,
            record_present=proof.is_file(),
            prior_posthoc_replay=case.get('explicit_posthoc_replay')))
    C.require(scope['full_union_count'] == 36 and len(rows) == 36
        and len({r['id'] for r in rows}) == 36
        and {r['id'] for r in rows} == {r['id'] for r in scope['rows']},
        'full original16/selected28 union36 differs')
    for row in rows:
        declared = next(r for r in scope['rows'] if r['id'] == row['id'])
        C.require((declared['cell'],declared['dynamic'],declared['frames']) ==
            (row['cell'],row['dynamic'],row['frames']), 'declared history scope differs')
    return rows


def verify(lock_path, references, work, inputs):
    C.require(Path(lock_path).resolve() == LOCK, 'full026 actual boundary lock required')
    rows = inventory()
    missing = [r['id'] for r in rows if not r['record_present']]
    inputs.update(R.INPUTS)
    C.require(not missing, 'missing actual full selected pilot records: '+','.join(missing))
    work = Path(work)
    C.require(not work.exists(), 'fresh full36 scoring output required; no overwrite/retry')
    work.mkdir()
    proofs = []
    for row in rows:
        path = Path(row['path'])
        if row['kind'] == 'continuation-pt':
            proof = C.verify_capture(path,LOCK,row['cell'],row['vertices'],1024,row['dynamic'],
                references=references,score_work=work/row['id'],reference_verifier=H.verify_reference)
        else:
            if row['posthoc_reuse']:
                prior = C.read(Path(row['prior_posthoc_replay']))
                C.require(prior['complete'] and prior['posthoc'] and not prior['native_executed']
                    and prior['source_capture'] == str(path) and prior['original507_failure_unchanged'],
                    'explicit507/509 post-hoc identity differs')
                for group in ('input_sha256','payload_sha256'):
                    for name,digest in prior[group].items():R.checked(name,digest)
            proof = N.verify_capture(path,row['id'],references=references,score_work=work/row['id'],
                reference_verifier=H.verify_reference)
        C.require(proof['execution_evidence_valid'] and proof['quality_evidence_valid']
            and not proof['accepted_timing'] and not proof['reference_admission'],
            'full pilot raw/quality/memory proof is incomplete')
        proofs.append(dict(boundary_id=row['id'],posthoc_reuse=row['posthoc_reuse'],proof=proof))
    R.unchanged();inputs.update(R.INPUTS)
    return dict(evidence_valid=True,quality_evidence_valid=True,full_union_count=36,
        pt_count=28,non_pt_count=8,precision='TIMING_INCONCLUSIVE',accepted_timing=False,
        rows=proofs,known_work_required_for_descriptive_handoff=False,
        limitation='Descriptive full pilots; no calibrated speed/equivalence or general superiority claim')

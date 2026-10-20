#!/usr/bin/env python3
"""Plan175: R1 slot views, verifier and scorer wrapper (plan174 eligibility; no rendering).

An R1 slot view copies (byte-identical) the retained original-oracle payloads up to the first R1
qualifying level and carries a truncated qualification whose classification is the
truthful ORIGINAL-screen result for those levels. R1 status lives separately in
r1-eligibility.json and is recomputed on every verification.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

import assess_r1_reference_eligibility as R1
import hybrid_reference_provenance as H
import score_hdr as S

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'out/research/n010-comparison-readiness'
SLOT_VIEWS = BASE/'r1-slot-views-v1'
PLAN = ROOT/'research/lanes/n010-comparison-readiness/experiments/175-r1-reference-integration.md'
_ORIGINAL_VERIFY = H.verify_reference  # bound once: callers may later route H through this module
_ORIGINAL_SCORE = S.score
R1_SLOTS = ('C1_T_B8','C2_T_B8','C3_T_B8','C4_T_B8','C5_T_B2','C5_T_B8','C6_T_B2','C6_T_B8')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_slot_view(slot,source):
    source = Path(source).resolve()
    out = SLOT_VIEWS/slot
    if out.exists():raise ValueError('refuse existing R1 slot view')
    if slot not in R1_SLOTS:raise ValueError('R1 applies only to the eight missing slots')
    q = json.loads((source/'qualification.json').read_text())
    if q['classification'] != 'INELIGIBLE':raise ValueError('R1 view needs an original-screen INELIGIBLE source')
    r1 = R1.assess(slot,source,None)
    if r1['classification'] != 'R1_STATISTICALLY_ELIGIBLE':raise ValueError('source is not R1 eligible')
    level = r1['r1_eligible_at_spp']
    levels = [l for l in q['levels'] if l['spp'] <= level]
    if [l['spp'] for l in levels][-1] != level:raise ValueError('R1 level missing from original levels')
    names = {'scene.n008'}
    for l in levels:
        names.update(l['all_payload_sha256'])
        names.update((f'n{l["spp"]}.meta.json',f'screen-n{l["spp"]}.json'))
    if (source/'prefix-import.json').exists():names.add('prefix-import.json')
    out.mkdir(parents=True)
    for name in sorted(names):
        shutil.copyfile(source/name,out/name)
        if sha(out/name)!=sha(source/name):raise ValueError('slot view copy changed bytes')
    view_q = copy.deepcopy(q)
    view_q['levels'] = levels
    view_q['classification'] = 'INELIGIBLE'
    view_q['r1_slot_view'] = dict(source_directory=str(source),source_qualification_sha256=sha(source/'qualification.json'),
        truncated_at_spp=level,note='classification is the unchanged original screen for the retained levels')
    view_q.pop('r1',None)
    (out/'qualification.json').write_text(json.dumps(view_q,indent=2,allow_nan=False)+'\n')
    r1_view = R1.assess(slot,out,None)
    if r1_view['r1_eligible_at_spp'] != level or r1_view['classification'] != 'R1_STATISTICALLY_ELIGIBLE':
        raise ValueError('R1 slot view does not reproduce source R1 result')
    record = dict(schema='n010-r1-slot-eligibility/1',slot=slot,eligibility_rule='R1',
        classification='R1_STATISTICALLY_ELIGIBLE',r1_eligible_at_spp=level,
        original_classification='INELIGIBLE',plan174_sha256=sha(R1.PLAN),
        assessor_sha256=sha(R1.__file__),qualification_sha256=sha(out/'qualification.json'),
        levels=r1_view['levels'],limits=r1_view['limits'])
    (out/'r1-eligibility.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    return record


def verify_reference(directory, cell, vertices, spec, inputs, require_eligible=True):
    directory = Path(directory)
    r1_path = directory.resolve()/'r1-eligibility.json'
    if not r1_path.exists():
        return _ORIGINAL_VERIFY(directory,cell,vertices,spec,inputs,require_eligible)
    proof = _ORIGINAL_VERIFY(directory,cell,vertices,spec,inputs,require_eligible=False)
    q = json.loads((directory.resolve()/'qualification.json').read_text())
    record = json.loads(r1_path.read_text())
    slot = f'{cell}_T_B{vertices}'
    fresh = R1.assess(slot,directory.resolve(),None)
    if (record['slot'],record['classification'],record['r1_eligible_at_spp']) != (slot,fresh['classification'],fresh['r1_eligible_at_spp']) \
            or record['levels'] != fresh['levels'] or record['qualification_sha256'] != sha(directory.resolve()/'qualification.json'):
        raise ValueError('R1 eligibility record differs from recomputation')
    if fresh['classification'] != 'R1_STATISTICALLY_ELIGIBLE' or q['levels'][-1]['spp'] != fresh['r1_eligible_at_spp']:
        raise ValueError('R1 reference is not eligible at its final retained level')
    inputs[str(r1_path)] = sha(r1_path)
    return dict(proof,eligibility_rule='R1',r1_eligibility_sha256=sha(r1_path),original_classification=q['classification'])


def score(capture,row,reference_work,output):
    reference_work = Path(reference_work)
    r1_path = reference_work.resolve()/'r1-eligibility.json'
    if not r1_path.exists():
        result = _ORIGINAL_SCORE(capture,row,reference_work,output)
        result['eligibility_rule'] = 'original'
        return result
    record = json.loads(r1_path.read_text())
    if record['classification'] != 'R1_STATISTICALLY_ELIGIBLE' or row['classification'] != 'INELIGIBLE' \
            or row['levels'][-1]['spp'] != record['r1_eligible_at_spp']:
        raise ValueError('R1 scoring requires a verified R1 slot view')
    # score_hdr's only eligibility use is its first-line gate; R1 replaces that gate.
    result = _ORIGINAL_SCORE(capture,dict(row,classification='STATISTICALLY_ELIGIBLE'),reference_work,output)
    result.update(eligibility_rule='R1',reference_original_classification=row['classification'],
                  r1_eligibility_sha256=sha(r1_path))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--slot',nargs=2,action='append',metavar=('SLOT','SOURCE'),required=True)
    a = ap.parse_args()
    for slot,source in a.slot:
        r = build_slot_view(slot,source)
        print(slot,r['classification'],r['r1_eligible_at_spp'])


if __name__ == '__main__':
    main()

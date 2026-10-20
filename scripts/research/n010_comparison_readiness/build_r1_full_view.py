#!/usr/bin/env python3
"""Plan175C: full24-slot reference view; 16 original160 targets + 8 R1 slot views, all verified."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess

import r1_reference_provenance as X

ROOT = X.ROOT
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
SOURCE_VIEW = RESULTS/'160-primary-direction-reference-view.json'
LOCK = RESULTS/'026-dynamic-execution-state-lock.json'
OUTPUT = RESULTS/'747-full-corpus-r1-reference-view.json'
WORK = X.BASE/'full-corpus-r1-view-v1'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    os.sched_setaffinity(0,{27})
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    if OUTPUT.exists() or WORK.exists():raise ValueError('refuse existing747 view')
    source = json.loads(SOURCE_VIEW.read_text());lock = json.loads(LOCK.read_text())
    rows = []
    for old in source['rows']:
        row = dict(old)
        if old['name'] in X.R1_SLOTS:
            if old['reference_state'] != 'PENDING_NOT_ADMITTED':raise ValueError('unexpected160 state for R1 slot')
            target = X.SLOT_VIEWS/old['name']
            q = json.loads((target/'qualification.json').read_text())
            row.update(target=str(target),computational_variant=q.get('computational_variant','original-full-prefix'),
                       reference_state='R1_STATISTICALLY_ELIGIBLE',eligibility_rule='R1',
                       superseded_160_target=old['target'])
        else:
            if old['reference_state'] != 'EXISTING_ELIGIBLE_REVERIFIED':raise ValueError('unexpected160 state')
            row.update(eligibility_rule='original')
        inputs = {}
        vertices = int(row['transport'][-1])
        proof = X.verify_reference(Path(row['target']),row['cell'],vertices,lock['cells'][row['cell']],inputs)
        if proof['eligibility_rule'] != row['eligibility_rule']:raise ValueError('eligibility rule mismatch '+row['name'])
        row['verification'] = proof
        rows.append(row)
    WORK.mkdir(parents=True)
    for row in rows:(WORK/row['name']).symlink_to(row['target'])
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip()
    view = dict(schema='n010-full-corpus-r1-reference-view/1',complete=True,all_pass=True,gpu_run=False,
        classification='FULL_24_SLOT_REFERENCE_VIEW_16_ORIGINAL_8_R1',eligible_for_comparison=True,
        plan='175-r1-reference-integration.md',source_commit=commit,work=str(WORK),
        source_view_sha256=sha(SOURCE_VIEW),lock_sha256=sha(LOCK),rows=rows,
        retained_eligible_count=sum(r['eligibility_rule']=='original' for r in rows),
        r1_eligible_count=sum(r['eligibility_rule']=='R1' for r in rows),pending_count=0,full_corpus_eligible=True,
        scope='R1 (plan174) is a disclosed post-hoc amendment; original-screen INELIGIBLE is retained for the eight R1 slots',
        tests='NOT_RUN')
    OUTPUT.write_text(json.dumps(view,indent=2,allow_nan=False)+'\n')
    print(view['classification'],view['retained_eligible_count'],view['r1_eligible_count'])


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Post-hoc generic/full-control evidence replay; no new native acquisition."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

OUTPUT=D.RESULTS/'233-posthoc-all-split-general-controls-replay.json'
NAMES={222:'222-all-split-general-transport-equivalence.json',223:'223-all-split-general-transport-equivalence.json',224:'224-all-split-exporter-build.json',225:'225-all-split-full-sidedness-controls.json',226:'226-all-split-full-deterministic-controls.json',227:'227-all-split-original-a7-cost-pilot.json',229:'229-all-split-original-a7-cost-pilot.json',230:'230-all-split-original-a7-full-control.json',231:'231-posthoc-original-a7-retained-control.json',232:'232-all-split-original-a6c-cpu-cost.json'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    if OUTPUT.exists():raise ValueError('refuse existing replay')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2)
    inputs={str(Path(__file__).resolve()):sha(__file__)};verified={};rs={};terminal={}
    for n,name in NAMES.items():
        p=D.RESULTS/name;inputs[str(p)]=sha(p);r=json.loads(p.read_text());rs[n]=r
        if 'ACQUIRING' in r['classification']:raise ValueError('unsealed acquisition remains')
        for key in ('input_sha256','payload_sha256'):
            for p,h in r.get(key,{}).items():
                if p in verified and verified[p]!=h:raise ValueError('conflicting immutable payload')
                if p not in verified and sha(p)!=h:raise ValueError('payload changed: '+p)
                verified[p]=h
        for p in r.get('payload_sha256',{}):
            if not p.endswith('.resources.json'):continue
            receipt=json.loads(Path(p).read_text());proc=Path('/proc')/str(receipt['pid'])/'stat'
            if proc.exists():
                row=proc.read_text().rsplit(')',1)[1].split()
                if int(row[19])==receipt['start_ticks'] and row[0]!='Z':raise ValueError('native/compile still live')
            if len(receipt['affinity'])!=1 or receipt['nice']!=15:raise ValueError('low-load scope differs')
            terminal[p]=dict(pid=receipt['pid'],start_ticks=receipt['start_ticks'],terminal=True)
    if rs[222]['complete'] or rs[227]['complete'] or rs[230]['complete']:raise ValueError('historical failures relabelled')
    if not rs[223]['per_sample_legacy_component_depth_bits_exact'] or not rs[224]['all_pass']:raise ValueError('actual equivalence/build proof absent')
    old=json.loads((D.RESULTS/'218-all-split-path-mixture-diagnosis.json').read_text())
    old_rows=json.loads(next(Path(p) for p in old['payload_sha256'] if p.endswith('/data.json')).read_text())
    new_rows=json.loads(next(Path(p) for p in rs[223]['payload_sha256'] if p.endswith('/data.json')).read_text())
    if len(new_rows)!=32:raise ValueError('new equivalence scope differs')
    for row in new_rows:
        prior=next(v for v in old_rows if all(v[k]==row[k]for k in ('x','y','seed')))
        for k in ('mean','second','mixture_mean','mixture_second','mixture_depth_mean'):
            if np.array(row[k],dtype='<f8').tobytes()!=np.array(prior[k],dtype='<f8').tobytes():raise ValueError('retained218 statistics differ')
    scenes=[]
    for n in (225,226):
        r=rs[n]
        if not r['complete'] or not r['all_pass']:raise ValueError('full deterministic controls absent')
        folder=D.OUT/('all-split-full-sidedness-v1' if n==225 else 'all-split-full-deterministic-v1')
        for row in r['rows']:
            if not row['pass_'] or row['spp']!=64 or row['full_frame']!=[128,96] or row['seeds']!=list(D.SEEDS):raise ValueError('original full scope differs')
            for p in row['payloads']:
                actual=folder/(row['name']+p['payload']);original=D.OUT/'sampler-validation-v1/rqmc'/(row['name']+p['payload'])
                if actual.read_bytes()!=original.read_bytes():raise ValueError('full original payload bytes differ')
            scenes.append(row['name'])
    if not rs[229]['cost_pass'] or not rs[231]['complete'] or not rs[231]['all_pass'] or not rs[231]['physical_checks']['pass'] or not rs[231]['independent_iid']['pass_']:raise ValueError('original full A7 control absent')
    scenes.append('A7')
    all_original=json.loads((D.RESULTS/'022-cached-oracle-equivalence.json').read_text())
    control_names={p.name.removesuffix('.meta.json') for p in (D.OUT/'sampler-validation-v1/rqmc').glob('*.meta.json')}
    if len(control_names)!=17 or not control_names.issubset({r['name']for r in all_original['rows']}):raise ValueError('original seventeen control artifacts differ')
    pending=sorted(control_names-set(scenes))
    if len(scenes)!=10 or len(pending)!=7 or len(set(scenes))!=10:raise ValueError('original full control inventory differs')
    if not rs[232]['complete'] or rs[232]['physical_control_decision']!='NOT_APPLICABLE_COST_ONLY':raise ValueError('A6c cost pilot not properly scoped')
    if rs[232]['estimated_original8192_cpu']!=1024*rs[232]['child_cpu_seconds']:raise ValueError('A6c cost projection differs')
    for p,h in verified.items():
        if sha(p)!=h:raise ValueError('payload changed during replay')
    result=dict(schema='n010-posthoc-all-split-general-controls-replay/1',complete=True,gpu_run=False,reference_admission=False,classification='POSTHOC_IDENTITIES_TEN_ORIGINAL_FULL_CONTROLS_AND_TERMINATION_REPLAYED_NO_ADMISSION',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=inputs,verified_payloads=verified,native_compiler_terminal_receipts=terminal,
        inventory_note='Original022 catalog has20 entries:17 control scenes and3 corpus checkpoints. Filter by exact original control metadata artifacts; first post-hoc inventory mistakenly counted all20 and stopped without output.',retained218_statistics_bit_exact=True,equivalence_scored_indices=32*8192,original_full_controls_pass=scenes,original_full_controls_pending=pending,
        scope='Ten of17 original full scenes only; failed222/227/230 retained, no native retry/A6c physical PASS/all-state/prefix/whole-frame qualification',tests='NOT_RUN; post-hoc scientific evidence replay only')
    OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'complete':True,'verified_payloads':len(verified),'native_compiler_receipts':len(terminal),'original_full_controls_pass':scenes,'pending':pending},indent=2))

if __name__=='__main__':main()

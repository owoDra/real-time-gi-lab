#!/usr/bin/env python3
"""Plan 059: exact short C7 diagnostic under user-declared natural idle."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RESULTS=ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN=RESULTS.parent/'experiments/059-natural-idle-c7-observation.md'
OUTPUT=RESULTS/'197-natural-idle-c7-precision-diagnostic.json'


def snapshot():
    clients={};inaccessible=0
    start=time.monotonic_ns()
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            if p.stat().st_uid!=os.getuid():continue
            name=(p/'comm').read_text().strip()
            files=list((p/'fdinfo').iterdir())
        except OSError:
            inaccessible+=1;continue
        for f in files:
            try:data=f.read_text()
            except OSError:continue
            if 'drm-client-id:' not in data:continue
            fields={line.split(':',1)[0]:line.split(':',1)[1].strip()
                    for line in data.splitlines() if ':' in line}
            engines={k:int(v.split()[0]) for k,v in fields.items()
                     if k.startswith('drm-engine-') and v.endswith(' ns')}
            if not engines:continue
            key=fields.get('drm-pdev','unknown')+'/'+fields['drm-client-id']
            client=clients.setdefault(key,{'device':fields.get('drm-pdev'),
                'client_id':fields['drm-client-id'],'processes':[], 'engines_ns':{}})
            owner={'pid':int(p.name),'comm':name}
            if owner not in client['processes']:client['processes'].append(owner)
            for k,v in engines.items():client['engines_ns'][k]=max(v,client['engines_ns'].get(k,0))
    return {'start_monotonic_ns':start,'end_monotonic_ns':time.monotonic_ns(),
            'inaccessible_same_uid_pids':inaccessible,'clients':clients}


def main():
    if OUTPUT.exists():raise ValueError('refuse existing idle diagnostic')
    parent=HERE/'diagnose_deferred_c7_precision.py'
    committed=subprocess.check_output(['git','show','b9b027c:scripts/research/n010_reference_sampling/diagnose_deferred_c7_precision.py'])
    if parent.read_bytes()!=committed:raise ValueError('frozen plan-058 driver changed')
    source=committed.decode();edits=[]
    for old,new in (
        ('196-deferred-c7-precision-diagnostic.json',OUTPUT.name),
        ('deferred-c7-precision-diagnostic-v1','natural-idle-c7-precision-diagnostic-v1'),
        ('Path(__file__).resolve(),PLAN,prior,',
         'Path(__file__).resolve(),PLAN,_idle_plan,Path(_parent_wrapper),prior,')):
        if source.count(old)!=1:raise ValueError('idle dispatch anchor differs')
        source=source.replace(old,new);edits.append((old,new))
    restored=source
    for old,new in reversed(edits):restored=restored.replace(new,old)
    if restored!=committed.decode():raise ValueError('whole driver inverse differs')
    proof={'whole_plan058_driver_inverse_exact':True,
        'parent_source_sha256':hashlib.sha256(committed).hexdigest(),
        'generated_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'dispatch_edits':[{'old':a,'new':b} for a,b in edits]}
    before=snapshot()
    try:
        exec(compile(source,str(parent)+'#plan059','exec'),
             {'__name__':'__main__','__file__':str(Path(__file__).resolve()),
              '_idle_plan':PLAN,'_parent_wrapper':str(parent)})
    finally:
        after=snapshot()
        if OUTPUT.exists():
            d=json.loads(OUTPUT.read_bytes());deltas={}
            for key,a in after['clients'].items():
                if key not in before['clients']:continue
                b=before['clients'][key]
                deltas[key]={k:(v-b['engines_ns'][k] if v>=b['engines_ns'][k] else 'COUNTER_RESET')
                             for k,v in a['engines_ns'].items() if k in b['engines_ns']}
            d['natural_idle_observation']={'user_declared_idle':True,
                'before':before,'after':after,'surviving_client_engine_deltas_ns':deltas,
                'created_clients':sorted(set(after['clients'])-set(before['clients'])),
                'disappeared_clients':sorted(set(before['clients'])-set(after['clients'])),
                'dispatch_proof':proof,
                'scope':'Same-UID coarse DRM accounting only; no global-quiescence, exact per-query overlap or causal claim. No samples excluded.'}
            OUTPUT.write_text(json.dumps(d,indent=2)+'\n')


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Conditional fixed sixteen-case hybrid diagnostic; no reference admission."""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import time
from reference_provenance import ROOT, RESULTS, sha


def run(args):
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing suite')
    args.work.mkdir(parents=True)
    ctypes.CDLL(None).prctl(15,b'n010_hyb_suite',0,0,0)
    cases=[(c,b,i)for c,b in [('C7',2),('C1',2),('C7',8),('C1',8)]for i in range(4)]
    script=ROOT/'scripts/research/n010_comparison_readiness/acquire_hybrid_reference_diagnostic.py'
    build=ROOT/'out/research/n010-comparison-readiness/hybrid-oracle-build-v1'
    manifest=RESULTS/'095-hybrid-oracle-build.json'
    proof=json.loads(manifest.read_text())
    if not proof.get('all_pass'):raise ValueError('requires complete build')
    if any(sha(build/name)!=h for name,h in proof['generated_sha256'].items()):
        raise ValueError('candidate build identities differ')
    files=[Path(__file__),script,manifest,RESULTS.parent/'experiments/026-hybrid-full-numerical-suite.md']
    files+=[build/name for name in proof['generated_sha256']]
    inputs={str(p.resolve()):sha(p)for p in files}
    result=dict(schema='n010-hybrid-full-conformance/1',complete=False,all_pass=False,gpu_run=False,
        eligible_for_references=False,classification='DIAGNOSTIC_ONLY_NOT_REFERENCE_ELIGIBILITY',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=inputs,frozen_cases=cases,spp=8192,batch=16,cpu_fallback_threads=16,
        thresholds={'max_absolute_mean_and_moment':1e-10,'indirect_nrmse':1e-8,'counter_disagreements':0},
        rows=[],scope='Complete fixed numerical suite only. Physical, all-state and exact-prefix checks still required. No reference transition, scoring exclusions, or GI timing acceptance.')
    status=args.work/'status.json'
    def save(phase):
        status.write_text(json.dumps(dict(phase=phase,complete=result['complete'],rows=len(result['rows']),updated_unix_seconds=time.time()),indent=2)+'\n')
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    def identities():
        if any(sha(Path(p))!=h for p,h in inputs.items()):
            raise ValueError('frozen suite input changed')
    def audit_child(path,case):
        d=json.loads(path.read_text());c,b,i=case
        if not d.get('complete')or not d.get('all_pass'):
            raise ValueError('case failed fixed numerical gates')
        if (d['cell'],d['vertices'],d['seed'],d['spp'],d['batch'],d['cpu_fallback_threads'])!=(c,b,(305419896,2596069104,81985529216486895,18364758544493064720)[i],8192,16,16):
            raise ValueError('case identity differs')
        for p,h in d['input_sha256'].items():
            if sha(Path(p))!=h:raise ValueError('case frozen input changed')
        for name in ('hybrid.spv','phos-n010-hybrid-reference'):
            if d['input_sha256'].get(str((build/name).resolve()))!=proof['generated_sha256'][name]:
                raise ValueError('case candidate build differs')
        directory=Path(d['gpu_command'][-1]).parent
        for p,h in d['payload_sha256'].items():
            if sha(directory/p)!=h:raise ValueError('case output changed')
        return d
    save('WAITING_FOR_FULL_FRAME_DEEP_FEASIBILITY')
    try:
        while True:
            identities()
            if args.prior.exists():
                p=json.loads(args.prior.read_text())
                if p.get('complete'):
                    if not p.get('all_pass'):
                        raise ValueError('096 dependency failed; no suite dispatch')
                    prior=audit_child(args.prior,('C1',8,0))
                    inputs[str(args.prior.resolve())]=sha(args.prior)
                    break
            time.sleep(15)
        for index,case in enumerate(cases):
            identities();c,b,i=case
            row={'case_index':index,'cell':c,'vertices':b,'seed_index':i,'pass':False}
            result['rows'].append(row);save('CASE_'+str(index))
            if case==('C1',8,0):
                child=args.prior;row['reused_prior_case']=True
                audit_child(child,case)
            else:
                child=args.work/f'{c}-B{b}-seed{i}.json'
                command=[str(ROOT/'out/research/n010-comparison-readiness/venv/bin/python'),str(script),
                    '--cell',c,'--vertices',str(b),'--spp','8192','--seed-index',str(i),'--batch','16',
                    '--threads','16','--elapsed-limit','3600','--work',str((args.work/f'{c}-B{b}-seed{i}').resolve()),'--output',str(child.resolve())]
                row['command']=command;save('CASE_'+str(index))
                with (args.work/f'{c}-B{b}-seed{i}.stdout').open('w')as stdout,(args.work/f'{c}-B{b}-seed{i}.stderr').open('w')as stderr:
                    p=subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr)
                row['returncode']=p.returncode
                result['gpu_run']=True
                if child.exists():row['result_sha256']=sha(child)
                save('CASE_'+str(index))
                if p.returncode:raise ValueError('case execution/conformance failed; no retry')
                audit_child(child,case)
            row.update(result=str(child.resolve()),result_sha256=sha(child));row['pass']=True
            result['gpu_run']=True;save('CASE_'+str(index)+'_PASS')
            print(c,b,i,'PASS',flush=True)
        identities();result['all_pass']=len(result['rows'])==16 and all(r['pass']for r in result['rows'])
    except (ValueError,OSError,KeyError)as error:
        result['failure']=str(error)
    result['complete']=True;save('COMPLETE_PASS'if result['all_pass']else 'COMPLETE_FAILED')
    print('FULL NUMERICAL PASS'if result['all_pass']else 'FULL NUMERICAL FAIL',flush=True)
    return 0 if result['all_pass']else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior',type=Path,default=RESULTS/'096-hybrid-full-frame-deep-conformance.json')
    p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(p.parse_args()))

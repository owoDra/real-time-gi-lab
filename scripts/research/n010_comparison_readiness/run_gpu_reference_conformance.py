#!/usr/bin/env python3
"""Freeze and retain the sixteen Amendment 7 full-level diagnostic cases."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import ctypes
from reference_provenance import ROOT,RESULTS,sha,verify_reference
import qualify_references as Q

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--elapsed-limit',type=int,default=120)
    parser.add_argument('--prior',type=Path,help='Retain the completed ordered prefix of a terminal resource-limited diagnostic')
    args=parser.parse_args()
    if not 60<=args.elapsed_limit<=1800:raise ValueError('explicit elapsed limit required')
    ctypes.CDLL(None).prctl(15,b'n010_num_check',0,0,0)
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing conformance acquisition')
    args.work.mkdir(parents=True)
    script=Path(__file__).with_name('acquire_gpu_reference_diagnostic.py')
    paths=[script,Path(__file__),ROOT/'build/n010-cpu/phos-n010-gpu-reference',
        ROOT/'out/research/n010-comparison-readiness/gpu-oracle-compile-v3/n010_gpu_oracle.spv',
        Q.NET,Q.BINARY,RESULTS/'009-iid-precision-confirmation.json',
        RESULTS.parent/'experiments/016-amendment-7-gpu-reference-feasibility.md']
    inputs={str(p.resolve()):sha(p) for p in paths}
    prior=None
    if args.prior:
        prior=json.loads(args.prior.read_text())
        if not prior['complete'] or prior['all_pass'] or len(prior['rows'])!=13 or not all(r['pass'] for r in prior['rows'][:12]) or prior['rows'][12]['pass']:
            raise ValueError('expected terminal twelve-case prefix followed by resource failure')
        if prior['input_sha256'][str(paths[2])]!=sha(paths[2]) or prior['input_sha256'][str(paths[3])]!=sha(paths[3]):raise ValueError('retained prefix numerical implementation differs')
        stopped=json.loads(Path(prior['rows'][12]['result']).read_text())
        if not stopped.get('gpu_timeout') or stopped.get('max_abs_mean') is not None:raise ValueError('expected unfinished resource-limited case')
        inputs[str(args.prior.resolve())]=sha(args.prior)
    result={'schema':'n010-gpu-reference-full-conformance/1','complete':False,'all_pass':False,
        'gpu_run':True,'eligible_for_references':False,'classification':'DIAGNOSTIC_ONLY_NOT_REFERENCE_ELIGIBILITY',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':inputs,'frozen_cases':[[c,v,i] for c,v in (('C7',2),('C1',2),('C7',8),('C1',8)) for i in range(4)],
        'spp':8192,'batch':16,'elapsed_limit':args.elapsed_limit,'rows':[],
        'stop':'Stop at first failed numerical/runtime gate and retain all attempts. Full controls/all-state/prefix admission gates remain separate.'}
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    env=os.environ.copy();env['LD_LIBRARY_PATH']=':'.join(filter(None,[env.get('NIX_LD_LIBRARY_PATH'),env.get('LD_LIBRARY_PATH')]))
    python=str(ROOT/'out/research/n010-comparison-readiness/venv/bin/python')
    lock=json.loads((RESULTS/'016-corpus-state-lock.json').read_text())
    if prior and prior['frozen_cases']!=result['frozen_cases']:raise ValueError('retained fixed case schedule differs')
    for position,(cell,vertices,index) in enumerate(result['frozen_cases']):
        if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('frozen numerical acquisition dependency changed')
        # Retain and audit the already executed first 8192 case, without re-running
        # its GPU calculation. Its historical wrapper hash remains historical.
        if prior and position<12:
            retained=prior['rows'][position]
            if (retained['cell'],retained['vertices'],retained['seed_index'])!=(cell,vertices,index):raise ValueError('completed prefix is not in fixed schedule order')
            path=Path(retained['result'])
            if sha(path)!=retained['sha256']:raise ValueError('retained numerical result changed')
            row=json.loads(path.read_text());gpu=Path(row['gpu_command'][-1]).parent
            for name,digest in row['payload_sha256'].items():
                if sha(gpu/name)!=digest:raise ValueError('retained complete numerical payload changed')
            audit=result.setdefault('retained_case_provenance_audit',{})
            directory=ROOT/'out/research/n010-comparison-readiness/references-v1'/f'{cell}_T_B{vertices}'
            if not str(directory) in result.setdefault('audited_cpu_directories',[]):
                verify_reference(directory,cell,vertices,lock['cells'][cell],audit,require_eligible=False)
                result['audited_cpu_directories'].append(str(directory))
        elif (cell,vertices,index)==('C7',2,0):
            path=RESULTS/'073-gpu-reference-c7-b2-8192-seed0.json';row=json.loads(path.read_text())
            audit={};directory=ROOT/'out/research/n010-comparison-readiness/references-v1/C7_T_B2'
            verify_reference(directory,cell,vertices,lock['cells'][cell],audit,require_eligible=False)
            gpu=ROOT/'out/research/n010-comparison-readiness/gpu-reference-diagnostic-v2'
            if row['input_sha256'][str(paths[2])]!=sha(paths[2]) or row['input_sha256'][str(paths[3])]!=sha(paths[3]):raise ValueError('retained first GPU case differs from this numerical implementation')
            for name,digest in row['payload_sha256'].items():
                if sha(gpu/name)!=digest:raise ValueError('retained diagnostic payload changed')
            result['retained_case_provenance_audit']=audit
        else:
            name=f'{cell}-B{vertices}-seed{index}'
            path=args.work/(name+'.json')
            command=[python,str(script),'--cell',cell,'--vertices',str(vertices),'--seed-index',str(index),
                '--spp','8192','--batch','16','--elapsed-limit',str(args.elapsed_limit),'--work',str(args.work/name),'--output',str(path)]
            with (args.work/(name+'.stdout')).open('w') as stdout,(args.work/(name+'.stderr')).open('w') as stderr:
                process=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
            if not path.exists():
                result['failure']={'case':[cell,vertices,index],'returncode':process.returncode,'reason':'child output absent; logs retained'}
                break
            row=json.loads(path.read_text())
        result['rows'].append({'cell':cell,'vertices':vertices,'seed_index':index,'result':str(path),
            'sha256':sha(path),'pass':row['complete'] and row['all_pass'],
            'max_abs_mean':row.get('max_abs_mean'),'max_abs_moment':row.get('max_abs_moment'),
            'indirect_nrmse':row.get('indirect_nrmse'),'failure':row.get('failure')})
        save();print(cell,vertices,index,'PASS' if row['all_pass'] else 'FAIL',flush=True)
        if not row['all_pass']:break
    result['complete']=True;result['all_pass']=len(result['rows'])==16 and all(r['pass'] for r in result['rows'])
    save();print('FULL NUMERICAL DIAGNOSTIC PASS' if result['all_pass'] else 'NUMERICAL DIAGNOSTIC FAIL',flush=True)
    raise SystemExit(0 if result['all_pass'] else 2)

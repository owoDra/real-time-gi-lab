#!/usr/bin/env python3
"""Plan134: replay current six-gate inputs and the actual selected execution scope."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import continuation_quality_provenance as C
from continuation_quality_provenance import P,R
import hybrid_reference_provenance as H
import reportable_timing_provenance as T

PLAN=R.RESULTS.parent/'experiments/134-selected-scope-readiness-audit.md'
ORIGINAL=Path(__file__).with_name('readiness_preflight.py')
ORIGINAL_SHA='87985c62edd7ad9a7a8e931e0f36264d939a4e4774507fe0653ac9d483857e2c'
LOCK=R.RESULTS/'026-dynamic-execution-state-lock.json'
VIEW=R.RESULTS/'160-primary-direction-reference-view.json'
DESCRIPTION=R.RESULTS/'425-selected-execution-audit-description.json'
AUDIT=R.RESULTS/'426-selected-scope-readiness-audit.json'
GATES=('refs','correctness','dynamic','static','provenance')


def selected():
    description=C.read(R.RESULTS/'417-selected-pt-quality-command-description.json')
    cases=[r for r in description['cases'] if r['spp']==1024]
    expected={(cell,v,False) for cell in ('C1','C7','C8','C9') for v in (2,8)}
    expected|={(cell,v,True) for cell in C.DYNAMIC for v in (2,8)}
    C.require(len(cases)==28 and {(r['cell'],r['vertices'],r['dynamic']) for r in cases}==expected,
              'exact selected execution scope differs')
    for row in cases:
        if row['retained_capture'] is not None:
            number=row['retained_capture']
            row['proof_path']=str(R.RESULTS/f'{number}-continuation-pixel-pt-{row["cell"].lower()}.json')
        else:row['proof_path']=row['result']
    return cases


def program():
    original=R.checked(ORIGINAL,ORIGINAL_SHA).decode()
    source,edits=original,[]
    def change(before,after):
        nonlocal source
        C.require(source.count(before)==1 and after not in source,'nonunique audit overlay')
        source=source.replace(before,after,1);edits.append((before,after))
    change('from reference_provenance import physical_proof,verify_reference',
           'from reference_provenance import physical_proof\nfrom hybrid_reference_provenance import verify_reference')
    begin=source.index(' def calibration():\n')
    end=source.index(" gate('demonstrated_full_renderer_timing_capability',calibration)",begin)
    change(source[begin:end],''' def calibration():
  return _selected_timing(a.lock,result['inputs'])
''')
    change(" gate('demonstrated_full_renderer_timing_capability',calibration)",
           " gate('valid_timing_pilot_and_selected_execution',calibration)")
    change("'schema':'n010-readiness-preflight/1'","'schema':'n010-selected-scope-readiness-audit/1'")
    change("if all(g['pass'] for g in result['gates']):result['classification']='READY_FOR_LANE_M_FIRST_COHORT'",
           "if all(g['pass'] for g in result['gates']):result['classification']='SUPPORTED_INPUTS_VALID_FINAL_TIMING_INTAKE_PENDING'")
    change(" a.output.write_text(json.dumps(result,indent=2)+'\\n');print(result['classification'])",
           " _finish(result)\n print(result['classification'])")
    def bodies(text):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text))
                if isinstance(n,ast.FunctionDef) and n.name in GATES}
    C.require(bodies(source)==bodies(original) and set(bodies(source))==set(GATES),
              'one of the five non-timing gate bodies changed')
    restored=source
    for before,after in reversed(edits):
        C.require(restored.count(after)==1,'audit inverse count differs')
        restored=restored.replace(after,before,1)
    C.require(restored==original,'complete original source inverse differs')
    return source,dict(whole_source_inverse_exact=True,other_five_gate_asts_identical=True,
        original_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(source.encode()).hexdigest(),
        final_selected_history_timing_intake_implemented=False,all_split_reference_dispatch_implemented=False)


def bind_pilots():
    static=C.read(R.RESULTS/'415-retained-pt-ladder-proof-replay.json')
    dynamic=C.read(R.RESULTS/'423-retained-controlled-dynamic-cohort-proof.json')
    for proof in (static,dynamic):
        C.require(proof['complete'],'terminal retained replay proof required')
        for group in ('input_sha256','payload_sha256'):
            for name,digest in proof[group].items():R.checked(name,digest)
    # Paths are fixed by the two actual proof outputs, never caller booleans.
    static_paths=[R.BASE/'retained-pt-ladder-proof-v1'/f'{cell}-canonical-pilot.json'
                  for cell in ('C1','C7','C8','C9')]
    for path in static_paths:
        C.require(str(path) in static['payload_sha256'],'static pilot not bound by actual415 output')
    dynamic_path=Path(dynamic['validation']['canonical_path'])
    C.require(str(dynamic_path) in dynamic['payload_sha256'],'dynamic pilot not bound by actual423 output')
    return static_paths,dynamic_path


def execution(cases):
    rows=[]
    failed=False
    for case in cases:
        path=Path(case['proof_path'])
        row=dict(case=case['case'],path=str(path),frames=case['frames'])
        if not path.exists():row['status']='MISSING_ACTUAL_CAPTURE'
        elif failed:row['status']='NOT_REPLAYED_AFTER_PRIOR_PROOF_FAILURE'
        else:
            try:
                row['proof']=C.verify_capture(path,LOCK,case['cell'],case['vertices'],1024,case['dynamic'])
                row['status']='ACTUAL_EXECUTION_REPLAY_VALID'
            except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
                row.update(status='ACTUAL_EXECUTION_PROOF_INVALID',reason=str(error));failed=True
        rows.append(row)
    return rows


def inventory(view,lock):
    rows=[]
    for cell in lock['cells']:
        for vertices in (2,8):
            directory=Path(view['work'])/f'{cell}_T_B{vertices}'
            row=dict(cell=cell,vertices=vertices,directory=str(directory))
            try:
                entry=next(r for r in view['rows'] if r['name']==directory.name)
                C.require(directory.is_symlink() and str(directory.resolve())==entry['target'],'view target differs')
                row['proof']=H.verify_reference(directory,cell,vertices,lock['cells'][cell],R.INPUTS)
                row['status']='ELIGIBLE_CHAIN_VERIFIED'
            except (ValueError,OSError,KeyError,AssertionError,StopIteration,subprocess.SubprocessError) as error:
                row.update(status='NOT_ELIGIBLE_OR_PROOF_INCOMPLETE',reason=str(error))
            rows.append(row)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--describe',action='store_true');mode.add_argument('--audit',action='store_true')
    args=ap.parse_args()
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),'one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180)
    start,cpu=time.monotonic(),time.process_time()
    output=DESCRIPTION if args.describe else AUDIT
    C.require(not output.exists(),'fresh output required; never overwrite/retry')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])==R.checked(path),
                  'commit exact source/recipe before audit')
    source,inverse=program()
    cases=selected()
    detail=dict(source_composition=inverse,selected_cases=cases,accepted_timing=False,
                final_handoff_admitted=False,scope='Current supported inputs; final selected-history timing/all-split intake still required')
    lock,view=C.read(LOCK),C.read(VIEW)
    if args.describe:
        result=dict(schema='n010-selected-execution-audit-description/1',complete=True,
            classification='SOURCE_AND_SCOPE_METADATA_ONLY',native_executed=False,all_pass=False,detail=detail)
    else:
        static_paths,dynamic_path=bind_pilots()
        detail['references']=inventory(view,lock)
        detail['execution']=execution(cases)
        def timing(lock_path,inputs):
            # Missing proof must not become a valid inconclusive observation.
            try:
                legacy=T.verify_timing_pilot(lock_path,inputs)
                detail['timing']=dict(evidence_valid=True,precision='TIMING_INCONCLUSIVE',legacy_pilot=legacy)
            except (ValueError,OSError,KeyError,AssertionError) as error:
                detail['timing']=dict(evidence_valid=False,precision='NOT_EVALUABLE',reason=str(error))
            missing=[r['case'] for r in detail['execution'] if r['status']!='ACTUAL_EXECUTION_REPLAY_VALID']
            C.require(detail['timing']['evidence_valid'] and not missing,
                      f'complete valid timing pilot required; selected execution slots missing/invalid={len(missing)}')
            return dict(evidence_valid=True,timing_classification='TIMING_INCONCLUSIVE',accepted_timing=False,
                        limitation='Legacy known-work plus actual selected execution; no history-frame calibration or final intake')
        def finish(result):
            result.update(complete=True,gpu_run=False,posthoc=True,selected_scope=detail)
        previous=sys.argv
        sys.argv=[str(ORIGINAL),'--lock',str(LOCK),'--references',view['work'],'--reference-view-record',str(VIEW),
            '--calibration',str(T.PILOT),'--dynamic-pilots',str(dynamic_path),'--static-pilots',
            *map(str,static_paths),'--output',str(output)]
        scope=dict(__name__='__main__',__file__=str(ORIGINAL),_selected_timing=timing,_finish=finish)
        try:
            exec(compile(source,str(ORIGINAL)+'#plan134','exec'),scope)
        except SystemExit as exit:
            C.require(exit.code==2,'intermediate audit must never grant final readiness')
        finally:sys.argv=previous
        result=scope['result']
        for name,digest in result['inputs'].items():R.checked(name,digest)
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename and Path(filename).resolve().is_relative_to(R.ROOT/'scripts/research'):R.checked(filename)
    R.unchanged()
    elapsed,used=time.monotonic()-start,time.process_time()-cpu
    C.require(elapsed<180 and used<120,'registered resource limit exceeded')
    result.update(source_commit=commit,input_sha256=R.INPUTS,accepted_timing=False,all_pass=False,
        execution=dict(elapsed_seconds=elapsed,cpu_seconds=used,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),numerical_threads=1,
            cpu_limit_seconds=120,elapsed_limit_seconds=180,address_space_limit_bytes=2*1024**3),
        tests='NOT_RUN; current scientific evidence/provenance audit only')
    with output.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__=='__main__':main()

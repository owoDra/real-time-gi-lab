#!/usr/bin/env python3
"""Plan165: original complete78 state/prefix science for private execution."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess

import acquire_compensated_state_prefix as S
import prepare_thread_private_cli as B
from acquire_compensated_state_prefix import D,L,C

PLAN=D.RESULTS.parent/'experiments/165-private-full-state-prefix-qualification.md'
DESCRIPTION=D.RESULTS/'629-private-state-prefix-description.json'
BASE=D.OUT/'private-state-prefix-v1'
SUMMARY=D.RESULTS/'708-private-all-state-prefix-summary.json'
EXECUTION='thread-private-audit-v2'


def prerequisites():
    S.prerequisites()
    prep,build=L.bind(B.PREP),L.bind(B.BUILD)
    pair=L.bind(D.RESULTS/'625-thread-private-full-frame-equivalence-summary.json')
    if not prep['source_preparation_valid'] or not build['build_valid'] or not pair['all_pass']:
        raise ValueError('complete private source/build/equivalence required')
    if not pair['all_six_payload_bytes_and_exported_audits_exact'] or pair['actual_affinity']!=[31]:
        raise ValueError('registered full C1 single-core equivalence required')
    for row in prep['rows']:D.checked(Path(row['binary']),build['payload_sha256'][row['binary']])
    return build


def program():
    parent,old_edits,old_proof=S.program();source=parent;edits=[]
    def change(before,after):
        nonlocal source
        source=D.once(source,before,after);edits.append((before,after))
    change("f'{532+3*case+phase:03d}-compensated-state-prefix-{label}.json'",
           "f'{630+3*case+phase:03d}-private-state-prefix-{label}.json'")
    change("'compensated-full-deterministic-v1/build/n010_compensated_exporter' if phase == 0\n"
           "                      else 'compensated-prefix-build-v1/n010_compensated_prefix'",
           "'thread-private-reference-build-v2/n010_thread_private_exporter' if phase == 0\n"
           "                      else 'thread-private-reference-build-v2/n010_thread_private_prefix'")
    change("str(spp), '--threads', '1']","str(spp), '--threads', '4']")
    for kind in ('all-state-prefix-summary','state-prefix-step'):
        change("schema='n010-compensated-"+kind+"/1'",
               "schema='n010-private-"+kind+"/1', execution_variant="+repr(EXECUTION))
    change("    if not data['terminal_identity_verified'] or data['numerical_variant'] != 'compensated-raw-target-v1':",
           "    if (not data['terminal_identity_verified'] or data['numerical_variant'] != 'compensated-raw-target-v1'\n"
           "            or data['execution_variant'] != "+repr(EXECUTION)+"):")
    inverse=source
    for before,after in reversed(edits):inverse=D.once(inverse,after,before)
    if inverse!=parent:raise ValueError('whole157 private execution inverse differs')
    combined=old_edits+edits;inverse=source
    for before,after in reversed(combined):inverse=D.once(inverse,after,before)
    if inverse!=D.checked(S.ORIGINAL,S.ORIGINAL_SHA).decode():raise ValueError('whole109 composed inverse differs')
    trees=[ast.parse(text) for text in (parent,source)];exact={}
    for name in ('original_slots','selected_slot'):
        nodes=[next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name==name) for t in trees]
        exact[name]=ast.dump(nodes[0],include_attributes=False)==ast.dump(nodes[1],include_attributes=False)
    begin,end='        meta = json.loads(proc.stdout)','        for path, digest in list(D.INPUTS.items()):'
    blocks=[text[text.index(begin):text.index(end)] for text in (parent,source)]
    exact['full_terminal_analysis_bytes']=blocks[0]==blocks[1]
    exact['full_terminal_analysis_ast']=ast.dump(ast.parse('def analysis():\n'+blocks[0]),include_attributes=False)==ast.dump(ast.parse('def analysis():\n'+blocks[1]),include_attributes=False)
    if not all(exact.values()):raise ValueError('scientific scope/terminal analysis changed')
    return source,combined,dict(parent157_proof=old_proof,whole157_inverse_exact=True,
        whole109_composed_inverse_exact=True,original_scientific_blocks_exact=exact)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe',action='store_true');args,extra=parser.parse_known_args()
    if args.describe and extra:parser.error('description takes no acquisition arguments')
    os.sched_setaffinity(0,{31});priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    if any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):raise ValueError('BLAS/OMP1 required')
    if args.describe:
        if DESCRIPTION.exists():raise ValueError('fresh private description required')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),S.PLAN,Path(S.__file__).resolve(),L.PLAN,Path(L.__file__).resolve(),B.PLAN,Path(B.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])!=D.checked(path):
            raise ValueError('commit exact165/157/156/164 source/recipe first')
    for module in (C,D,L.G,B.P):D.checked(Path(module.__file__).resolve())
    D.checked(D.HERE/'run_primary_direction_sequence.py')
    source,edits,proof=program()
    scope=dict(__name__='n010_plan165',__file__=str(Path(__file__).resolve()),
        CANDIDATE_PLAN=PLAN,CANDIDATE_BASE=BASE,CANDIDATE_SUMMARY=SUMMARY,
        candidate_prerequisites=prerequisites,isolated_native=S.isolated_native,
        source_edits=edits,generated_program=source,composition_proof=proof)
    exec(compile(source,str(Path(__file__).resolve()),'exec'),scope)
    if not args.describe:return scope['main']()
    original,_=scope['original_slots']();rows=[]
    for case in range(26):
        slot=scope['selected_slot'](original,case);small,full=(8,16) if case<24 else (8192,16384)
        for phase in range(3):
            output,work=scope['paths'](case,phase)
            rows.append(dict(case_index=case,phase=phase,cell=slot['cell'],vertices=slot['vertices'],
                spp=small if phase==1 else full,begin_spp=small if phase==2 else 0,seeds=list(D.SEEDS),
                output=str(output),work=str(work),render_threads=4,actual_affinity=[31]))
    if len(rows)!=78 or len({r['output'] for r in rows})!=78:raise ValueError('complete original78 scope required')
    result=dict(schema='n010-private-state-prefix-description/1',complete=True,source_scope_metadata_valid=True,
        source_commit=commit,input_sha256=D.INPUTS,proof=proof,source_edits=edits,rows=rows,
        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        classification='PRIVATE_FULL78_STATE_PREFIX_SOURCE_ONLY_NOT_RUN',gpu_run=False,native_executed=False,
        reference_admission=False,accepted_timing=False,physical_evidence_transfer_approved=False,
        tests='NOT_RUN; source/inverse/AST/full-scope metadata only')
    with DESCRIPTION.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__=='__main__':main()

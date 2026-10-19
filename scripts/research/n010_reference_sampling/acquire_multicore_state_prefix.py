#!/usr/bin/env python3
"""Plan170: unchanged full78 state/prefix science on the bounded four-core profile."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess

import acquire_private_state_prefix as P
import acquire_multicore_sphere_seed as M
from acquire_private_state_prefix import D,S,L,C,B,BASE,SUMMARY,EXECUTION

PLAN = D.RESULTS.parent/'experiments/170-four-core-full-state-prefix-profile.md'
DESCRIPTION = D.RESULTS/'723-four-core-state-prefix-description.json'
PARENT_SHA = '60d53f6fd7767f742f5c23acdfcaf7edca0680dc132647c2f4515ace9ec94d3a'
PROFILE = M.PROFILE


def prerequisites():
    build=P.prerequisites()
    pilot=L.bind(D.RESULTS/'720-four-core-full-c1-equivalence.json')
    if (not pilot['all_pass'] or not pilot['terminal_identity_verified']
            or not pilot['all_six_payload_bytes_and_exported_audits_exact']
            or pilot['actual_affinity']!=[28,29,30,31] or pilot['threads']!=4):
        raise ValueError('actual bounded four-core equivalence required')
    source,proof=M.program()
    scope=dict(__name__='n010_plan170_physical_reader',__file__=str(Path(M.__file__).resolve()),
        _execution_plan=M.PLAN,_private_binary=M.BINARY,_legacy_binary=M.LEGACY_BINARY,
        _execution_profile=PROFILE,_composition=proof)
    exec(compile(source,str(M.ORIGINAL)+'#plan170-readonly','exec'),scope)
    for name in M.G.NAMES:
        for index in range(4):scope['retained_part'](name,index)
    return build


def program():
    D.checked(Path(P.__file__).resolve(),PARENT_SHA)
    parent,old_edits,old_proof=P.program();source=parent;edits=[]
    def change(before,after):
        nonlocal source
        source=D.once(source,before,after);edits.append((before,after))
    change('os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})',
           'os.sched_setaffinity(0, {28,29,30,31})')
    change("actual['affinity'] != [31]","actual['affinity'] != [28,29,30,31]")
    for kind in ('all-state-prefix-summary','state-prefix-step'):
        old="schema='n010-private-"+kind+"/1', execution_variant='thread-private-audit-v2'"
        change(old,old+', execution_profile='+repr(PROFILE))
    change("or data['execution_variant'] != 'thread-private-audit-v2'):",
        "or data['execution_variant'] != 'thread-private-audit-v2'\n"
        "            or data.get('execution_profile') != "+repr(PROFILE)+'):' )
    inverse=source
    for before,after in reversed(edits):inverse=D.once(inverse,after,before)
    if inverse!=parent:raise ValueError('whole165 generated source inverse differs')
    combined=old_edits+edits;inverse=source
    for before,after in reversed(combined):inverse=D.once(inverse,after,before)
    if inverse!=D.checked(S.ORIGINAL,S.ORIGINAL_SHA).decode():raise ValueError('whole109 composed source inverse differs')
    begin,end='        meta = json.loads(proc.stdout)','        for path, digest in list(D.INPUTS.items()):'
    blocks=[text[text.index(begin):text.index(end,text.index(begin))] for text in (parent,source)]
    if blocks[0]!=blocks[1]:raise ValueError('original full state/prefix scientific analysis differs')
    if ast.dump(ast.parse('def analysis():\n'+blocks[0]),include_attributes=False)!=ast.dump(ast.parse('def analysis():\n'+blocks[1]),include_attributes=False):
        raise ValueError('original full state/prefix scientific AST differs')
    ast.parse(source)
    return source,combined,dict(parent165_proof=old_proof,whole165_generated_inverse_exact=True,
        whole109_composed_inverse_exact=True,full_scientific_terminal_analysis_bytes_exact=True,
        full_scientific_terminal_analysis_ast_exact=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe',action='store_true');args,extra=parser.parse_known_args()
    if args.describe and extra:parser.error('description takes no acquisition arguments')
    if not args.describe and not {28,29,30,31}.issubset(os.sched_getaffinity(0)):
        raise ValueError('registered four CPUs unavailable')
    os.sched_setaffinity(0,{31});priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    if any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):raise ValueError('BLAS/OMP1 required')
    if args.describe:
        if DESCRIPTION.exists():raise ValueError('fresh source description required')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),P.PLAN,Path(P.__file__).resolve(),S.PLAN,Path(S.__file__).resolve(),
                 M.PLAN,Path(M.__file__).resolve(),L.PLAN,Path(L.__file__).resolve(),B.PLAN,Path(B.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])!=D.checked(path):
            raise ValueError('commit exact four-core state/prefix sources and recipes first')
    source,edits,proof=program()
    scope=dict(__name__='n010_plan170',__file__=str(Path(__file__).resolve()),CANDIDATE_PLAN=PLAN,
        CANDIDATE_BASE=BASE,CANDIDATE_SUMMARY=SUMMARY,candidate_prerequisites=prerequisites,
        isolated_native=S.isolated_native,source_edits=edits,generated_program=source,composition_proof=proof)
    exec(compile(source,str(Path(__file__).resolve()),'exec'),scope)
    if not args.describe:return scope['main']()
    original,_=scope['original_slots']();rows=[]
    for case in range(26):
        slot=scope['selected_slot'](original,case);small,full=(8,16) if case<24 else (8192,16384)
        for phase in range(3):
            output,work=scope['paths'](case,phase)
            rows.append(dict(case_index=case,phase=phase,cell=slot['cell'],vertices=slot['vertices'],
                spp=small if phase==1 else full,begin_spp=small if phase==2 else 0,seeds=list(D.SEEDS),
                output=str(output),work=str(work),render_threads=4,actual_affinity=[28,29,30,31]))
    if len(rows)!=78 or len({r['output'] for r in rows})!=78:raise ValueError('complete original78 scope required')
    for path,digest in list(D.INPUTS.items()):D.checked(Path(path),digest)
    result=dict(schema='n010-four-core-state-prefix-description/1',complete=True,source_scope_metadata_valid=True,
        source_commit=commit,input_sha256=D.INPUTS,proof=proof,source_edits=edits,rows=rows,
        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),execution_profile=PROFILE,
        classification='FOUR_CORE_FULL78_STATE_PREFIX_SOURCE_ONLY_NOT_RUN',gpu_run=False,native_executed=False,
        prerequisites_executed=False,reference_admission=False,accepted_timing=False,
        tests='NOT_RUN; exact source/inverse/AST/full-scope metadata only')
    with DESCRIPTION.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__=='__main__':main()

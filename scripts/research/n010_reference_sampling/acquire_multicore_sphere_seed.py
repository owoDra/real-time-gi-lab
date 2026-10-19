#!/usr/bin/env python3
"""Plan169: original remaining full physical seeds, four-core private execution."""
import argparse
import ast
import hashlib
import os
from pathlib import Path
import subprocess

import acquire_compensated_full_sphere_seed as G
from acquire_compensated_full_sphere_seed import C,D

PLAN = D.RESULTS.parent/'experiments/169-four-core-full-physical-seed-profile.md'
ORIGINAL = Path(G.__file__).resolve()
ORIGINAL_SHA = '9cf015bd6b18ceeda9e4c016ce99689d991caa0e9c0eab1187f5e243dbd349a8'
BINARY = D.OUT/'thread-private-reference-build-v2/n010_thread_private_exporter'
LEGACY_BINARY = D.OUT/'compensated-full-deterministic-v1/build/n010_compensated_exporter'
PROFILE = 'four-core-low-priority-v1'


def program():
    original = D.checked(ORIGINAL,ORIGINAL_SHA).decode();source=original;edits=[]
    def change(before,after):
        nonlocal source
        source=D.once(source,before,after);edits.append((before,after))
    change("PLAN = D.RESULTS.parent / 'experiments/145-compensated-full-sphere-seed-checkpoints.md'",'PLAN = _execution_plan')
    change('os.sched_setaffinity(0, {31})','os.sched_setaffinity(0, {28,29,30,31})')
    change('    os.nice(15)','    priority=os.getpriority(os.PRIO_PROCESS,0)\n    if priority<15:os.nice(15-priority)')
    change("build = C.pinned_result('452')","build = C.pinned_result('627')")
    change("binary = D.OUT / 'compensated-full-deterministic-v1/build/n010_compensated_exporter'",'binary = _private_binary')
    change("'--spp', '8192', '--threads', '1']","'--spp', '8192', '--threads', '4']")
    change("numerical_variant='compensated-raw-target-v1', complete=False",
        "numerical_variant='compensated-raw-target-v1', execution_variant='thread-private-audit-v2',\n"
        '                  execution_profile=_execution_profile,source_composition_proof=_composition,complete=False')
    change("actual['affinity'] != [31]","actual['affinity'] != [28,29,30,31]")
    anchor="    receipt = json.loads(D.checked(Path(data['resource_receipt'])))\n"
    guard='''    profile=data.get('execution_profile','original-one-core145')
    if profile=='original-one-core145':
        affinity,binary,threads=[31],_legacy_binary,'1'
    elif profile==_execution_profile:
        if data.get('execution_variant')!='thread-private-audit-v2':raise ValueError('wrong private physical variant')
        affinity,binary,threads=[28,29,30,31],_private_binary,'4'
    else:raise ValueError('unknown prior physical execution profile')
    command=data['command'];limits=data['native_limits']
    if (receipt['command']!=command or command[0]!=str(binary)
            or command[-2:]!=['--threads',threads] or receipt['affinity']!=affinity
            or limits['affinity']!=affinity or receipt['nice']!=15 or limits['nice']!=15
            or receipt['cpu']!=[7200]*2 or limits['cpu_seconds']!=7200
            or receipt['address_space']!=[4*1024**3]*2 or limits['address_space_bytes']!=4*1024**3
            or receipt['elapsed_limit_seconds']!=10800 or limits['elapsed_seconds']!=10800):
        raise ValueError('prior physical execution command/resource profile differs')
'''
    change(anchor,anchor+guard)
    inverse=source
    for before,after in reversed(edits):inverse=D.once(inverse,after,before)
    if inverse!=original:raise ValueError('whole145 execution-profile source inverse differs')
    begin="        fresh = json.loads((work/'native.stdout').read_text())"
    end='        for p, digest in list(D.INPUTS.items()):'
    blocks=[text[text.index(begin):text.index(end,text.index(begin))] for text in (original,source)]
    if blocks[0]!=blocks[1]:raise ValueError('complete original physical/IID analysis changed')
    if ast.dump(ast.parse('def analysis():\n'+blocks[0]),include_attributes=False)!=ast.dump(ast.parse('def analysis():\n'+blocks[1]),include_attributes=False):
        raise ValueError('complete original physical/IID AST changed')
    ast.parse(source)
    return source,dict(original145_sha256=ORIGINAL_SHA,whole145_source_inverse_exact=True,
        full_physical_and_independent_iid_analysis_bytes_exact=True,
        full_physical_and_independent_iid_analysis_ast_exact=True,
        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),source_edits=edits)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',choices=('A6b','A10'),required=True)
    parser.add_argument('--seed-index',type=int,choices=range(4),required=True);args=parser.parse_args()
    if args.name=='A6b' and args.seed_index==0:parser.error('original493 already retained; only remaining seeds')
    if not {28,29,30,31}.issubset(os.sched_getaffinity(0)):raise ValueError('registered four CPUs unavailable')
    if any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):raise ValueError('BLAS/OMP1 required')
    os.sched_setaffinity(0,{31});priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    G.require_no_other_research_worker()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),ORIGINAL,D.RESULTS/'720-four-core-full-c1-equivalence.json',
                 D.RESULTS/'717-private-estimator-identity-and-physical-evidence-transfer.md'):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])!=D.checked(path):
            raise ValueError('commit exact profile source/recipe and retained evidence first')
    proofs={}
    for stem in ('626','627','720'):
        proof=C.pinned_result(stem);proofs[stem]=proof
        for group in ('input_sha256','payload_sha256'):
            for name,digest in proof.get(group,{}).items():D.checked(Path(name),digest)
    if (not proofs['626']['source_preparation_valid'] or not proofs['627']['build_valid']
            or not proofs['720']['all_pass'] or not proofs['720']['terminal_identity_verified']
            or not proofs['720']['all_six_payload_bytes_and_exported_audits_exact']
            or proofs['720']['actual_affinity']!=[28,29,30,31] or proofs['720']['threads']!=4):
        raise ValueError('exact private source/build/four-core equivalence required')
    source,proof=program()
    scope=dict(__name__='n010_plan169',__file__=str(Path(__file__).resolve()),_execution_plan=PLAN,
        _private_binary=BINARY,_legacy_binary=LEGACY_BINARY,_execution_profile=PROFILE,_composition=proof)
    exec(compile(source,str(ORIGINAL)+'#plan169','exec'),scope)
    return scope['main']()


if __name__=='__main__':main()

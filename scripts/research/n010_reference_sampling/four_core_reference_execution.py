#!/usr/bin/env python3
"""Plan171: explicit four-core raw-chain/one-level connection; source-only CLI."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
from types import ModuleType

import private_reference_execution as P
import acquire_multicore_state_prefix as S
from private_reference_execution import D

PLAN = D.RESULTS.parent/'experiments/171-four-core-reference-chain-and-level-io.md'
DESCRIPTION = D.RESULTS/'726-four-core-reference-execution-description.json'
PARENT_SHA = 'cbf084a97e55570554202756d002fbafccfe04b45b8e90c1b12c75889c919a63'
STATE_SHA = '73335a75b415547890fcc056541e0bb067885cd87b11d7fd805be4bd2229850d'
PROFILE = S.PROFILE
VARIANT = 'compensated-all-split-private-four-core-v1'
ROOT = D.OUT/'private-four-core-reference-ladders-v1'
BINARY = P.BINARY
PROOFS = P.PROOFS + ('720-four-core-full-c1-equivalence.json',
    '723-four-core-state-prefix-description.json')


def components():
    """Bind libraries without invoking prerequisites, acquisition or images."""
    D.checked(Path(P.__file__).resolve(),PARENT_SHA)
    D.checked(Path(S.__file__).resolve(),STATE_SHA)
    _,_,parent = P.components()
    extra = [
        ('import acquire_private_state_prefix as S','import acquire_multicore_state_prefix as S'),
        ("summary.get('execution_variant') != 'thread-private-audit-v2'",
         "summary.get('execution_variant') != 'thread-private-audit-v2'\n"
         "            or summary.get('execution_profile') != "+repr(PROFILE)),
        ("if q['computational_variant'] != VARIANT:",
         "if q.get('execution_profile') != "+repr(PROFILE)+" or q['computational_variant'] != VARIANT:"),
        ("or receipt['affinity'] != [31] or receipt['nice'] != 15",
         "or receipt['affinity'] != [28,29,30,31] or receipt['nice'] != 15\n"
         "                or receipt.get('execution_profile') != "+repr(PROFILE)+"\n"
         "                or attempt.get('execution_profile') != "+repr(PROFILE)),
    ]
    source = P.compose(D.checked(P.CHAIN,P.CHAIN_SHA).decode(),parent['chain_edits']+extra)
    chain = ModuleType('n010_four_core_reference_chain')
    chain.__dict__.update(__file__=str(Path(__file__).resolve()),_private_plan=PLAN,
        _private_variant=VARIANT,_private_binary=BINARY,_private_root=ROOT,_private_proofs=PROOFS)
    exec(compile(source,str(P.CHAIN)+'#plan171-library','exec'),chain.__dict__)
    io_extra = [
        ("raise ValueError('one numerical thread required')\n    os.sched_setaffinity(0,{31})",
         "raise ValueError('one numerical thread required')\n"
         "    if not {28,29,30,31}.issubset(os.sched_getaffinity(0)):\n"
         "        raise ValueError('registered four CPUs unavailable')\n"
         "    os.sched_setaffinity(0,{28,29,30,31})"),
        ("computational_variant=P.VARIANT,proof_sha256=proofs,levels=[],classification='INELIGIBLE')",
         "computational_variant=P.VARIANT,execution_profile="+repr(PROFILE)+
         ",proof_sha256=proofs,levels=[],classification='INELIGIBLE')"),
        ('attempt = dict(command=command,source_commit=commit,pass_=False,native_terminal=False,',
         'attempt = dict(command=command,source_commit=commit,pass_=False,native_terminal=False,\n'
         '        execution_profile='+repr(PROFILE)+','),
        ("boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,",
         "boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,\n"
         "            execution_profile="+repr(PROFILE)+','),
        ("or own['affinity'] != [31] or own['nice'] != 15",
         "or own['affinity'] != [28,29,30,31] or own['nice'] != 15\n"
         "                or own.get('execution_profile') != "+repr(PROFILE)),
    ]
    original_io = D.checked(P.LEVEL,P.LEVEL_SHA).decode()
    io_source = P.compose(original_io,parent['level_edits']+io_extra)
    level = ModuleType('n010_four_core_reference_level_io')
    level.__dict__.update(__file__=str(Path(__file__).resolve()),_private_plan=PLAN,_private_chain=chain)
    exec(compile(io_source,str(P.LEVEL)+'#plan171-library','exec'),level.__dict__)
    def node(text,name):
        return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
    if ast.dump(node(original_io,'analysis_program'),include_attributes=False) != ast.dump(node(io_source,'analysis_program'),include_attributes=False):
        raise ValueError('complete original161 scientific analyser changed')
    _,_,raw_proof = chain.program()
    _,io_proof = level.analysis_program()
    return chain,level,dict(parent167_composition=parent,whole158_composed_inverse_exact=True,
        whole161_composed_inverse_exact=True,original161_analysis_function_ast_exact=True,
        raw_verifier_composition=raw_proof,scientific_analysis_composition=io_proof,
        chain_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        level_source_sha256=hashlib.sha256(io_source.encode()).hexdigest(),
        additional_chain_edits=extra,additional_level_edits=io_extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe',action='store_true',required=True)
    parser.parse_args()
    os.sched_setaffinity(0,{31});priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('BLAS/OMP1 required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);signal.alarm(180)
    if DESCRIPTION.exists():raise ValueError('fresh source description required')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),P.PLAN,Path(P.__file__).resolve(),
                 S.PLAN,Path(S.__file__).resolve(),S.M.PLAN,Path(S.M.__file__).resolve(),
                 P.CHAIN,P.LEVEL):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact four-core connection sources/recipes first')
    chain,level,proof = components()
    if (chain.SELECTED != ('C1_T_B8','C2_T_B8','C3_T_B8','C4_T_B8','C5_T_B2','C5_T_B8','C6_T_B2','C6_T_B8')
            or list(chain.Q.LEVELS) != [8192,16384,32768,65536,131072,262144]
            or list(chain.Q.L.N007_SEEDS) != list(D.SEEDS)):
        raise ValueError('complete original eight-slot/six-level/four-seed scope required')
    for path,digest in list(D.INPUTS.items()):D.checked(Path(path),digest)
    result = dict(schema='n010-four-core-reference-execution-description/1',complete=True,
        classification='FOUR_CORE_RAW_CHAIN_AND_LEVEL_IO_SOURCE_ONLY_NOT_QUALIFIED',
        source_commit=commit,input_sha256=D.INPUTS,proof=proof,variant=VARIANT,root=str(ROOT),
        binary=str(BINARY),required_proofs=list(PROOFS),selected_transports=list(chain.SELECTED),
        levels=list(chain.Q.LEVELS),seeds=list(D.SEEDS),render_threads=4,
        actual_native_affinity=[28,29,30,31],description_affinity=[31],execution_profile=PROFILE,
        prerequisites_executed=False,raw_evidence_replayed=False,native_executed=False,gpu_run=False,
        scientific_launcher_implemented=False,reference_admission=False,accepted_timing=False,
        tests='NOT_RUN; exact source/inverse/AST/full-scope connection metadata only')
    with DESCRIPTION.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__ == '__main__':main()

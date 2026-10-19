#!/usr/bin/env python3
"""Plan167: private raw-chain/one-level library; CLI describes source only."""
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

import acquire_private_state_prefix as S
from acquire_private_state_prefix import D

PLAN = D.RESULTS.parent/'experiments/167-private-reference-chain-and-level-io.md'
DESCRIPTION = D.RESULTS/'718-private-reference-execution-description.json'
CHAIN = D.HERE/'compensated_reference_chain.py'
CHAIN_SHA = '45cf734783d70ec2ebef5f25a16e256b9b78d1920086010c95ede42e8f586735'
LEVEL = D.HERE/'compensated_reference_level_io.py'
LEVEL_SHA = '24899620c4322aa31d08548165b414aa15b0645cdf115bf181916b6547634ae0'
VARIANT = 'compensated-all-split-private-v2'
ROOT = D.OUT/'private-compensated-reference-ladders-v1'
BINARY = D.OUT/'thread-private-reference-build-v2/n010_thread_private_prefix'
PROOFS = ('452-compensated-full-exporter-build.json','525-compensated-prefix-source-prepare.json',
          '526-compensated-prefix-build.json','626-thread-private-cli-source.json',
          '627-thread-private-cli-build.json','708-private-all-state-prefix-summary.json',
          '717-private-estimator-identity-and-physical-evidence-transfer.md')


def compose(original, edits):
    source = original
    for before,after in edits:source = D.once(source,before,after)
    inverse = source
    for before,after in reversed(edits):inverse = D.once(inverse,after,before)
    if inverse != original:raise ValueError('whole private connection source inverse differs')
    ast.parse(source)
    return source


def components():
    """Compose libraries only: no prerequisite, replay or acquisition call."""
    original = D.checked(CHAIN,CHAIN_SHA).decode()
    begin = original.index("PROOFS = ('452-")
    end = original.index('\nDESCRIPTION =',begin)
    edits = [
        ('import acquire_compensated_state_prefix as S','import acquire_private_state_prefix as S'),
        ("PLAN = D.RESULTS.parent/'experiments/158-compensated-reference-raw-chain.md'",'PLAN = _private_plan'),
        ("VARIANT = 'compensated-all-split-mixture-v1'",'VARIANT = _private_variant'),
        ("BINARY = D.OUT/'compensated-prefix-build-v1/n010_compensated_prefix'",'BINARY = _private_binary'),
        ("REFERENCE_ROOT = D.OUT/'compensated-reference-ladders-v1'",'REFERENCE_ROOT = _private_root'),
        (original[begin:end],'PROOFS = _private_proofs'),
        ('isolated_native=S.isolated_native','isolated_native=S.S.isolated_native'),
        ('str(S.ORIGINAL)','str(S.S.ORIGINAL)'),
        ("if (not summary['all_pass'] or summary['numerical_variant']",
         "if (summary.get('execution_variant') != 'thread-private-audit-v2'\n"
         "            or not summary['all_pass'] or summary['numerical_variant']"),
        ("\"'--spp', str(spp), '--threads', '1']\"", "\"'--spp', str(spp), '--threads', '4']\""),
    ]
    source = compose(original,edits)
    chain = ModuleType('n010_private_reference_chain')
    chain.__dict__.update(__file__=str(Path(__file__).resolve()),_private_plan=PLAN,
        _private_variant=VARIANT,_private_binary=BINARY,_private_root=ROOT,_private_proofs=PROOFS)
    exec(compile(source,str(CHAIN)+'#plan167-library','exec'),chain.__dict__)
    original_io = D.checked(LEVEL,LEVEL_SHA).decode()
    io_edits = [
        ('import compensated_reference_chain as P\nfrom compensated_reference_chain import D, Q, require_no_other_research_worker',
         'P = _private_chain\nD, Q, require_no_other_research_worker = P.D, P.Q, P.require_no_other_research_worker'),
        ("PLAN = D.RESULTS.parent/'experiments/161-compensated-single-level-io-component.md'",'PLAN = _private_plan'),
        ("'--spp',str(spp),'--threads','1']","'--spp',str(spp),'--threads','4']"),
    ]
    io_source = compose(original_io,io_edits)
    level = ModuleType('n010_private_reference_level_io')
    level.__dict__.update(__file__=str(Path(__file__).resolve()),_private_plan=PLAN,_private_chain=chain)
    exec(compile(io_source,str(LEVEL)+'#plan167-library','exec'),level.__dict__)
    # The scientific analyser is the exact existing161 analyser, including
    # its original032 inverse. Only module binding and render thread differ.
    def node(text,name):
        return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
    analyser_exact = ast.dump(node(original_io,'analysis_program'),include_attributes=False) == ast.dump(node(io_source,'analysis_program'),include_attributes=False)
    if not analyser_exact:raise ValueError('original161 scientific analysis source changed')
    _,_,raw_proof = chain.program()
    _,io_proof = level.analysis_program()
    proof = dict(whole158_inverse_exact=True,whole161_inverse_exact=True,
        original161_analysis_function_ast_exact=analyser_exact,
        raw_verifier_composition=raw_proof,scientific_analysis_composition=io_proof,
        chain_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        level_source_sha256=hashlib.sha256(io_source.encode()).hexdigest(),
        chain_edits=edits,level_edits=io_edits)
    return chain,level,proof


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
    for path in (PLAN,Path(__file__).resolve(),S.PLAN,Path(S.__file__).resolve(),CHAIN,LEVEL,
                 D.RESULTS/'717-private-estimator-identity-and-physical-evidence-transfer.md'):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact private connection sources/assessment first')
    chain,level,proof = components()
    if (chain.SELECTED != ('C1_T_B8','C2_T_B8','C3_T_B8','C4_T_B8','C5_T_B2','C5_T_B8','C6_T_B2','C6_T_B8')
            or list(chain.Q.LEVELS) != [8192,16384,32768,65536,131072,262144]
            or list(chain.Q.L.N007_SEEDS) != list(D.SEEDS)):
        raise ValueError('complete original eight-slot/level/seed scope required')
    for module in (S,S.S,S.B,S.L,chain.Q,chain.Q.L,chain.Q.convergence):
        D.checked(Path(module.__file__).resolve())
    for path,digest in list(D.INPUTS.items()):D.checked(Path(path),digest)
    result = dict(schema='n010-private-reference-execution-description/1',complete=True,
        classification='PRIVATE_RAW_CHAIN_AND_LEVEL_IO_SOURCE_ONLY_NOT_QUALIFIED',
        source_commit=commit,input_sha256=D.INPUTS,proof=proof,variant=VARIANT,root=str(ROOT),
        binary=str(BINARY),required_proofs=list(PROOFS),selected_transports=list(chain.SELECTED),
        levels=list(chain.Q.LEVELS),seeds=list(D.SEEDS),render_threads=4,actual_affinity=[31],
        prerequisites_executed=False,raw_evidence_replayed=False,native_executed=False,gpu_run=False,
        scientific_launcher_implemented=False,reference_admission=False,accepted_timing=False,
        tests='NOT_RUN; exact source/inverse/AST/full-scope connection metadata only')
    with DESCRIPTION.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__ == '__main__':main()

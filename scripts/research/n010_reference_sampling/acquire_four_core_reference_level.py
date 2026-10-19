#!/usr/bin/env python3
"""Plan172: one manually named scientific level; never automatic admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

import four_core_reference_execution as E
from four_core_reference_execution import D

PLAN = D.RESULTS.parent/'experiments/172-four-core-scientific-level-and-feasibility.md'
ASSESSMENT = D.RESULTS/'735-independent-compensated-density-and-bias-assessment.md'
PREPARED = D.RESULTS/'736-four-core-reference-scientific-preparation.json'
PILOT = {8192:D.RESULTS/'737-four-core-c1-b8-feasibility-8192.json',
         16384:D.RESULTS/'738-four-core-c1-b8-feasibility-16384.json'}
FEASIBILITY = D.RESULTS/'739-four-core-full-frame-two-level-feasibility.json'
EXECUTION_SHA = '30b51c56b6a07b889d12e2ea2b9ad5af347c6b14a8c8aef2687df984864b6242'
ASSESSMENT_SHA = 'f85c7e225c7e03306714ec81135ed428b1bb1dd7982d2ac439d4ded97a4dc768'


def write(path, value, fresh=False):
    with path.open('x' if fresh else 'w') as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def identity():
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),ASSESSMENT,E.PLAN,Path(E.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact172/171 sources, recipes and735 before execution')
    D.checked(Path(E.__file__).resolve(),EXECUTION_SHA)
    D.checked(ASSESSMENT,ASSESSMENT_SHA)
    return commit


def record(path):
    value = json.loads(D.checked(path))
    if not value.get('complete') or not value.get('pass_'):
        raise ValueError('actual complete passing prerequisite required: '+str(path))
    if (value.get('execution_profile') != E.PROFILE or value.get('variant') != E.VARIANT
            or value.get('assessment_sha256') != ASSESSMENT_SHA):
        raise ValueError('scientific profile/assessment identity differs')
    for name,digest in value['input_sha256'].items():D.checked(Path(name),digest)
    return value


def envelope(native=False):
    if not {28,29,30,31}.issubset(os.sched_getaffinity(0)):
        raise ValueError('registered four CPUs unavailable')
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('BLAS/OMP1 required')
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if os.getpriority(os.PRIO_PROCESS,0) != 15:raise ValueError('exact nice15 required')
    resource.setrlimit(resource.RLIMIT_CPU,(1200,172800 if native else 1200))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    signal.alarm(1800)


def snapshot(selected,spp):
    directory = E.ROOT/selected
    source = directory/'qualification.json'
    data = source.read_bytes()
    frozen = directory/f'qualification-after-n{spp}.json'
    with frozen.open('xb') as stream:stream.write(data)
    if frozen.read_bytes() != data:raise ValueError('immutable qualification snapshot differs')
    live = D.INPUTS.pop(str(source),None)
    if live != hashlib.sha256(data).hexdigest():
        raise ValueError('raw reader did not bind exact current qualification view')
    D.checked(frozen,live)
    return frozen,json.loads(data)


def output_for(selected,spp):
    return PILOT[spp] if selected == 'C1_T_B8' and spp in PILOT else E.ROOT/f'{selected}.n{spp}.scientific-launcher.json'


def preceding_slot(chain,selected):
    for earlier in chain.SELECTED[:chain.SELECTED.index(selected)]:
        directory = E.ROOT/earlier
        q = json.loads(D.checked(directory/'qualification.json'))
        if (q.get('execution_profile') != E.PROFILE or q.get('computational_variant') != E.VARIANT
                or not q['levels']):raise ValueError('preceding slot has no accepted scientific prefix')
        count = q['levels'][-1]['spp']
        old = record(output_for(earlier,count))
        frozen = Path(old['qualification_snapshot']['path'])
        if frozen.read_bytes() != (directory/'qualification.json').read_bytes():
            raise ValueError('preceding slot live view differs from terminal scientific snapshot')
        if not (q['classification'] == 'STATISTICALLY_ELIGIBLE' or
                (q['classification'] == 'INELIGIBLE' and count == chain.Q.LEVELS[-1])):
            raise ValueError('preceding slot has not reached its original scientific stop')
        # Only immutable snapshots belong in a later record's input identity.
        D.INPUTS.pop(str(directory/'qualification.json'),None)


def acquire(chain,level,selected,spp,result):
    prepared = record(PREPARED)
    if not prepared.get('prerequisites_executed'):
        raise ValueError('source metadata cannot replace actual full prerequisite preparation')
    pilot = selected == 'C1_T_B8' and spp in PILOT
    if not pilot:
        pair = record(FEASIBILITY)
        if not pair.get('feasibility_pass'):raise ValueError('actual two-level feasibility must pass first')
        preceding_slot(chain,selected)
    directory = E.ROOT/selected
    if spp != chain.Q.LEVELS[0]:
        q = json.loads(D.checked(directory/'qualification.json'))
        previous = q['levels'][-1]['spp']
        old = record(output_for(selected,previous))
        if Path(old['qualification_snapshot']['path']).read_bytes() != (directory/'qualification.json').read_bytes():
            raise ValueError('continuation must start from exact prior terminal snapshot')
        D.INPUTS.pop(str(directory/'qualification.json'),None)
    result['native_executed'] = False
    os.sched_setaffinity(0,{28,29,30,31})
    raw = level.acquire_level(selected,spp)
    frozen,q = snapshot(selected,spp)
    if not raw['raw_chain_valid'] or raw['reference_admission']:
        raise ValueError('unchanged raw reader failed or improperly admitted a reference')
    attempt_path = directory/f'n{spp}.attempt.json'
    attempt = json.loads(D.checked(attempt_path))
    receipt = json.loads(D.checked(directory/f'n{spp}.resource-limits.json'))
    if (not attempt['pass'] or not attempt['native_terminal'] or attempt['returncode'] != 0
            or attempt['execution_profile'] != E.PROFILE or receipt['execution_profile'] != E.PROFILE):
        raise ValueError('original native terminal/resource checks did not pass')
    if spp != chain.Q.LEVELS[0]:
        before = directory/f'qualification-before-n{spp}.json'
        if before.read_bytes() != Path(old['qualification_snapshot']['path']).read_bytes():
            raise ValueError('original before-next archive differs from immutable preceding view')
        D.checked(before)
    D.checked(Path(raw['raw_chain_audit']))
    result.update(complete=True,pass_=True,native_executed=True,native_terminal=True,
        terminal_identity_verified=True,raw_chain_valid=True,
        classification='SCIENTIFIC_LEVEL_VALID_NOT_REFERENCE_ADMITTED',
        sample_interval=attempt['sample_interval'],seeds=list(chain.Q.L.N007_SEEDS),
        frame=[320,180],actual_affinity=receipt['affinity'],render_threads=4,
        qualification_classification=q['classification'],levels=[v['spp'] for v in q['levels']],
        qualification_snapshot=dict(path=str(frozen),sha256=D.sha(frozen)),
        native_attempt=dict(path=str(attempt_path),sha256=D.sha(attempt_path)),
        raw_chain_audit=dict(path=raw['raw_chain_audit'],sha256=D.sha(Path(raw['raw_chain_audit']))),
        child_cpu_seconds_diagnostic=attempt['child_cpu_seconds'],
        elapsed_seconds_diagnostic=attempt['wall_seconds_diagnostic'])


def summarize(result):
    first,second = [record(PILOT[n]) for n in (8192,16384)]
    for value,spp,interval in ((first,8192,[0,8192]),(second,16384,[8192,16384])):
        if (value.get('selected') != 'C1_T_B8' or value.get('spp') != spp
                or not value.get('native_terminal') or not value.get('terminal_identity_verified')
                or not value.get('raw_chain_valid') or value.get('sample_interval') != interval
                or value.get('frame') != [320,180] or value.get('seeds') != list(D.SEEDS)
                or value.get('actual_affinity') != [28,29,30,31] or value.get('render_threads') != 4):
            raise ValueError('fixed complete two-level feasibility scope differs')
    directory = E.ROOT/'C1_T_B8'
    if ((directory/'qualification-before-n16384.json').read_bytes() !=
            Path(first['qualification_snapshot']['path']).read_bytes()):
        raise ValueError('actual feasibility prefix history differs')
    D.checked(directory/'qualification-before-n16384.json')
    result.update(complete=True,pass_=True,feasibility_pass=True,native_executed=False,
        classification='ACTUAL_FULL_FRAME_TWO_LEVEL_FEASIBLE_NOT_REFERENCE_ADMITTED',
        selected='C1_T_B8',levels=[8192,16384],native_records=[str(PILOT[n]) for n in (8192,16384)],
        qualification_classification=second['qualification_classification'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--summarize-feasibility',action='store_true')
    parser.add_argument('--selected',choices=('C1_T_B8','C2_T_B8','C3_T_B8','C4_T_B8',
                                             'C5_T_B2','C5_T_B8','C6_T_B2','C6_T_B8'))
    parser.add_argument('--spp',type=int,choices=(8192,16384,32768,65536,131072,262144))
    args = parser.parse_args()
    if (args.prepare+args.summarize_feasibility+bool(args.selected and args.spp) != 1
            or bool(args.selected) != bool(args.spp)):
        parser.error('exactly one operation: --prepare, --summarize-feasibility, or --selected and --spp')
    # Refuse partials before any costly prerequisite or scientific replay.
    output = PREPARED if args.prepare else FEASIBILITY if args.summarize_feasibility else output_for(args.selected,args.spp)
    if output.exists():raise ValueError('fresh scientific record required; no overwrite/retry')
    # The detector is exported by the composed raw-chain module.
    envelope(native=bool(args.selected));commit = identity();chain,level,proof = E.components()
    chain.require_no_other_research_worker()
    if not args.prepare and not args.summarize_feasibility and args.spp != chain.Q.LEVELS[0]:
        if not output.parent.exists():raise ValueError('continuation slot does not exist')
    # Later records live in the already-existing root, outside fresh slot dirs.
    if not output.parent.exists():raise ValueError('scientific record parent missing')
    result = dict(schema='n010-four-core-scientific-reference-level/1',complete=False,pass_=False,
        source_commit=commit,execution_profile=E.PROFILE,variant=E.VARIANT,
        assessment_sha256=ASSESSMENT_SHA,source_composition=proof,
        selected=args.selected,spp=args.spp,reference_admission=False,accepted_timing=False,
        gpu_run=False,native_executed=False,automatic_queue=False,
        finite_arithmetic_global_bias_bound_proved=False,
        tests='NOT_RUN; registered scientific acquisition or retained-evidence verification only')
    if args.prepare:
        result['prior_bootstrap_failures'] = [dict(interpreter='bare system python',
            error="ModuleNotFoundError: No module named 'numpy'",returncode=1,
            preparation_executed=False,native_executed=False,scientific_outputs_created=False),
            dict(interpreter='retained venv without LD_LIBRARY_PATH',
            error='ImportError: libstdc++.so.6 unavailable to NumPy; loader also reports libz.so.1 missing',
            returncode=1,preparation_executed=False,native_executed=False,scientific_outputs_created=False)]
    result['library_search_path'] = os.environ.get('LD_LIBRARY_PATH','')
    for path in (Path('/nix/store/chqq8mpmpyfi9kgsngya71akv5xicn03-gcc-15.2.0-lib/lib/libstdc++.so.6'),
                 Path('/nix/store/lw86vj9kfwgvlivg3p8qg2nibpmhmsl9-zlib-1.3.2/lib/libz.so.1')):
        D.checked(path)
    write(output,result,True);started = time.monotonic()
    try:
        if args.prepare:
            proofs = chain.prerequisites(D.INPUTS)
            result.update(complete=True,pass_=True,prerequisites_executed=True,
                proof_sha256=proofs,classification='FULL_PREREQUISITES_VALID_NO_NATIVE_OR_REFERENCE_ADMISSION')
        elif args.summarize_feasibility:summarize(result)
        else:acquire(chain,level,args.selected,args.spp,result)
        for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(complete=True,pass_=False,failure=str(error),classification='INCOMPLETE_NO_RETRY_PARTIALS_RETAINED')
        if args.selected:
            attempt_path = E.ROOT/args.selected/f'n{args.spp}.attempt.json'
            if attempt_path.exists():
                attempt = json.loads(attempt_path.read_text())
                result.update(native_executed='native_pid' in attempt,
                    native_terminal=attempt.get('native_terminal',False),
                    retained_attempt=dict(path=str(attempt_path),sha256=D.sha(attempt_path)))
    result.update(input_sha256=dict(D.INPUTS),driver_elapsed_seconds_diagnostic=time.monotonic()-started)
    write(output,result);signal.alarm(0)
    print(json.dumps(dict(output=str(output),complete=result['complete'],pass_=result['pass_'],
        classification=result['classification'],failure=result.get('failure'))))
    return 0 if result['pass_'] else 2


if __name__ == '__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Plan164: preserve621; correct only private CLI thread scope, then isolated build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess

import prepare_thread_private_reference as P
from prepare_thread_private_reference import D,require_no_other_research_worker

PLAN = D.RESULTS.parent/'experiments/164-thread-private-cli-scope-correction.md'
PREP = D.RESULTS/'626-thread-private-cli-source.json'
BUILD = D.RESULTS/'627-thread-private-cli-build.json'
ROOT = D.OUT/'thread-private-reference-source-v2'
BUILD_ROOT = D.OUT/'thread-private-reference-build-v2'


def prepare(commit):
    if PREP.exists() or ROOT.exists():raise ValueError('fresh CLI correction required')
    parent = json.loads(D.checked(P.PREP))
    if not parent['complete'] or not parent['source_preparation_valid']:raise ValueError('actual621 source required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in parent[group].items():D.checked(Path(name),digest)
    rows,prepared = [],[]
    for original in parent['rows']:
        mode = original['mode'];main = 'exporter.cpp' if mode == 'full' else 'n010_rqmc_main.cpp'
        header = D.checked(P.ROOT/mode/'n010_rqmc_oracle.hpp',original['generated_header_sha256'])
        before = D.checked(P.ROOT/mode/main,original['main_sha256']).decode()
        edits = [('if(threads!=1||scene.sampling!=Sampling::Center',
                  'if((threads<1||threads>4)||scene.sampling!=Sampling::Center'),
                 ('all-split requires centre,one point,1..8 vertices,one thread',
                  'all-split requires centre,one point,1..8 vertices,one to four threads')]
        after = before
        for old,new in edits:after = D.once(after,old,new)
        restored = after
        for old,new in reversed(edits):restored = D.once(restored,new,old)
        if restored != before:raise ValueError('whole CLI inverse differs')
        command = list(original['command'])
        command[-3] = str(ROOT/mode/main)
        command[-1] = str(BUILD_ROOT/Path(original['binary']).name)
        rows.append(dict(original,command=command,binary=command[-1],
            main_sha256=hashlib.sha256(after.encode()).hexdigest(),parent_main_sha256=original['main_sha256'],
            cli_edits=edits,whole_cli_inverse_exact=True,header_bytes_unchanged=True))
        prepared.append((mode,main,after,header))
    ROOT.mkdir()
    for mode,main,after,header in prepared:
        folder=ROOT/mode;folder.mkdir()
        (folder/main).write_text(after);(folder/'n010_rqmc_oracle.hpp').write_bytes(header)
    for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
    result=dict(schema='n010-thread-private-cli-source/1',complete=True,source_preparation_valid=True,
        source_commit=commit,parent_record=str(P.PREP),input_sha256=D.INPUTS,rows=rows,
        payload_sha256={str(p):D.sha(p) for folder in ROOT.iterdir() for p in folder.iterdir()},
        classification='THREAD_PRIVATE_CLI_SCOPE_SOURCE_ONLY_NOT_QUALIFIED',compiled=False,
        native_rendering_executed=False,actual_cpu_load_changed=False,reference_admission=False,
        tests='NOT_RUN; exact source predicates/inverses/headers only')
    P.write(PREP,result,True);print(result['classification'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--build',action='store_true')
    args=parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    if any(os.environ.get(k)!='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))])!=D.checked(path):
            raise ValueError('commit exact164 source/recipe first')
    if args.prepare:
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
        return prepare(commit)
    require_no_other_research_worker()
    # Reuse the original build function, resource guards and terminal verifier.
    P.PREP=PREP;P.BUILD=BUILD;P.ROOT=ROOT;P.BUILD_ROOT=BUILD_ROOT
    return P.build(commit)


if __name__=='__main__':raise SystemExit(main())

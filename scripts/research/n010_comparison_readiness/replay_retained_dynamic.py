#!/usr/bin/env python3
"""Plan133: manually replay one retained dynamic cell, or aggregate proved parts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import sys
import time

import numpy as np
import continuation_quality_provenance as C
from continuation_quality_provenance import P,R,S

PLAN = R.RESULTS.parent/'experiments/133-retained-dynamic-cohort-proof-reuse.md'
WORK = R.BASE/'retained-dynamic-proof-v1'
CELLS = tuple(f'C{i}' for i in range(8,13))
ROLES = {'incumbent-hwrt','incumbent-software','vanilla-traversal','pixel-pt-B2','pixel-pt-B8','dense-rc'}
SCOPES = ('src/research/lane_n_end_to_end_renderer','shaders/research/lane_n_end_to_end_renderer')


def part_path(cell):
    return R.RESULTS/f'{410+int(cell[1:])}-retained-dynamic-{cell.lower()}-proof.json'


def write(path,data):
    with path.open('x') as output:
        output.write(json.dumps(data,indent=2,allow_nan=False)+'\n')


def git_blob(commit,path):
    return subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))],cwd=R.ROOT)


def source_proof(commit,cache):
    if commit in cache:
        return cache[commit]
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=R.ROOT,check=True,capture_output=True)
    identity = {}
    for directory in SCOPES:
        before = subprocess.check_output(['git','rev-parse',commit+':'+directory],text=True).strip()
        current = subprocess.check_output(['git','rev-parse','HEAD:'+directory],text=True).strip()
        C.require(before==current, 'published pinned N-series subtree changed')
        identity[directory] = before
        names = subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','--',directory],text=True).splitlines()
        for name in names:
            C.require(git_blob(commit,R.ROOT/name)==R.checked(R.ROOT/name), 'pinned source file differs from captured source')
    cache[commit] = identity
    return identity


def command_proof(row,lock):
    cell,role = row['cell'],row['role']
    spec = lock['cells'][cell]
    command = row['command']
    capture = Path(command[command.index('--out')+1])
    C.require(capture.is_absolute(), 'absolute capture required')
    prefix = ['bash','scripts/run_with_vulkan.sh']
    if role.startswith('incumbent') or role=='vanilla-traversal':
        backend = {'incumbent-hwrt':'hwrt','incumbent-software':'software','vanilla-traversal':'vanilla'}[role]
        expected = prefix+[str(R.ROOT/'build/n009/phos-n010-capture'),'--scene',
            str(R.ROOT/'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf'),
            '--scenario',spec['scenario'],'--backend',backend,'--direct-profile','ulp4',
            '--target-state','--recovery-frames','3','--out',str(capture)]
        if cell=='C12':
            expected.append('--topology-churn')
        spp = None
    else:
        vertices = 8 if role=='pixel-pt-B8' else 2
        spp = int(command[command.index('--spp')+1])
        C.require(spp in ({1} if role=='dense-rc' else ({1024} if vertices==8 else {256,1024})),
                  'unexpected retained budget')
        expected = prefix+[str(R.ROOT/'build/n009/phos-n010-pixel-pt'),'--state',
            str(R.ROOT/spec['source_directory']),'--target-state',str(R.ROOT/spec['state_directory']),
            '--family','dense-rc' if role=='dense-rc' else 'pixel-pt','--spp',str(spp),
            '--vertices',str(vertices),'--seed','305419896','--frames','5','--out',str(capture)]
    C.require(command==expected and row['returncode']==0, 'native command/role/state/budget differs or failed')
    return capture,spp


def frame_state_proof(directory,expected,role,index):
    C.require(R.checked(directory/'geometry-state.bin')==R.checked(expected/'geometry-state.bin'),
              'complete captured geometry differs from locked state')
    actual=R.checked(directory/'frame-state.bin')
    locked=R.checked(expected/'frame-state.bin')
    if role.startswith('incumbent') or role=='vanilla-traversal':
        # A001ParamsGpu.limits[3] is the frame ID, not a transport parameter.
        # The historical wrapper advances it for the three recovery frames.
        C.require(len(actual)==len(locked)==148 and actual[:144]==locked[:144]
            and struct.unpack_from('<I',actual,144)[0]==index+1
            and struct.unpack_from('<I',locked,144)[0]==(1 if index==0 else 2),
            'state differs beyond exact registered frame-counter progression')
    else:
        C.require(actual==locked, 'complete PT/dense frame state differs')


def replay_cell(cell,lock,view):
    output = part_path(cell)
    work = WORK/cell
    C.require(not output.exists() and not work.exists(), 'existing cell proof/partials; no overwrite/retry')
    work.mkdir(parents=True)
    legacy = C.read(R.RESULTS/'019-controlled-dynamic-cohort.json')
    extra = C.read(R.RESULTS/'037-controlled-dynamic-pt1024.json')
    C.require(legacy['complete'] and extra['complete']
        and legacy['lock_sha256']==P.sha(R.RESULTS/'016-corpus-state-lock.json')
        and extra['lock_sha256']==P.sha(R.RESULTS/'026-dynamic-execution-state-lock.json'), 'original acquisition lock mismatch')
    R.checked(R.RESULTS/'016-corpus-state-lock.json')
    old = [r for r in legacy['rows'] if r['cell']==cell]
    additions = [r for r in extra['rows'] if r['cell']==cell]
    C.require(len(old)==6 and {r['role'] for r in old}==ROLES and len(additions)==1
              and additions[0]['role']=='pixel-pt-B2', 'full retained role/budget scope missing')
    physical = P.physical_proof(R.INPUTS)
    R.checked(P.Q.BINARY,physical['binary_sha256'])
    R.checked(P.Q.NET,physical['sobol_table_sha256'])
    refs,source_cache,rows,proofs = {},{},[],[]
    for ordinal,row in enumerate(old+additions):
        role = row['role']
        if row.get('classification')=='UNSUPPORTED_IN_CAPTURE_API':
            C.require(cell=='C12' and role=='incumbent-software', 'unexpected unsupported role/regime')
            rows.append(row)
            proofs.append(dict(cell=cell,role=role,classification='UNSUPPORTED_IN_CAPTURE_API'))
            continue
        source_proof(row['source_commit'],source_cache)
        capture,spp = command_proof(row,lock)
        for name,digest in row['payload_sha256'].items():
            R.checked(capture/name,digest)
        ledger = C.read(capture/'allocation-ledger.json')
        C.require(ledger==row['memory'] and P.sha(capture/'allocation-ledger.json')==row['ledger_sha256'],
                  'actual/saved ledger differs')
        peak = R.ledger_replay(capture/'allocation-ledger.json')
        timing_path = capture/('frames.json' if (capture/'frames.json').exists() else 'renderer-timings.jsonl')
        raw = R.checked(timing_path,row['timing_sha256'])
        timing = json.loads(raw) if timing_path.suffix=='.json' else [json.loads(line) for line in raw.splitlines()]
        C.require(timing==row['timings'], 'actual/saved timing differs')
        frames = timing['frames'] if isinstance(timing,dict) else timing
        C.require(len(frames)==5 and [f['state'] for f in frames]==['source','first-target','recovery','recovery','recovery'],
                  'missing/reordered source/change/recovery observation')
        for f in frames:
            C.require(R.positive(f.get('gpu_us',f.get('complete_renderer_gpu_us')))
                      and R.positive(f['wall_us']), 'invalid descriptive frame cost')
        transports = (2,) if role=='pixel-pt-B2' else ((8,) if role=='pixel-pt-B8' else (2,8))
        expected = {(f,f'T_B{v}') for f in range(5) for v in transports}
        C.require(len(row['scores'])==len(expected)
            and {(s['frame_index'],s['transport']) for s in row['scores']}==expected,
            'complete unique frame/transport score coverage missing')
        scores=[]
        for f in range(5):
            frame_dir = capture/'frames'/str(f)
            frame_state_proof(frame_dir,R.ROOT/lock['cells'][cell]['source_directory' if f==0 else 'state_directory'],role,f)
            for vertices in transports:
                ref_cell = 'C7' if f==0 else cell
                key=ref_cell,vertices
                if key not in refs:
                    ref = Path(view['work'])/f'{ref_cell}_T_B{vertices}'
                    entry = next(r for r in view['rows'] if r['name']==f'{ref_cell}_T_B{vertices}')
                    C.require(ref.is_symlink() and str(ref.resolve())==entry['target'], 'fixed reference target changed')
                    proof=P.verify_reference(ref,ref_cell,vertices,lock['cells'][ref_cell],R.INPUTS)
                    refs[key]=(ref,P.read(ref/'qualification.json',R.INPUTS),proof)
                ref,q,proof = refs[key]
                original = next(s for s in row['scores'] if s['frame_index']==f and s['transport']==f'T_B{vertices}')
                C.require(original['qualification_sha256']==P.sha(ref/'qualification.json'), 'reference changed since capture')
                score_dir=work/f'row{ordinal}'/f'frame{f}'
                score_dir.mkdir(parents=True,exist_ok=True)
                score_path=score_dir/f'quality-B{vertices}.json'
                score=S.score(frame_dir,q,ref,score_path)
                C.require(score['components']==original['components']
                    and score['pilot_quality_target']==original['pilot_quality_target']
                    and score['capture_payload_sha256']==original['capture_payload_sha256']
                    and score['scoring_exclusions']==0 and score['complete_physical_scene_bytes_equal']
                    and all(m['pixels']==57600 and m['scoring_exclusions']==0 for m in score['components'].values()),
                    'full quality metrics/classification/image/pixel scope differs')
                for component in ('direct','indirect','total'):
                    filename=f'quality-B{vertices}.{component}.error.npy'
                    C.require(R.checked(frame_dir/filename)==(score_dir/filename).read_bytes(), 'full error-map bytes differ')
                score.update(frame_index=f,role=role,qualification_sha256=P.sha(ref/'qualification.json'))
                write(score_path,score)
                scores.append(score)
        rows.append(dict(row,scores=scores))
        proofs.append(dict(cell=cell,role=role,spp=spp,frames=5,scores=len(scores),
            quality_counts={status:sum(s['pilot_quality_target']==status for s in scores) for status in ('PASS','FAIL')},
            owned_peak_bytes=peak,owned_teardown_zero=True,source_commit=row['source_commit'],
            historical_binary_sha256=row['binary_sha256'],accepted_timing=False))
        print(cell,role,spp,'scores',len(scores),'REPLAY_VALID',flush=True)
    canonical=dict(schema='n010-dynamic-cohort-pilot/1',complete=True,lock_sha256=P.sha(R.RESULTS/'026-dynamic-execution-state-lock.json'),
        full_required_corpus=False,cells=[cell],rows=rows,evidence_origin='POSTHOC_REPLAY_OF_RETAINED019_AND037_NO_TIMING_TRANSFER')
    canonical_path=work/'canonical-pilot.json'
    write(canonical_path,canonical)
    return dict(cell=cell,canonical_path=str(canonical_path),rows=proofs,
        reference_proofs=[v[2] for v in refs.values()],pinned_source_subtrees=source_cache,
        score_count=sum(p.get('scores',0) for p in proofs),native_histories=sum(p.get('frames',0)==5 for p in proofs))


def aggregate():
    output=R.RESULTS/'423-retained-controlled-dynamic-cohort-proof.json'
    work=WORK/'aggregate'
    C.require(not output.exists() and not work.exists(), 'existing aggregate; no overwrite/retry')
    work.mkdir(parents=True)
    rows=[]
    for cell in CELLS:
        part=C.read(part_path(cell))
        C.require(part['complete'] and part['retained_evidence_valid'] and part['cell']==cell, 'terminal valid cell proof required')
        for group in ('input_sha256','payload_sha256'):
            for name,digest in part[group].items():R.checked(name,digest)
        canonical=C.read(Path(part['validation']['canonical_path']))
        C.require(canonical['complete'] and canonical['cells']==[cell] and len(canonical['rows'])==7,
                  'canonical cell coverage differs')
        rows+=canonical['rows']
    C.require(len(rows)==35 and sum(len(r.get('scores',[])) for r in rows)==265
              and sum(r.get('classification')=='UNSUPPORTED_IN_CAPTURE_API' for r in rows)==1,
              'full retained aggregate coverage differs')
    canonical=dict(schema='n010-dynamic-cohort-pilot/1',complete=True,full_required_corpus=False,
        cells=list(CELLS),lock_sha256=P.sha(R.RESULTS/'026-dynamic-execution-state-lock.json'),rows=rows,
        evidence_origin='ALL_RETAINED019_AND037_ROWS_REPLAYED_NO_SPONZA_OR_CURRENT401_TIMING_ADMISSION')
    canonical_path=work/'canonical-cohort.json'
    write(canonical_path,canonical)
    return output,work,dict(canonical_path=str(canonical_path),rows=35,native_histories=34,
        frames=170,scores=265,full_required_corpus=False,cells=list(CELLS))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--cell',choices=CELLS)
    mode.add_argument('--aggregate',action='store_true')
    args=ap.parse_args()
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')), 'one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    signal.alarm(180)
    started,cpu=time.monotonic(),time.process_time()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN):C.require(git_blob(commit,path)==R.checked(path), 'commit exact recipe/source before replay')
    if args.aggregate:
        output,work,validation=aggregate()
    else:
        output,work=part_path(args.cell),WORK/args.cell
        validation=replay_cell(args.cell,C.read(R.RESULTS/'026-dynamic-execution-state-lock.json'),
                               C.read(R.RESULTS/'160-primary-direction-reference-view.json'))
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename and Path(filename).resolve().is_relative_to(R.ROOT/'scripts/research'):R.checked(filename)
    payloads={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(work.rglob('*')) if p.is_file()}
    R.unchanged()
    elapsed,used=time.monotonic()-started,time.process_time()-cpu
    C.require(elapsed<180 and used<120, 'registered resource bound exceeded')
    result=dict(schema='n010-retained-dynamic-proof/1',complete=True,retained_evidence_valid=True,
        cell=args.cell,classification='FULL_RETAINED_COHORT_REPLAY_VALID_NOT_FULL_N010' if args.aggregate else 'RETAINED_CELL_ALL_ROWS_REPLAY_VALID',
        all_pass=False,accepted_timing=False,reference_admission=False,gpu_run=False,posthoc=True,
        source_commit=commit,validation=validation,input_sha256=R.INPUTS,payload_sha256=payloads,
        execution=dict(pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            cpu_limit_seconds=120,elapsed_limit_seconds=180,address_space_limit_bytes=2*1024**3,
            elapsed_seconds=elapsed,cpu_seconds=used,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            numerical_threads=1,python=sys.version,numpy=np.__version__),
        tests='NOT_RUN; read-only scientific archived dynamic quality/reference/owned-memory replay only')
    write(output,result)
    signal.alarm(0)
    print(result['classification'])


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Plan131: replay every retained PT budget row into canonical audit inputs."""
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import numpy as np
import continuation_quality_provenance as C
from continuation_quality_provenance import P,R,S

PLAN = R.RESULTS.parent/'experiments/131-retained-pt-ladder-proof-reuse.md'
OUTPUT = R.RESULTS/'415-retained-pt-ladder-proof-replay.json'
WORK = R.BASE/'retained-pt-ladder-proof-v1'
PILOTS = dict(C7='013-c7-pt-cohort-pilot.json',C8='024-c8-pt-quality-ladder.json',
              C9='025-c9-pt-quality-ladder.json',C1='031-c1-b2-pt-quality-ladder.json')
SHADER = R.ROOT/'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl'
HOST = R.ROOT/'src/research/n010_comparison_readiness/pixel_pt_main.cpp'


def git_blob(commit,path):
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=R.ROOT,
                   check=True,capture_output=True)
    return subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))],cwd=R.ROOT)


def main():
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),
              'one numerical thread required before NumPy import')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    signal.alarm(180)
    started,cpu_started = time.monotonic(),time.process_time()
    C.require(not OUTPUT.exists() and not WORK.exists(), 'existing proof/work; no overwrite/retry')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN):
        C.require(git_blob(commit,path)==R.checked(path), 'commit exact recipe/driver before analysis')
    WORK.mkdir()
    lock = C.read(R.RESULTS/'026-dynamic-execution-state-lock.json')
    view = C.read(R.RESULTS/'160-primary-direction-reference-view.json')
    physical = P.physical_proof(R.INPUTS)
    R.checked(P.Q.BINARY,physical['binary_sha256'])
    R.checked(P.Q.NET,physical['sobol_table_sha256'])
    # Keep the real source/numerical bridge to401; it grants no timing claim.
    bridge = {cell:R.retained_part(cell) for cell in ('C1','C7')}
    original_shader = R.checked(SHADER)
    references,rows,pilots,blobs = {},[],{},{}
    for cell,pilot_name in PILOTS.items():
        legacy = C.read(R.RESULTS/pilot_name)
        expected = {(v,n) for v in ((2,) if cell=='C1' else (2,8)) for n in C.BUDGETS}
        C.require(legacy['complete'] and legacy['cell']==cell
            and len(legacy['rows'])==len(expected)
            and {(r['vertices'],r['spp']) for r in legacy['rows']}==expected,
            'complete unique retained ladder scope differs: '+cell)
        normalized = []
        for index,row in enumerate(legacy['rows']):
            vertices,spp = row['vertices'],row['spp']
            key = cell,vertices
            if key not in references:
                directory = Path(view['work'])/f'{cell}_T_B{vertices}'
                entry = next(r for r in view['rows'] if r['name']==f'{cell}_T_B{vertices}')
                C.require(directory.is_symlink() and str(directory.resolve())==entry['target'],
                          'fixed reference view target changed')
                proof = P.verify_reference(directory,cell,vertices,lock['cells'][cell],R.INPUTS)
                qualification = P.read(directory/'qualification.json',R.INPUTS)
                references[key] = directory,qualification,proof
            reference,qualification,proof = references[key]
            C.require(row['quality']['qualification_sha256']==P.sha(reference/'qualification.json'),
                      'reference changed since original quality scoring')
            source = row['source_commit']
            if source not in blobs:
                shader = git_blob(source,SHADER)
                host = git_blob(source,HOST)
                C.require(shader==original_shader, 'original full shader differs; cannot reuse estimator evidence')
                blobs[source] = dict(shader_sha256=hashlib.sha256(shader).hexdigest(),
                    host_sha256=hashlib.sha256(host).hexdigest(),source_commit=source)
            command = row['command']
            C.require(command[:2]==['bash','scripts/run_with_vulkan.sh']
                and command[2]==str(R.ROOT/'build/n009/phos-n010-pixel-pt')
                and len(command[3:])%2==0, 'legacy command executable/shape differs')
            options = dict(zip(command[3::2],command[4::2]))
            expected_options = {'--state':lock['cells'][cell]['state_directory'],
                '--out':options['--out'],'--vertices':str(vertices),'--spp':str(spp),
                '--seed':'305419896','--frames':'1'}
            C.require(len(options)*2==len(command[3:]) and options==expected_options
                and row['returncode']==0, 'legacy physical/budget/seed command differs or failed')
            capture = Path(options['--out'])
            C.require(capture.is_absolute(), 'absolute retained capture expected')
            required = {'geometry-state.bin','frame-state.bin','direct.pfm','indirect.pfm',
                        'total.pfm','frames.json','allocation-ledger.json'}
            C.require(required <= set(row['payload_sha256']), 'incomplete declared legacy payload')
            for name,digest in row['payload_sha256'].items():
                R.checked(capture/name,digest)
            state = C.require_state(capture,R.ROOT/lock['cells'][cell]['state_directory'])
            width,height = state['width'],state['height']
            metadata = C.read(capture/'frames.json')
            C.require((metadata['vertices'],metadata['spp'],metadata['seed'],metadata['width'],metadata['height'])
                    == (vertices,spp,305419896,width,height) and len(metadata['frames'])==1
                    and metadata.get('family','pixel-pt')=='pixel-pt'
                    and metadata==row['timings'], 'raw/saved native budget/timing differs')
            frame = metadata['frames'][0]
            C.require(frame['index']==0 and frame['seed']==305419896
                    and R.positive(frame['gpu_us']) and R.positive(frame['wall_us']),
                    'invalid retained descriptive frame observation')
            if (capture/'frames/0').is_dir():
                for name in ('geometry-state.bin','frame-state.bin','direct.pfm','indirect.pfm','total.pfm'):
                    C.require(R.checked(capture/'frames/0'/name)==R.checked(capture/name),
                              'top-level/frame0 retained payload differs')
            ledger = C.read(capture/'allocation-ledger.json')
            C.require(ledger==row['allocation_ledger'], 'raw/saved owned ledger differs')
            peak = R.ledger_replay(capture/'allocation-ledger.json')
            score_dir = WORK/f'{cell}-B{vertices}-n{spp}'
            score_dir.mkdir()
            score_path = score_dir/'quality.json'
            scored = S.score(capture,qualification,reference,score_path)
            C.require(scored['components']==row['quality']['components']
                    and scored['pilot_quality_target']==row['quality']['pilot_quality_target']
                    and scored['capture_payload_sha256']==row['quality']['capture_payload_sha256']
                    and scored['scoring_exclusions']==0
                    and all(m['pixels']==width*height and m['scoring_exclusions']==0
                            for m in scored['components'].values()),
                    'original full-image metrics/classification/images differ')
            for component in ('direct','indirect','total'):
                old_map = capture/f'quality.{component}.error.npy'
                C.require(R.checked(old_map)==(score_dir/f'quality.{component}.error.npy').read_bytes(),
                          'original full error-map bytes differ')
            scored['qualification_sha256'] = P.sha(reference/'qualification.json')
            with score_path.open('x') as output:
                output.write(json.dumps(scored,indent=2,allow_nan=False)+'\n')
            canonical = dict(row,quality=scored)
            normalized.append(canonical)
            rows.append(dict(cell=cell,vertices=vertices,spp=spp,quality_evidence_valid=True,
                quality_classification=scored['pilot_quality_target'],source_commit=source,
                original_binary_sha256=row['binary_sha256'],reference_proof=proof,
                owned_peak_bytes=peak,owned_teardown_zero=True,score_path=str(score_path),
                accepted_timing=False,reference_admission=False))
            print(cell,vertices,spp,scored['pilot_quality_target'],flush=True)
        pilot = dict(schema='n010-pt-cohort-pilot/1',complete=len(normalized)==12,cell=cell,
            full_two_transport_ladder=len(normalized)==12,rows=normalized,
            evidence_origin='READ_ONLY_RECOMPUTED_LEGACY_QUALITY_NOT_CURRENT_IMPLEMENTATION_TIMING')
        pilot_path = WORK/f'{cell}-canonical-pilot.json'
        with pilot_path.open('x') as output:
            output.write(json.dumps(pilot,indent=2,allow_nan=False)+'\n')
        pilots[cell] = dict(path=str(pilot_path),rows=len(normalized),complete=pilot['complete'])
    C.require(len(rows)==42, 'full retained scope not replayed')
    for module in tuple(sys.modules.values()):
        filename = getattr(module,'__file__',None)
        if filename and Path(filename).resolve().is_relative_to(R.ROOT/'scripts/research'):
            R.checked(filename)
    payloads = {str(path):hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(WORK.rglob('*')) if path.is_file()}
    R.unchanged()
    elapsed,cpu = time.monotonic()-started,time.process_time()-cpu_started
    C.require(elapsed < 180 and cpu < 120, 'registered resource guard exceeded')
    minimum = {f'{cell}_T_B{v}':min((r['spp'] for r in rows if r['cell']==cell
        and r['vertices']==v and r['quality_classification']=='PASS'),default=None)
        for cell,v in references}
    result = dict(schema='n010-retained-pt-ladder-proof-replay/1',complete=True,
        retained_quality_evidence_valid=True,all_pass=False,accepted_timing=False,
        reference_admission=False,gpu_run=False,posthoc=True,source_commit=commit,
        classification='ALL_42_RETAINED_ROWS_REPLAYED_C1_B8_LADDER_STILL_MISSING',
        rows=rows,canonical_pilots=pilots,descriptive_minimum_passing_spp=minimum,
        historical_source_blobs=blobs,continuation_equivalence_bridge=bridge,
        input_sha256=R.INPUTS,payload_sha256=payloads,
        execution=dict(pid=os.getpid(),affinity=sorted(os.sched_getaffinity(0)),
            nice=os.getpriority(os.PRIO_PROCESS,0),cpu_limit_seconds=120,elapsed_limit_seconds=180,
            address_space_limit_bytes=2*1024**3,elapsed_seconds=elapsed,cpu_seconds=cpu,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            numerical_threads=1,python=sys.version,numpy=np.__version__),
        limitations=['C1 full B8 ladder and eligible B8 reference still missing.',
            'Historical binary bytes not recovered/claimed; source/blob and raw capture identities retained.',
            'No legacy timing transfer to401 or prospective Lane M quality-budget selection.',
            'No dynamic/selected-boundary timing/full N010 audit admission.'],
        tests='NOT_RUN; read-only scientific archived quality/physical/owned-memory replay only')
    with OUTPUT.open('x') as output:
        output.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0)
    print(result['classification'])


if __name__=='__main__':
    main()

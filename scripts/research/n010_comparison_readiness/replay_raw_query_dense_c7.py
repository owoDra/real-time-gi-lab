#!/usr/bin/env python3
"""Plan151: post-hoc full507 replay with source-exact binary32 timer decoding."""
import json
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import time

import acquire_raw_query_dense_c7 as A
from acquire_raw_query_dense_c7 import C,R,P,H,S

PLAN = R.RESULTS.parent/'experiments/151-raw-query-native-float-conversion-replay.md'
OUTPUT = R.RESULTS/'509-posthoc-c7-dense-raw-query-replay.json'
WORK = R.BASE/'raw-query-c7-dense-replay-v1'


def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]


def native_interval(query,first,last):
    delta = (query['ticks'][last]-query['ticks'][first])&((1<<64)-1)
    return f32(f32(delta)*f32(query['timestamp_period_ns']))/1000.


def main():
    C.require(not OUTPUT.exists() and not WORK.exists(),'fresh post-hoc replay required')
    A.quiet();os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),'one numerical thread')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180);started,cpu = time.monotonic(),time.process_time()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),Path(A.__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])==R.checked(path),
                  'commit exact post-hoc replay source before use')
    record = C.read(A.OUTPUT)
    C.require(record['complete'] and record['native_returncode']==0
        and record['classification']=='RAW_QUERY_PILOT_FAILURE_PARTIALS_RETAINED'
        and record['failure']=='continuation quality proof: raw image/optional-interval/native aggregate mismatch',
        'exact preserved507 intake failure required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in record[group].items():R.checked(path,digest)
    own = C.read(A.WORK/'native.resources.json')
    C.require(own['pid']==own['pgid']==record['native_pid'] and type(own['start_ticks']) is int
        and own['boot_id']==record['environment']['boot_id'] and own['command']==record['command']
        and own['affinity']==[31] and own['nice']==15 and own['cpu']==[120,120]
        and own['address_space']==[-1,-1] and own['elapsed_limit_seconds']==180
        and 0<record['elapsed_seconds']<180 and 0<=record['child_cpu_seconds']<=120,'actual native/resource mismatch')
    build = C.read(R.RESULTS/'506-raw-query-pilot-build.json')
    C.require(build['complete'] and build['build_valid'],'actual build506 required')
    C.require(record['command'][2]==build['binaries']['dense'],'actual native binary differs')
    old = next(r for r in C.read(R.RESULTS/'015-dense-rc-pilot.json')['rows'] if r['cell']=='C7')
    prior = Path(old['command'][old['command'].index('--out')+1])
    C.require(old['returncode']==0,'original dense evidence failed')
    for name,digest in old['payload_sha256'].items():R.checked(prior/name,digest)
    lock,view = C.read(A.LOCK),C.read(A.VIEW)
    state = R.ROOT/lock['cells']['C7']['state_directory'];capture = A.WORK/'capture'
    expected_command = ['bash',str(R.ROOT/'scripts/run_with_vulkan.sh'),build['binaries']['dense'],
        '--state',str(state.resolve()),'--out',str(capture),'--family','dense-rc',
        '--spp','1','--vertices','2','--seed','305419896','--frames','1']
    C.require(record['command']==expected_command,'exact original full command differs')
    for name,key in (('geometry-state.bin','geometry'),('frame-state.bin','frame')):
        expected = R.checked(state/name,lock['cells']['C7']['state_sha256'][key])
        C.require(R.checked(capture/name)==R.checked(prior/name)==R.checked(capture/'frames/0'/name)==expected,
                  'full original static physical state differs')
    for component in ('direct','indirect','total'):
        name = component+'.pfm'
        C.require(R.checked(capture/name)==R.checked(prior/name)==R.checked(capture/'frames/0'/name),
                  'full original dense image differs')
    metadata = C.read(capture/'frames.json')
    C.require((metadata['family'],metadata['vertices'],metadata['spp'],metadata['seed'],metadata['width'],metadata['height'])
        ==('dense-rc',2,1,305419896,320,180) and len(metadata['frames'])==1,'full image/budget scope differs')
    frame = metadata['frames'][0]
    C.require((frame['index'],frame['state'],frame['seed'],frame['dose'],frame['changed_slots'])
        ==(0,'static',305419896,0,0),'full frame identity differs')
    raw = A.trace(A.WORK/'raw-queries.jsonl')
    queries = [json.loads(line) for line in R.checked(A.WORK/'raw-queries.jsonl').splitlines()]
    query = next(q for q in queries if q['kind']=='query' and q['phase']=='static' and q['count']==4)
    converted = dict(image_gpu_us=native_interval(query,0,1),known_work_gpu_us=native_interval(query,2,3))
    C.require(R.close(converted['image_gpu_us'],frame['image_gpu_us'])
        and R.close(converted['known_work_gpu_us'],frame['known_work_gpu_us'])
        and R.close(frame['gpu_us'],frame['image_gpu_us']+frame['maintenance_gpu_us']),
        'source-exact native binary32 aggregate mismatch')
    # Retain source expression instead of silently reinterpreting its arithmetic.
    source = R.BASE/'raw-query-pilot-source-v1/dense.cpp'
    body = R.checked(source).decode()
    C.require('return (ts[1]-ts[0])*context.timestamp_period_ns()/1000.;' in body
        and 'n::NeutralWork::last_gpu_us=(ts[3]-ts[2])*context.timestamp_period_ns()/1000.;' in body,
        'original native timer expression changed')
    peak = R.ledger_replay(capture/'allocation-ledger.json')
    WORK.mkdir()
    result = dict(schema='n010-posthoc-raw-query-pilot-replay/1',complete=False,posthoc=True,
        native_executed=False,source_commit=commit,input_sha256=R.INPUTS,source_capture=str(A.OUTPUT),
        classification='POSTHOC_FULL_RAW_DENSE_ANALYSIS_PENDING',execution_evidence_valid=False,
        quality_evidence_valid=False,accepted_timing=False,reference_admission=False,gpu_run=False)
    try:
        scores = []
        for vertices in (2,8):
            ref = Path(view['work'])/f'C7_T_B{vertices}'
            entry = next(r for r in view['rows'] if r['name']==ref.name)
            C.require(ref.is_symlink() and str(ref.resolve())==entry['target'],'fixed reference view differs')
            proof = H.verify_reference(ref,'C7',vertices,lock['cells']['C7'],R.INPUTS)
            q = C.read(ref/'qualification.json')
            score = S.score(capture,q,ref,WORK/f'quality-B{vertices}.json')
            C.require(score['scoring_exclusions']==0 and all(m['pixels']==57600 and m['scoring_exclusions']==0
                for m in score['components'].values()),'full scored pixels required')
            with (WORK/f'quality-B{vertices}.json').open('x') as stream:stream.write(json.dumps(score,indent=2,allow_nan=False)+'\n')
            scores.append(dict(vertices=vertices,reference_proof=proof,quality=score))
        for path,digest in list(R.INPUTS.items()):R.checked(path,digest)
        result.update(complete=True,execution_evidence_valid=True,quality_evidence_valid=True,
            classification='POSTHOC_COMPLETE_FULL_C7_DENSE_RAW_PILOT_NO_SPEED_CLAIM',
            original_full_image_state_bytes_exact=True,owned_peak_bytes=peak,owned_teardown_zero=True,
            validation=raw,native_converted_fields=converted,scores=scores,
            raw_minus_native_image_gpu_us=raw['image_gpu_us']-frame['image_gpu_us'],
            original507_failure_unchanged=True,timing_precision='TIMING_INCONCLUSIVE')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(complete=True,failure=str(error),classification='POSTHOC_RAW_DENSE_REPLAY_FAILURE_RETAINED')
    result.update(elapsed_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
        payload_sha256={str(p):P.sha(p) for p in WORK.rglob('*') if p.is_file()},
        tests='NOT_RUN; post-hoc CPU full native/raw/physical/quality replay only')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0)
    print(json.dumps({k:result.get(k) for k in ('classification','execution_evidence_valid','quality_evidence_valid',
        'failure','validation','native_converted_fields','raw_minus_native_image_gpu_us')},indent=2))
    return 0 if result['quality_evidence_valid'] else 2


if __name__ == '__main__':raise SystemExit(main())

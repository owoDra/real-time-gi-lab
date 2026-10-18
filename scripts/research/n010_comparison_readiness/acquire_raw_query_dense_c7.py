#!/usr/bin/env python3
"""Plan150: exactly one full static C7 dense native and independent raw intake."""
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

import continuation_quality_provenance as C
from continuation_quality_provenance import R,P
import hybrid_reference_provenance as H
import score_hdr as S
from acquire_continuation_quality_case import identity_environment
from build_raw_query_pilots import quiet

PLAN = R.RESULTS.parent/'experiments/150-first-raw-query-dense-pilot.md'
WORK = R.BASE/'raw-query-pilot-cases-v1/static-C7-dense-rc'
OUTPUT = R.RESULTS/'507-raw-query-static-c7-dense-pilot.json'
LOCK = R.RESULTS/'026-dynamic-execution-state-lock.json'
VIEW = R.RESULTS/'160-primary-direction-reference-view.json'


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def trace(path):
    rows = [json.loads(line) for line in R.checked(path).splitlines()]
    contexts,queries,fences,phases = {},[],[],[]
    active = (-1,'setup')
    for i,row in enumerate(rows):
        C.require(row['sequence']==i,'raw query sequence differs')
        kind = row['kind']
        if kind == 'context':
            c = row['context']
            C.require(type(c) is int and c>0 and c not in contexts
                and R.positive(row['timestamp_period_ns'])
                and type(row['timestamp_valid_bits']) is int and 1<=row['timestamp_valid_bits']<=64
                and type(row['queue_family']) is int and row['queue_family']>=0,'raw context metadata invalid')
            contexts[c] = row
        elif kind == 'phase':
            active = (row['frame'],row['phase']);phases.append(active)
        else:
            C.require(row['context'] in contexts and (row['frame'],row['phase'])==active,'unregistered context/phase')
            C.require(row['result']==0,'failed raw Vulkan call')
            if kind == 'fence':
                C.require(0<=row['bounded_timeout_ns']<=500000000
                    and row['bounded_timeout_ns']==min(row['requested_timeout_ns'],500000000)
                    and row['count']>0 and row['wait_all'] in (0,1),'fence guard differs')
                fences.append(row)
            elif kind == 'query':
                info = contexts[row['context']]
                C.require(row['timestamp_period_ns']==info['timestamp_period_ns']
                    and row['timestamp_valid_bits']==info['timestamp_valid_bits']
                    and row['flags']==3 and row['stride']==8 and row['first']==0
                    and row['count']==len(row['ticks']) and row['count'] in (2,4)
                    and row['data_size']>=row['count']*8
                    and all(type(t) is int and 0<=t<2**64 for t in row['ticks']),'raw query layout differs')
                queries.append(row)
            else:raise ValueError('unknown raw observer record')
    C.require(contexts and queries and fences and phases==[(0,'static'),(0,'readback'),(-3,'teardown')],
              'incomplete raw static trajectory')
    frame = [q for q in queries if (q['frame'],q['phase'])==(0,'static')]
    images = [q for q in frame if q['count']==4]
    C.require(len(images)==1,'one complete image timestamp receipt required')
    image = images[0]
    def duration(q,i,j):
        period,bits = q['timestamp_period_ns'],q['timestamp_valid_bits']
        C.require(math.ldexp(period,bits)/1e9>180,'timestamp wrap range insufficient')
        return ((q['ticks'][j]-q['ticks'][i])&((1<<bits)-1))*period/1000
    image_us,empty_us = duration(image,0,1),duration(image,2,3)
    C.require(R.positive(image_us) and image_us<=250000 and 0<=empty_us<=image_us,'image timestamp guard')
    maintenance = [q for q in frame if q['count']==2]
    maintenance_us = sum(duration(q,0,1) for q in maintenance)
    C.require(all(0<=duration(q,0,1)<=500000 for q in queries if q['count']==2),'auxiliary timestamp range')
    return dict(context_count=len(contexts),query_count=len(queries),fence_count=len(fences),
        all_raw_records_retained=True,image_gpu_us=image_us,empty_optional_interval_gpu_us=empty_us,
        raw_maintenance_gpu_us=maintenance_us,complete_renderer_gpu_us=image_us+maintenance_us,
        maintenance_receipts=len(maintenance),precision='TIMING_INCONCLUSIVE',accepted_timing=False)


def main():
    C.require(not WORK.exists() and not OUTPUT.exists(),'fresh case/result required; no retry')
    quiet()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    C.require(all(os.environ.get(k)=='1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),'one numerical thread required')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))])==R.checked(path),
                  'commit exact acquisition/intake before native')
    build = C.read(R.RESULTS/'506-raw-query-pilot-build.json')
    control = C.read(R.RESULTS/'487-compensated-a6c-full-control.json')
    C.require(build['complete'] and build['build_valid'] and control['complete'] and control['all_pass'],
              'actual private build and terminal A6c PASS required')
    for proof in (build,control):
        for group in ('input_sha256','payload_sha256'):
            for path,digest in proof[group].items():R.checked(path,digest)
    scope = C.read(R.RESULTS/'503-selected-reportable-timing-scope.json')
    C.require(any(r['id']=='static-C7-dense-rc' for r in scope['rows']) and scope['full_union_count']==36,
              'original full selected pilot scope required')
    old = next(r for r in C.read(R.RESULTS/'015-dense-rc-pilot.json')['rows'] if r['cell']=='C7')
    prior = Path(old['command'][old['command'].index('--out')+1])
    C.require(old['returncode']==0,'original C7 dense archive failure')
    for name,digest in old['payload_sha256'].items():R.checked(prior/name,digest)
    lock,view = C.read(LOCK),C.read(VIEW)
    state = R.ROOT/lock['cells']['C7']['state_directory']
    for name,key in (('geometry-state.bin','geometry'),('frame-state.bin','frame')):
        R.checked(state/name,lock['cells']['C7']['state_sha256'][key])
    command = ['bash',str(R.ROOT/'scripts/run_with_vulkan.sh'),build['binaries']['dense'],
        '--state',str(state.resolve()),'--out',str(WORK/'capture'),'--family','dense-rc',
        '--spp','1','--vertices','2','--seed','305419896','--frames','1']
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('PHOS_N010_CALIBRATION') or key.startswith('PHOS_N007_') or key=='PHOS_N010_MINIMAL_CALIBRATION_READBACK':
            del env[key]
    env['PHOS_N010_RAW_QUERY_CAPTURE'] = str(WORK/'raw-queries.jsonl')
    WORK.mkdir(parents=True)
    receipt = WORK/'native.resources.json'
    record = dict(schema='n010-raw-query-pilot-part/1',complete=False,cell='C7',role='dense-rc',
        boundary_id='static-C7-dense-rc',source_commit=commit,command=command,environment=identity_environment(),
        classification='ONE_RAW_QUERY_NATIVE_ACQUIRING',execution_evidence_valid=False,
        quality_evidence_valid=False,accepted_timing=False,reference_admission=False,gpu_run=True,
        input_sha256=R.INPUTS,tests='NOT_RUN; one full scientific descriptive pilot')
    def save():OUTPUT.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    def hashes():return {str(p):P.sha(p) for p in WORK.rglob('*') if p.is_file()}
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(resource.RLIM_INFINITY,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            elapsed_limit_seconds=180))+'\n')
    save()
    try:
        quiet()
        before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
        with (WORK/'native.stdout').open('wb') as out,(WORK/'native.stderr').open('wb') as err:
            child = subprocess.Popen(command,cwd=R.ROOT,env=env,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
            record['native_pid'] = child.pid;save()
            try:code = child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                own = json.loads(receipt.read_text())
                C.require((own['pid'],own['pgid'],own['start_ticks'])==(child.pid,child.pid,start_ticks(child.pid)),
                          'owned native identity differs; refuse signalling')
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5);code='TIMEOUT_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(native_returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            classification='RAW_QUERY_NATIVE_TERMINAL_ANALYSIS_PENDING',payload_sha256=hashes())
        save()
        C.require(code==0,'native failure; retain partials, no retry')
        own = C.read(receipt)
        C.require(own['pid']==own['pgid']==child.pid and type(own['start_ticks']) is int
            and own['boot_id']==record['environment']['boot_id'] and own['command']==command
            and own['affinity']==[31] and own['nice']==15 and own['cpu']==[120,120]
            and own['address_space']==[-1,-1] and own['elapsed_limit_seconds']==180
            and record['elapsed_seconds']<180 and record['child_cpu_seconds']<=120,'actual native resource mismatch')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
        capture = WORK/'capture'
        for name in ('geometry-state.bin','frame-state.bin'):
            C.require(R.checked(capture/name)==R.checked(state/name)==R.checked(prior/name),'full physical state differs')
            C.require(R.checked(capture/'frames/0'/name)==R.checked(state/name),'full per-frame physical state differs')
        for component in ('direct','indirect','total'):
            name = component+'.pfm'
            C.require(R.checked(capture/name)==R.checked(prior/name)==R.checked(capture/'frames/0'/name),
                      'full original dense image bytes differ')
        timings = C.read(capture/'frames.json')
        C.require((timings['family'],timings['vertices'],timings['spp'],timings['seed'],timings['width'],timings['height'])
            ==('dense-rc',2,1,305419896,320,180) and len(timings['frames'])==1,'full frame scope differs')
        frame = timings['frames'][0]
        C.require((frame['index'],frame['state'],frame['seed'],frame['dose'],frame['changed_slots'])
            ==(0,'static',305419896,0,0),'frame identity differs')
        raw = trace(WORK/'raw-queries.jsonl')
        C.require(R.close(raw['image_gpu_us'],frame['image_gpu_us'])
            and R.close(raw['empty_optional_interval_gpu_us'],frame['known_work_gpu_us'])
            and R.close(frame['gpu_us'],frame['image_gpu_us']+frame['maintenance_gpu_us']),
            'raw image/optional-interval/native aggregate mismatch')
        raw['native_reported_renderer_gpu_us'] = frame['gpu_us']
        raw['additional_raw_maintenance_gpu_us'] = raw['raw_maintenance_gpu_us']-frame['maintenance_gpu_us']
        peak = R.ledger_replay(capture/'allocation-ledger.json')
        scores = []
        for vertices in (2,8):
            ref = Path(view['work'])/f'C7_T_B{vertices}'
            entry = next(r for r in view['rows'] if r['name']==ref.name)
            C.require(ref.is_symlink() and str(ref.resolve())==entry['target'],'fixed reference view differs')
            proof = H.verify_reference(ref,'C7',vertices,lock['cells']['C7'],R.INPUTS)
            q = C.read(ref/'qualification.json')
            score = S.score(capture,q,ref,WORK/f'quality-B{vertices}.json')
            C.require(score['scoring_exclusions']==0 and all(m['pixels']==57600 and m['scoring_exclusions']==0
                for m in score['components'].values()),'full pixel scoring required')
            with (WORK/f'quality-B{vertices}.json').open('x') as output:output.write(json.dumps(score,indent=2,allow_nan=False)+'\n')
            scores.append(dict(vertices=vertices,reference_proof=proof,quality=score))
        for path,digest in list(R.INPUTS.items()):R.checked(path,digest)
        record.update(complete=True,execution_evidence_valid=True,quality_evidence_valid=True,
            classification='COMPLETE_FULL_C7_DENSE_RAW_PILOT_NO_SPEED_CLAIM',validation=raw,
            original_full_image_state_bytes_exact=True,owned_peak_bytes=peak,owned_teardown_zero=True,scores=scores,
            timing_precision='TIMING_INCONCLUSIVE')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        record.update(complete=True,failure=str(error),classification='RAW_QUERY_PILOT_FAILURE_PARTIALS_RETAINED')
    record['payload_sha256'] = hashes();save();signal.alarm(0)
    print(json.dumps({k:record.get(k) for k in ('classification','execution_evidence_valid','quality_evidence_valid',
        'failure','elapsed_seconds','child_cpu_seconds','validation')},indent=2))
    return 0 if record['quality_evidence_valid'] else 2


if __name__ == '__main__':raise SystemExit(main())

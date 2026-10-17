#!/usr/bin/env python3
"""Plan111: one explicit selected-pixel probe or seed; never a native queue."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys
import time

import numpy as np
import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'whole-path-hybrid-diagnostic-v1'
BUILD = D.OUT / 'whole-path-hybrid-prototype-v1'
PLAN = D.RESULTS.parent / 'experiments/111-whole-path-hybrid-numerical-diagnostic.md'
PIXELS = [(x,y) for y in (30,150) for x in (40,120,200,280)]
SELECTED = [y*320+x for x,y in PIXELS]
PATH_DTYPE = np.dtype([('values','<f8',(4,4)),('counters','<u8',(4,))])
STATS_DTYPE = np.dtype([('sum','<f8',(4,4)),('sum2','<f8',(4,4)),('counters','<u8',(4,))])


def location(index):
    number = 353 if index is None else 354+index
    label = 'probe' if index is None else 'seed'+str(index)
    return D.RESULTS / f'{number}-whole-path-hybrid-{label}.json', WORK / label


def prior(index):
    output, _ = location(index)
    d = json.loads(D.checked(output))
    seed=D.SEEDS[0 if index is None else index]
    spp,batch=(1,1) if index is None else (8192,16)
    if not (d['schema']=='n010-whole-path-hybrid-part/1' and d['complete'] and d['all_pass']
            and d['seed_index']==index and (d['seed'],d['spp'],d['batch'])==(seed,spp,batch)
            and d['selected_pixels']==SELECTED and not d['reference_admission'] and not d['accepted_timing']
            and [(r['x'],r['y'],r['seed']) for r in d['validation']['rows']]
                ==[(x,y,seed) for x,y in PIXELS]):
        raise ValueError('terminal successful prior hybrid part required')
    for path,digest in d['payload_sha256'].items():
        D.checked(Path(path),digest)
    for path,digest in d['input_sha256'].items():
        D.checked(Path(path),digest)
    return d


def hit_record(data,pixel):
    if data[:8]!=b'N008HIT\0' or struct.unpack_from('<II',data,8)!=(320,180):
        raise ValueError('original hit shape differs')
    if len(data)!=16+320*180*16:
        raise ValueError('original hit length differs')
    return data[16+pixel*16:16+(pixel+1)*16]


def validate(directory,seed,spp,batch,expected,probe_rows,original_hits):
    def read(name):return json.loads((directory/name).read_text())
    meta,scope,hybrid=read('gpu.json'),read('prototype-scope.json'),read('hybrid.json')
    if (meta['schema']!='n010-whole-path-eight-pixel-hybrid/1' or
            (meta['width'],meta['height'],meta['vertices'],meta['spp'],meta['seed'])!=(320,180,8,spp,seed)
            or meta['fault_flags'] or not meta['all_finite'] or meta['eligible_for_references']):
        raise ValueError('prototype identity/fault/finite scope differs')
    if (scope['selected_pixels']!=SELECTED or scope['selection_scope']!='eight_fixed_pixels_only'
            or scope['seed']!=seed or scope['spp']!=spp or scope['path_record_bytes']!=160
            or scope['primary_record_bytes']!=192 or scope['flag_record_bytes']!=4
            or scope['reference_admission']):
        raise ValueError('prototype selection/stream layout differs')
    batches=[json.loads(line) for line in (directory/'batches.jsonl').read_text().splitlines()]
    intervals=[(begin,min(spp,begin+batch)) for begin in range(0,spp,batch)]
    if len(batches)!=len(intervals):raise ValueError('missing batch interval')
    for row,(begin,end) in zip(batches,intervals):
        wall=row['submit_wait_wall_seconds_diagnostic']
        if ((row['begin'],row['end'],row['selected_count'])!=(begin,end,8)
                or row['complete'] is not True or not math.isfinite(wall) or not 0<=wall<=.250):
            raise ValueError('incomplete/incorrect/stopped batch retained')
    paths=np.fromfile(directory/'corrected-paths.bin',dtype=PATH_DTYPE)
    raw=np.fromfile(directory/'gpu-paths.bin',dtype=PATH_DTYPE)
    flags=np.fromfile(directory/'routing-flags.bin',dtype='<u4')
    for name,width in (('corrected-paths.bin',160),('gpu-paths.bin',160),('routing-flags.bin',4)):
        if (directory/name).stat().st_size!=8*spp*width:raise ValueError('incomplete stream '+name)
    if np.any(flags>1):raise ValueError('unknown sample routing flag')
    a=raw.view(np.uint8).reshape(-1,160);b=paths.view(np.uint8).reshape(-1,160)
    if not np.array_equal(a[flags==0],b[flags==0]):raise ValueError('unflagged sample changed')
    if not (np.isfinite(paths['values']).all() and (paths['values']>=0).all()):
        raise ValueError('invalid corrected path')
    if np.any(paths['values'][:,:,3]):raise ValueError('unexpected component padding')
    if (hybrid['total_paths']!=8*spp or hybrid['cpu_fallback_paths']!=int(np.count_nonzero(flags))
            or hybrid['cpu_threads']!=1 or hybrid['batch']!=batch or hybrid['eligible_for_references']):
        raise ValueError('fallback bookkeeping differs')
    rebuilt=np.zeros(8,dtype=STATS_DTYPE)
    raw_rebuilt=np.zeros(8,dtype=STATS_DTYPE)
    offset=0
    for begin,end in intervals:
        for slot in range(8):
            for _ in range(begin,end):
                value=paths[offset];raw_value=raw[offset];offset+=1
                rebuilt['sum'][slot]+=value['values']
                rebuilt['sum2'][slot]+=value['values']*value['values']
                rebuilt['counters'][slot]+=value['counters']
                with np.errstate(invalid='ignore',over='ignore'):
                    raw_rebuilt['sum'][slot]+=raw_value['values']
                    raw_rebuilt['sum2'][slot]+=raw_value['values']*raw_value['values']
                raw_rebuilt['counters'][slot]+=raw_value['counters']
    stats=np.fromfile(directory/'gpu.stats',dtype=STATS_DTYPE)
    if (directory/'gpu.stats').stat().st_size!=8*288 or stats.tobytes()!=rebuilt.tobytes():
        raise ValueError('corrected stream/stats bits differ')
    side=(directory/'o.f64').read_bytes()
    if (side[:8]!=b'N008F64\0' or struct.unpack_from('<IIIQ',side,8)!=(320,180,spp,seed)
            or len(side)!=28+320*180*24*8):raise ValueError('sparse sidecar identity differs')
    values=np.frombuffer(side,dtype='<f8',offset=28).reshape(320*180,2,4,3)
    mean=stats['sum'][:,:,:3]/spp;second=stats['sum2'][:,:,:3]/spp
    if values[SELECTED,0].tobytes()!=mean.tobytes() or values[SELECTED,1].tobytes()!=second.tobytes():
        raise ValueError('sparse sidecar/stats bits differ')
    mask=np.ones(320*180,dtype=bool);mask[SELECTED]=False
    if np.any(values[mask]):raise ValueError('unexpected computation outside fixed selection')
    primary=(directory/'primary-records.bin').read_bytes()
    hits=(directory/'o.hits').read_bytes()
    if len(primary)!=8*192:raise ValueError('primary record length differs')
    rows=[]
    for slot,((x,y),cpu,probe) in enumerate(zip(PIXELS,expected,probe_rows)):
        if (cpu['x'],cpu['y'],cpu['seed'])!=(x,y,seed):raise ValueError('CPU record identity differs')
        p=primary[192*slot:192*(slot+1)]
        want_primary=struct.pack('<20d4Q',*probe['primary_doubles'],1,
                                 probe['cache_shadow_tests'],probe['cache_shadow_blocked'],0)
        if p!=want_primary:raise ValueError('independent CPU primary/cache bits differ')
        if hit_record(hits,SELECTED[slot])!=hit_record(original_hits,SELECTED[slot]):
            raise ValueError('original primary hit bits differ')
        cpu_mean=np.asarray(cpu['mean'],dtype='<f8').reshape(4,3)
        cpu_second=np.asarray(cpu['second'],dtype='<f8').reshape(4,3)
        counter=stats['counters'][slot].tolist()
        if counter!=cpu['counters']:raise ValueError('scored integer counters differ')
        if mean[slot,:2].tobytes()!=cpu_mean[:2].tobytes() or second[slot,:2].tobytes()!=cpu_second[:2].tobytes():
            raise ValueError('deterministic mean/moment bits differ')
        rows.append(dict(x=x,y=y,seed=seed,counters=counter,
                         max_abs_mean=float(np.max(np.abs(mean[slot]-cpu_mean))),
                         max_abs_second=float(np.max(np.abs(second[slot]-cpu_second)))))
    cpu_means=np.asarray([row['mean'] for row in expected],dtype=np.float64).reshape(8,4,3)
    cpu_seconds=np.asarray([row['second'] for row in expected],dtype=np.float64).reshape(8,4,3)
    difference=mean[:,2]-cpu_means[:,2]
    den=float(np.sum(cpu_means[:,2]**2));num=float(np.sum(difference**2))
    nrmse=math.sqrt(num/den) if den else (0.0 if num==0 else None)
    if nrmse is None or nrmse>1e-8 or any(r['max_abs_mean']>1e-10 or r['max_abs_second']>1e-10 for r in rows):
        raise ValueError('frozen numerical tolerance failed')
    sys.path.insert(0,str(D.HERE.parent/'n010_comparison_readiness'))
    from readiness_preflight import replay
    ledger=read('allocation-ledger.json')
    if not replay(ledger):raise ValueError('owned allocation ledger failed')
    counters=stats['counters'].sum(axis=0).tolist()
    if [meta[k] for k in ('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')]!=counters:
        raise ValueError('metadata counters differ')
    def finite_error(gpu,cpu):
        if not np.isfinite(gpu).all():return None
        return float(np.max(np.abs(gpu-cpu)))
    return dict(rows=rows,indirect_nrmse=nrmse,owned_memory_replay_pass=True,
                true_peak_owned_bytes=ledger['true_peak_owned_bytes'],
                cpu_fallback_paths=int(np.count_nonzero(flags)),total_paths=8*spp,
                cpu_fallback_fraction=float(np.count_nonzero(flags))/(8*spp),
                unflagged_raw_corrected_bytes_equal=True,corrected_stream_stats_sidecar_bits_equal=True,
                raw_nonfinite_values=int(np.count_nonzero(~np.isfinite(raw['values']))),
                raw_gpu_diagnostic=dict(
                    max_abs_mean=finite_error(raw_rebuilt['sum'][:,:,:3]/spp,cpu_means),
                    max_abs_second=finite_error(raw_rebuilt['sum2'][:,:,:3]/spp,cpu_seconds),
                    counter_disagreements=int(np.count_nonzero(raw_rebuilt['counters']!=stats['counters'])),
                    scope='Every raw sample retained, including flagged/nonfinite; not acceptance values'),
                max_batch_submit_wait_wall_diagnostic=max(r['submit_wait_wall_seconds_diagnostic'] for r in batches))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--probe',action='store_true')
    group.add_argument('--seed-index',type=int,choices=range(4))
    group.add_argument('--summarize',action='store_true')
    args=parser.parse_args()
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__).resolve(),PLAN,Path(C.__file__),Path(D.__file__),
              D.HERE/'run_primary_direction_sequence.py'):
        D.checked(p)
    if args.summarize:
        output=D.RESULTS/'358-whole-path-hybrid-numerical.json'
        if output.exists():raise ValueError('refuse existing summary')
        parts=[prior(i) for i in range(4)]
        prior(None)
        output.write_text(json.dumps(dict(schema='n010-whole-path-hybrid-numerical/1',
            complete=True,all_pass=True,classification='SELECTED_C1_NUMERICAL_PASS_NO_ADMISSION',
            reference_admission=False,accepted_timing=False,gpu_run=False,
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            input_sha256=D.INPUTS,parts=[str(location(i)[0]) for i in range(4)],
            rows=[row for part in parts for row in part['validation']['rows']],
            scope='All32 selected-pixel numerical pairs only; no full-frame/physical/bias/state/prefix/feasibility qualification.'),
            indent=2,allow_nan=False)+'\n')
        print('SELECTED C1 NUMERICAL PASS; NO ADMISSION');return
    index=None if args.probe else args.seed_index
    output,work=location(index)
    if output.exists() or work.exists():raise ValueError('refuse existing part; no retry')
    if index is not None:
        prior(None)
        for i in range(index):prior(i)
    build=C.pinned_result('352');cpu=C.pinned_result('254');coverage=C.pinned_result('257')
    if not all(d['all_pass'] for d in (build,cpu,coverage)):raise ValueError('successful352/254/257 required')
    for p,h in build['input_sha256'].items():D.checked(Path(p),h)
    acquisition=cpu['attempts'][1]['command']
    scene,net=Path(acquisition[2]),Path(acquisition[1])
    for path in (scene,net):D.checked(path,cpu['input_sha256'][str(path)])
    baseline=json.loads(D.checked(Path(acquisition[4]),cpu['payload_sha256'][acquisition[4]]))
    if [(r['x'],r['y'],r['seed']) for r in baseline]!=[(x,y,s) for x,y in PIXELS for s in D.SEEDS]:
        raise ValueError('original32 paired rows differ')
    old_meta=json.loads(D.checked(scene.parent/'n8192.meta.json'))
    if (old_meta['scene_sha256']!=C.sha(scene) or old_meta['seeds']!=list(D.SEEDS)
            or (old_meta['width'],old_meta['height'],old_meta['spp'])!=(320,180,8192)):
        raise ValueError('original scene/seed/count metadata differs')
    original_hits=D.checked(scene.parent/'o.n8192.hits')
    for file in ('readiness_preflight.py','calibrate_renderer.py','reference_provenance.py'):
        D.checked(D.HERE.parent/'n010_comparison_readiness'/file)
    seed=D.SEEDS[0 if index is None else index];spp=1 if index is None else 8192
    batch=1 if index is None else 16
    work.mkdir(parents=True)
    result=dict(schema='n010-whole-path-hybrid-part/1',complete=False,all_pass=False,
        classification='SELECTED_C1_NUMERICAL_ACQUIRING',seed_index=index,seed=seed,spp=spp,batch=batch,
        gpu_run=False,reference_admission=False,accepted_timing=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=D.INPUTS,attempts=[],selected_pixels=SELECTED,
        thresholds=dict(max_abs_mean_and_second=1e-10,indirect_nrmse=1e-8,counter_disagreements=0),
        tests='NOT_RUN; registered scientific numerical diagnostic only')
    def save():output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    def run(command,label,cpu_limit,elapsed_limit):
        receipt=work/(label+'.resources.json')
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(cpu_limit,)*2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
        row=dict(label=label,command=command,cpu_limit=cpu_limit,elapsed_limit=elapsed_limit,
                 resource_receipt=str(receipt),terminal=False)
        result['attempts'].append(row);save()
        started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            child=subprocess.run(command,capture_output=True,timeout=elapsed_limit,preexec_fn=limits)
            stdout,stderr=child.stdout,child.stderr;row.update(terminal=True,returncode=child.returncode)
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b''
            row.update(terminal=True,returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',failure='ELAPSED_GUARD_NO_RETRY')
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        (work/(label+'.stdout')).write_bytes(stdout);(work/(label+'.stderr')).write_bytes(stderr)
        row.update(elapsed_seconds=time.monotonic()-started,
                   child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime);save()
        actual=json.loads(D.checked(receipt))
        if (actual['cpu']!=[cpu_limit]*2 or actual['address_space']!=[4*1024**3]*2
                or actual['affinity']!=[31] or actual['nice']!=15 or row['returncode']!=0):
            raise ValueError('native terminal/resources failure; no retry')
    save()
    try:
        if index is None:
            run([str(BUILD/'n010_whole_cpu_probe'),str(net),str(scene),str(seed),str(work/'cpu-probe.json')],
                'cpu-probe',30,60)
            probe_rows=json.loads(D.checked(work/'cpu-probe.json'))
            expected=probe_rows
            if len(probe_rows)!=8:raise ValueError('all8 independent CPU probe rows required')
            for pixel,row in zip(SELECTED,probe_rows):
                want=struct.pack('<dII',row['primary_t'],row['primary_triangle'],row['primary_front'])
                if hit_record(original_hits,pixel)!=want:raise ValueError('independent CPU/original primary bits differ')
        else:
            _,probe_work=location(None)
            probe_rows=json.loads(D.checked(probe_work/'cpu-probe.json'))
            expected=[]
            for (x,y),probe in zip(PIXELS,probe_rows):
                row=next(r for r in baseline if (r['x'],r['y'],r['seed'])==(x,y,seed))
                expected.append(dict(x=x,y=y,seed=seed,mean=row['mixture_mean'],second=row['mixture_second'],
                    counters=[8192,probe['cache_shadow_tests']*8192+row['audit']['endpoint_shadow_tests'],
                              probe['cache_shadow_blocked']*8192+row['audit']['endpoint_shadow_blocked'],0]))
        result['gpu_run']=True;save()
        # Wrapper execs the native, preserving the recorded PID/start/resource identity.
        D.checked(D.ROOT/'scripts/run_with_vulkan.sh')
        run(['bash',str(D.ROOT/'scripts/run_with_vulkan.sh'),str(BUILD/'phos-n010-whole-hybrid-prototype'),
             str(scene),str(net),str(BUILD/'prototype.spv'),str(seed),str(spp),str(batch),'1',str(work/'gpu')],
            'gpu',60 if index is None else 360,90 if index is None else 600)
        result['validation']=validate(work/'gpu',seed,spp,batch,expected,probe_rows,original_hits)
        if json.loads((work/'gpu/gpu.json').read_text())['geometry_sha256']!=old_meta['geometry_sha256']:
            raise ValueError('original geometry identity differs')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(all_pass=True,classification='SELECTED_C1_NUMERICAL_PART_PASS_NO_ADMISSION')
    except (ValueError,OSError,KeyError,StopIteration,AssertionError,struct.error,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='SELECTED_C1_NUMERICAL_FAILURE_RETAINED')
    result['complete']=True
    result['payload_sha256']={str(p):C.sha(p) for p in work.rglob('*') if p.is_file()}
    save();print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':main()

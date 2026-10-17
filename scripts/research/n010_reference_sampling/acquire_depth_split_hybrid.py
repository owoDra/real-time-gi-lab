#!/usr/bin/env python3
"""Plan113: one manual depth-split numerical acquisition; never a queue."""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import shutil
import struct
import subprocess
import time

import numpy as np
import acquire_whole_path_hybrid as H
import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN=D.RESULTS.parent/'experiments/113-depth-split-hybrid-numerical-diagnostic.md'
BUILD=D.OUT/'whole-path-full-frame-build-v1'
WORK=D.OUT/'depth-split-hybrid-diagnostic-v1'
PART_DTYPE=np.dtype([('value','<f8',(4,)),('counts','<u8',(4,)),('proposal','<u8',(4,)),('maxima','<f8',(4,))])


def location(index):
    label='probe' if index is None else 'seed'+str(index)
    return D.RESULTS/f'{361 if index is None else 362+index}-depth-split-hybrid-{label}.json',WORK/label


def prior(index):
    output,_=location(index);data=json.loads(D.checked(output))
    seed=D.SEEDS[0 if index is None else index];spp,batch=(1,1) if index is None else (8192,16)
    if not (data['schema']=='n010-depth-split-hybrid-part/1' and data['complete'] and data['all_pass']
            and (data['seed_index'],data['seed'],data['spp'],data['batch'],data['tile'])==(index,seed,spp,batch,8)
            and data['selected_pixels']==H.SELECTED and not data['reference_admission'] and not data['accepted_timing']
            and [(r['x'],r['y'],r['seed']) for r in data['validation']['rows']]==[(x,y,seed) for x,y in H.PIXELS]):
        raise ValueError('successful exact prior depth-split part required')
    for key in ('input_sha256','payload_sha256'):
        for p,h in data[key].items():D.checked(Path(p),h)
    return data


def validate(directory,seed,spp,batch,expected,probe_rows,original_hits,build,scene,net,original_meta):
    def read(name):return json.loads((directory/name).read_text())
    meta,scope=read('gpu.json'),read('scope.json')
    if (meta['schema']!='n010-tiled-depth-split-whole-hybrid/1'
            or (meta['width'],meta['height'],meta['vertices'],meta['spp'],meta['seed'],meta['begin_spp'],meta['batch'],meta['tile_capacity'],meta['selected_count'])
                !=(320,180,8,spp,seed,0,batch,8,8)
            or meta['mode']!='diagnostic8' or meta['backend_id']!=build['backend_id']
            or meta['scene_sha256']!=C.sha(scene) or meta['net_sha256']!=C.sha(net)
            or meta['geometry_sha256']!=original_meta['geometry_sha256']
            or meta['fault_flags'] or not meta['all_finite'] or meta['reference_admission'] or meta['accepted_timing']):
        raise ValueError('new backend identity/fault/scope differs')
    if (scope['schema']!='n010-tiled-whole-scope/1' or scope['mode']!='diagnostic8'
            or scope['selected_pixels']!=H.SELECTED
            or (scope['spp'],scope['begin_spp'],scope['seed'],scope['batch'],scope['tile_capacity'])!=(spp,0,seed,batch,8)
            or (scope['raw_path_record_bytes'],scope['part_record_bytes'],scope['primary_record_bytes'])!=(160,128,192)
            or scope['reference_admission']):raise ValueError('scope/stream layout differs')
    intervals=[(begin,min(spp,begin+batch)) for begin in range(0,spp,batch)]
    batches=[json.loads(line) for line in (directory/'batches.jsonl').read_text().splitlines()]
    dispatches=[json.loads(line) for line in (directory/'dispatches.jsonl').read_text().splitlines()]
    if len(batches)!=len(intervals) or len(dispatches)!=7*len(intervals):raise ValueError('missing dispatch/tile')
    walls=[]
    for i,((begin,end),row) in enumerate(zip(intervals,batches)):
        if (row['begin'],row['end'],row['tile_begin'],row['selected_count'],row['complete'])!=(begin,end,0,8,True):
            raise ValueError('incomplete/wrong tile')
        for depth,dispatch in enumerate(dispatches[7*i:7*i+7],1):
            if (dispatch['begin'],dispatch['end'],dispatch['tile_begin'],dispatch['tile_count'],dispatch['depth'])!=(begin,end,0,8,depth):
                raise ValueError('wrong depth/interval')
            wall=dispatch['submit_wait_wall_seconds_diagnostic'];walls.append(wall)
            if not math.isfinite(wall) or not 0<=wall<=.250:raise ValueError('operationally stopped dispatch')
        if row['max_depth_submit_wait_wall_seconds_diagnostic']!=max(walls[-7:]):raise ValueError('tile wall annotation differs')
    for name,width in [('gpu-paths.bin',160),('corrected-paths.bin',160),('routing-flags.bin',4),('gpu-parts.bin',7*128)]:
        if (directory/name).stat().st_size!=8*spp*width:raise ValueError('incomplete stream '+name)
    raw=np.fromfile(directory/'gpu-paths.bin',dtype=H.PATH_DTYPE)
    corrected=np.fromfile(directory/'corrected-paths.bin',dtype=H.PATH_DTYPE)
    flags=np.fromfile(directory/'routing-flags.bin',dtype='<u4')
    parts=np.fromfile(directory/'gpu-parts.bin',dtype=PART_DTYPE).reshape(-1,7)
    if np.any(flags&np.uint32(~63 & 0xffffffff)):raise ValueError('unknown route bit')
    if not np.array_equal(raw.view('u1').reshape(-1,160)[flags==0],corrected.view('u1').reshape(-1,160)[flags==0]):
        raise ValueError('unflagged sample changed')
    if not np.isfinite(corrected['values']).all() or np.any(corrected['values']<0) or np.any(corrected['values'][:,:,3]):
        raise ValueError('invalid corrected sample/padding')
    primary=(directory/'primary-records.bin').read_bytes();hits=(directory/'o.hits').read_bytes()
    if len(primary)!=8*192:raise ValueError('primary byte length differs')
    primary_dtype=np.dtype([('values','<f8',(5,4)),('counters','<u8',(4,))])
    primary_values=np.frombuffer(primary,dtype=primary_dtype)
    slots=np.tile(np.repeat(np.arange(8),batch),spp//batch)
    rebuilt_raw=np.zeros(8*spp,dtype=H.PATH_DTYPE)
    rebuilt_raw['values'][:,0]=primary_values['values'][slots,4]
    rebuilt_raw['values'][:,1]=primary_values['values'][slots,3]
    rebuilt_raw['counters']=primary_values['counters'][slots]
    with np.errstate(invalid='ignore',over='ignore'):
        for depth in range(7):
            rebuilt_raw['values'][:,2,:3]+=parts['value'][:,depth,:3]
            rebuilt_raw['counters'][:,1:3]+=parts['counts'][:,depth,:2]
        rebuilt_raw['values'][:,3,:3]=(rebuilt_raw['values'][:,0,:3]+rebuilt_raw['values'][:,1,:3])+rebuilt_raw['values'][:,2,:3]
    if rebuilt_raw.tobytes()!=raw.tobytes():raise ValueError('depth parts/raw path bits differ')
    reasons=[int(np.count_nonzero(flags&(1<<bit))) for bit in range(6)]
    fallback=int(np.count_nonzero(flags))
    if (meta['routing_reason_counts']!=reasons or meta['cpu_fallback_paths_new_interval']!=fallback
            or meta['new_scored_paths']!=8*spp or meta['max_depth_submit_wait_wall_seconds_diagnostic']!=max(walls)):
        raise ValueError('global routing/path annotations differ')
    for i,row in enumerate(batches):
        chunk=flags[i*8*batch:(i+1)*8*batch]
        if row['cpu_fallback_paths']!=int(np.count_nonzero(chunk)) or row['reason_counts']!=[int(np.count_nonzero(chunk&(1<<b))) for b in range(6)]:
            raise ValueError('tile routing annotations differ')
    stats=np.fromfile(directory/'gpu.stats',dtype=H.STATS_DTYPE)
    if len(stats)!=320*180 or (directory/'gpu.stats').stat().st_size!=320*180*288:raise ValueError('full-layout stats differ')
    rebuilt=np.zeros(8,dtype=H.STATS_DTYPE);raw_stats=np.zeros(8,dtype=H.STATS_DTYPE)
    for i,slot in enumerate(slots):
        for dst,src in ((rebuilt,corrected),(raw_stats,raw)):
            with np.errstate(invalid='ignore',over='ignore'):
                dst['sum'][slot]+=src['values'][i];dst['sum2'][slot]+=src['values'][i]*src['values'][i]
            dst['counters'][slot]+=src['counters'][i]
    if rebuilt.tobytes()!=stats[H.SELECTED].tobytes():raise ValueError('corrected stream/stats bits differ')
    outside=np.ones(320*180,dtype=bool);outside[H.SELECTED]=False
    if np.any(stats[outside].view('u1')):raise ValueError('uncomputed stats nonzero')
    counts=np.fromfile(directory/'sample-counts.bin',dtype='<u4')
    if len(counts)!=320*180 or np.any(counts[outside]) or not np.all(counts[H.SELECTED]==spp):raise ValueError('pixel counts differ')
    side=(directory/'o.f64').read_bytes()
    if side[:8]!=b'N008F64\0' or struct.unpack_from('<IIIQ',side,8)!=(320,180,spp,seed) or len(side)!=28+320*180*192:
        raise ValueError('sidecar identity differs')
    values=np.frombuffer(side,dtype='<f8',offset=28).reshape(320*180,2,4,3)
    mean=rebuilt['sum'][:,:,:3]/spp;second=rebuilt['sum2'][:,:,:3]/spp
    if values[H.SELECTED,0].tobytes()!=mean.tobytes() or values[H.SELECTED,1].tobytes()!=second.tobytes() or np.any(values[outside]):
        raise ValueError('sidecar/stats/uncomputed bits differ')
    rows=[]
    for slot,((x,y),cpu,probe) in enumerate(zip(H.PIXELS,expected,probe_rows)):
        if (cpu['x'],cpu['y'],cpu['seed'])!=(x,y,seed):raise ValueError('CPU row identity differs')
        want=struct.pack('<20d4Q',*probe['primary_doubles'],1,probe['cache_shadow_tests'],probe['cache_shadow_blocked'],0)
        if primary[slot*192:(slot+1)*192]!=want or H.hit_record(hits,H.SELECTED[slot])!=H.hit_record(original_hits,H.SELECTED[slot]):
            raise ValueError('independent primary/cache/hit bits differ')
        cpu_mean=np.asarray(cpu['mean'],dtype='<f8').reshape(4,3);cpu_second=np.asarray(cpu['second'],dtype='<f8').reshape(4,3)
        if rebuilt['counters'][slot].tolist()!=cpu['counters'] or mean[slot,:2].tobytes()!=cpu_mean[:2].tobytes() or second[slot,:2].tobytes()!=cpu_second[:2].tobytes():
            raise ValueError('scored counts/deterministic means/moments differ')
        rows.append(dict(x=x,y=y,seed=seed,max_abs_mean=float(np.max(np.abs(mean[slot]-cpu_mean))),max_abs_second=float(np.max(np.abs(second[slot]-cpu_second)))))
    cpu_means=np.asarray([r['mean'] for r in expected]).reshape(8,4,3);cpu_seconds=np.asarray([r['second'] for r in expected]).reshape(8,4,3)
    num=float(np.sum((mean[:,2]-cpu_means[:,2])**2));den=float(np.sum(cpu_means[:,2]**2))
    nrmse=math.sqrt(num/den) if den else (0 if num==0 else None)
    if nrmse is None or nrmse>1e-8 or any(r['max_abs_mean']>1e-10 or r['max_abs_second']>1e-10 for r in rows):raise ValueError('frozen numerical tolerance failed')
    audit=meta['all_split'];keys=('proposal_bvh_queries','component_attempts','component_nulls','own_checks')
    maxima=('max_own_log_error_bound','max_conditioned_error_fraction','max_unconditioned_error_fraction','max_weight')
    if (directory/'audit.bin').read_bytes()!=struct.pack('<4Q4d',*[audit[k] for k in keys],*[audit[k] for k in maxima]):raise ValueError('audit binary/meta bits differ')
    if (audit['component_attempts']!=8*spp*7 or audit['component_nulls']+audit['own_checks']!=audit['component_attempts']
            or not all(math.isfinite(audit[k]) and audit[k]>=0 for k in maxima)
            or audit[maxima[0]]>1e-6 or audit[maxima[1]]>1 or audit[maxima[3]]>8):raise ValueError('numerical/proposal audit invalid')
    if spp==8192 and [audit[k] for k in keys]!=[sum(r['audit'][k] for r in expected) for k in ('bvh_queries','component_attempts','component_nulls','own_checks')]:
        raise ValueError('independent original proposal counts differ')
    if [meta[k] for k in ('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')]!=rebuilt['counters'].sum(axis=0).tolist():raise ValueError('metadata scored counts differ')
    from readiness_preflight import replay
    ledger=read('allocation-ledger.json')
    if not replay(ledger):raise ValueError('owned peak/teardown replay failed')
    def err(a,b):return float(np.max(np.abs(a-b))) if np.isfinite(a).all() else None
    return dict(rows=rows,indirect_nrmse=nrmse,cpu_fallback_paths=fallback,total_paths=8*spp,cpu_fallback_fraction=fallback/(8*spp),
        routing_reason_counts=reasons,all_depth_parts_raw_corrected_stats_sidecar_bits_verified=True,
        independent_original_proposal_counts_verified=spp==8192,audit=audit,owned_memory_replay_pass=True,
        true_peak_owned_bytes=ledger['true_peak_owned_bytes'],max_depth_submit_wait_wall_diagnostic=max(walls),dispatch_count=len(dispatches),
        raw_gpu_diagnostic=dict(max_abs_mean=err(raw_stats['sum'][:,:,:3]/spp,cpu_means),max_abs_second=err(raw_stats['sum2'][:,:,:3]/spp,cpu_seconds),
            counter_disagreements=int(np.count_nonzero(raw_stats['counters']!=rebuilt['counters'])),nonfinite_values=int(np.count_nonzero(~np.isfinite(raw['values'])))))


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--probe',action='store_true');group.add_argument('--seed-index',type=int,choices=range(4));group.add_argument('--summarize',action='store_true');args=parser.parse_args()
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__).resolve(),PLAN,Path(H.__file__),Path(C.__file__),Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):
        D.checked(p)
    if args.summarize:
        output=D.RESULTS/'366-depth-split-hybrid-numerical.json'
        if output.exists():raise ValueError('refuse existing summary')
        prior(None);parts=[prior(i) for i in range(4)]
        output.write_text(json.dumps(dict(schema='n010-depth-split-hybrid-numerical/1',complete=True,all_pass=True,
            classification='DEPTH_SPLIT_SELECTED_C1_NUMERICAL_PASS_NO_ADMISSION',gpu_run=False,reference_admission=False,accepted_timing=False,
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,
            rows=[r for p in parts for r in p['validation']['rows']],parts=[str(location(i)[0]) for i in range(4)]),indent=2,allow_nan=False)+'\n');print('ALL32 DEPTH-SPLIT NUMERICAL PASS; NO ADMISSION');return
    index=None if args.probe else args.seed_index;output,work=location(index)
    if output.exists() or work.exists():raise ValueError('refuse existing part; no retry')
    if index is not None:
        prior(None)
        for i in range(index):prior(i)
    build=C.pinned_result('360');cpu=C.pinned_result('254');old_probe=H.prior(None);H.prior(3)
    if not build['all_pass'] or not cpu['all_pass']:raise ValueError('successful build/original CPU required')
    for p,h in build['input_sha256'].items():D.checked(Path(p),h)
    command=cpu['attempts'][1]['command'];scene,net=Path(command[2]),Path(command[1])
    D.checked(scene,cpu['input_sha256'][str(scene)]);D.checked(net,cpu['input_sha256'][str(net)])
    baseline=json.loads(D.checked(Path(command[4]),cpu['payload_sha256'][command[4]]))
    if [(r['x'],r['y'],r['seed']) for r in baseline]!=[(x,y,s) for x,y in H.PIXELS for s in D.SEEDS]:raise ValueError('original32 identities differ')
    probe_path=H.location(None)[1]/'cpu-probe.json';probe_rows=json.loads(D.checked(probe_path,old_probe['payload_sha256'][str(probe_path)]))
    original_meta=json.loads(D.checked(scene.parent/'n8192.meta.json'));original_hits=D.checked(scene.parent/'o.n8192.hits')
    if (original_meta['scene_sha256']!=C.sha(scene) or original_meta['seeds']!=list(D.SEEDS)
            or (original_meta['width'],original_meta['height'],original_meta['spp'])!=(320,180,8192)):raise ValueError('original metadata identity differs')
    for name in ('readiness_preflight.py','calibrate_renderer.py','reference_provenance.py'):D.checked(D.HERE.parent/'n010_comparison_readiness'/name)
    D.checked(D.ROOT/'scripts/run_with_vulkan.sh')
    seed=D.SEEDS[0 if index is None else index];spp,batch=(1,1) if index is None else (8192,16)
    expected=probe_rows if index is None else []
    if index is not None:
        for (x,y),p in zip(H.PIXELS,probe_rows):
            r=next(r for r in baseline if (r['x'],r['y'],r['seed'])==(x,y,seed))
            expected.append(dict(x=x,y=y,seed=seed,mean=r['mixture_mean'],second=r['mixture_second'],audit=r['audit'],
                counters=[spp,p['cache_shadow_tests']*spp+r['audit']['endpoint_shadow_tests'],p['cache_shadow_blocked']*spp+r['audit']['endpoint_shadow_blocked'],0]))
    work.mkdir(parents=True)
    result=dict(schema='n010-depth-split-hybrid-part/1',complete=False,all_pass=False,classification='DEPTH_SPLIT_NUMERICAL_ACQUIRING',
        seed_index=index,seed=seed,spp=spp,batch=batch,tile=8,selected_pixels=H.SELECTED,gpu_run=False,reference_admission=False,accepted_timing=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,attempts=[],
        tests='NOT_RUN; registered scientific numerical acquisition only',thresholds=dict(max_abs_mean_and_second=1e-10,indirect_nrmse=1e-8,counter_disagreements=0))
    def save():output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    if shutil.disk_usage(work).free<2*1024**3 or sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file())>=1024**3:
        raise ValueError('fixed retained-work/free-space guard; no native')
    cpu_limit,elapsed_limit=(60,90) if index is None else (360,600);receipt=work/'gpu.resources.json'
    command=['bash',str(D.ROOT/'scripts/run_with_vulkan.sh'),str(BUILD/'phos-n010-whole-full'),str(scene),str(net),str(BUILD/'full.spv'),str(seed),str(spp),str(batch),'8','diagnostic8','0','-',str(work/'gpu'),'1']
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(cpu_limit,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
    row=dict(command=command,resource_receipt=str(receipt),cpu_limit=cpu_limit,elapsed_limit=elapsed_limit,terminal=False);result['attempts'].append(row);result['gpu_run']=True;save()
    try:
        before=resource.getrusage(resource.RUSAGE_CHILDREN);started=time.monotonic()
        try:
            child=subprocess.run(command,capture_output=True,timeout=elapsed_limit,preexec_fn=limits);stdout,stderr=child.stdout,child.stderr;row.update(terminal=True,returncode=child.returncode)
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b'';row.update(terminal=True,returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',failure='ELAPSED_GUARD_NO_RETRY')
        after=resource.getrusage(resource.RUSAGE_CHILDREN);row.update(elapsed_seconds=time.monotonic()-started,child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        (work/'gpu.stdout').write_bytes(stdout);(work/'gpu.stderr').write_bytes(stderr);save();actual=json.loads(D.checked(receipt))
        if row['returncode']!=0 or actual['cpu']!=[cpu_limit]*2 or actual['address_space']!=[4*1024**3]*2 or actual['affinity']!=[31] or actual['nice']!=15:raise ValueError('native/resources failure; no retry')
        result['validation']=validate(work/'gpu',seed,spp,batch,expected,probe_rows,original_hits,build,scene,net,original_meta)
        if sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file())>1024**3:raise ValueError('retained-work cap exceeded')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(all_pass=True,classification='DEPTH_SPLIT_SELECTED_C1_NUMERICAL_PART_PASS_NO_ADMISSION')
    except (ValueError,OSError,KeyError,StopIteration,AssertionError,struct.error,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='DEPTH_SPLIT_NUMERICAL_FAILURE_RETAINED')
    result['complete']=True;result['payload_sha256']={str(p):C.sha(p) for p in work.rglob('*') if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure')}));raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':main()

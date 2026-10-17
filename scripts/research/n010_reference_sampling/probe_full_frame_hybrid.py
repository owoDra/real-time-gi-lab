#!/usr/bin/env python3
"""Plan114: one full-frame CPU/GPU conformance pilot step, never a queue."""
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
import acquire_depth_split_hybrid as K
import acquire_whole_path_hybrid as H
import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN=D.RESULTS.parent/'experiments/114-full-frame-one-sample-hybrid-pilot.md'
WORK=D.OUT/'full-frame-one-sample-hybrid-pilot-v1'
SEED=D.SEEDS[0]


def location(step):return D.RESULTS/f'{368 if step=="cpu" else 369}-full-frame-one-sample-{step}.json',WORK/step


def prior(step):
    path,_=location(step);data=json.loads(D.checked(path))
    if not (data['schema']=='n010-full-frame-one-sample-pilot/1' and data['complete'] and data['all_pass']
            and data['step']==step and data['seed']==SEED and data['spp']==1 and not data['reference_admission']):raise ValueError('exact prior full-frame pilot required')
    for key in ('input_sha256','payload_sha256'):
        for p,h in data[key].items():D.checked(Path(p),h)
    return data


def sidecar(path):
    raw=path.read_bytes()
    if raw[:8]!=b'N008F64\0' or struct.unpack_from('<IIIQ',raw,8)!=(320,180,1,SEED) or len(raw)!=28+57600*192:raise ValueError('full-frame sidecar identity differs')
    values=np.frombuffer(raw,dtype='<f8',offset=28).reshape(57600,2,4,3)
    if not np.isfinite(values).all() or np.any(values<0):raise ValueError('invalid full-frame values')
    return values


def check_pfms(prefix,values):
    for i,name in enumerate(('emission','direct','indirect','total')):
        raw=Path(str(prefix)+'.'+name+'.pfm').read_bytes();header=b'PF\n320 180\n-1\n'
        want=values[:,0,i].astype('<f4').reshape(180,320,3)[::-1].tobytes()
        if not np.isfinite(values[:,0,i].astype('<f4')).all() or raw!=header+want:raise ValueError('PFM/sidecar finite bits differ')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--step',required=True,choices=('cpu','gpu','summarize'));step=parser.parse_args().step
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15);resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__).resolve(),PLAN,Path(K.__file__),Path(H.__file__),Path(C.__file__),Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):D.checked(p)
    if step=='summarize':
        path=D.RESULTS/'370-full-frame-one-sample-hybrid-pilot.json'
        if path.exists():raise ValueError('refuse existing pilot summary')
        cpu,gpu=prior('cpu'),prior('gpu')
        path.write_text(json.dumps(dict(schema='n010-full-frame-one-sample-pilot-summary/1',complete=True,all_pass=True,
            classification='FULL_FRAME_ONE_SAMPLE_NUMERICAL_PASS_NO_REFERENCE_ADMISSION',gpu_run=False,reference_admission=False,accepted_timing=False,
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,
            cpu=cpu['attempts'],gpu=gpu['attempts'],validation=gpu['validation'],scope='Original C1 full320x180 one seed/one sample only; no full-count sizing or eligible reference.'),indent=2,allow_nan=False)+'\n');print('FULL-FRAME ONE-SAMPLE PASS; NO REFERENCE ADMISSION');return
    output,work=location(step)
    if output.exists() or work.exists():raise ValueError('refuse existing pilot part; no retry')
    summary=C.pinned_result('366');build=C.pinned_result('360');cpu_proof=C.pinned_result('254')
    if not all(p['all_pass'] for p in (summary,build,cpu_proof)) or len(summary['rows'])!=32:raise ValueError('successful all32/build/CPU prerequisites required')
    for proof in (summary,build):
        for p,h in proof['input_sha256'].items():D.checked(Path(p),h)
    command=cpu_proof['attempts'][1]['command'];scene,net=Path(command[2]),Path(command[1])
    D.checked(scene,cpu_proof['input_sha256'][str(scene)]);D.checked(net,cpu_proof['input_sha256'][str(net)])
    old_meta=json.loads(D.checked(scene.parent/'n8192.meta.json'));old_hits=D.checked(scene.parent/'o.n8192.hits')
    if old_meta['scene_sha256']!=C.sha(scene) or (old_meta['width'],old_meta['height'])!=(320,180):raise ValueError('original C1 identity differs')
    binary=D.OUT/'wide8-cpu-bvh-v1/n010_wide8_exporter';D.checked(binary,cpu_proof['payload_sha256'][str(binary)])
    for name in ('readiness_preflight.py','calibrate_renderer.py','reference_provenance.py'):D.checked(D.HERE.parent/'n010_comparison_readiness'/name)
    if step=='gpu':prior('cpu')
    D.checked(D.ROOT/'scripts/run_with_vulkan.sh');work.mkdir(parents=True)
    if shutil.disk_usage(work).free<2*1024**3:raise ValueError('free-space guard; no native')
    if step=='cpu':
        command=[str(binary),'--net',str(net),'--scene',str(scene),'--out',str(work/'o'),'--seeds',str(SEED),'--spp','1','--threads','1']
    else:
        command=['bash',str(D.ROOT/'scripts/run_with_vulkan.sh'),str(K.BUILD/'phos-n010-whole-full'),str(scene),str(net),str(K.BUILD/'full.spv'),str(SEED),'1','1','256','full','0','-',str(work/'gpu'),'1']
    result=dict(schema='n010-full-frame-one-sample-pilot/1',complete=False,all_pass=False,classification='FULL_FRAME_ONE_SAMPLE_ACQUIRING',
        step=step,seed=SEED,spp=1,width=320,height=180,gpu_run=step=='gpu',reference_admission=False,accepted_timing=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_sha256=D.INPUTS,attempts=[],
        tests='NOT_RUN; registered whole-frame scientific numerical/operational pilot')
    def save():output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    receipt=work/'native.resources.json'
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(300,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
    row=dict(command=command,resource_receipt=str(receipt),terminal=False,cpu_limit=300,elapsed_limit=420);result['attempts'].append(row);save()
    try:
        started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            child=subprocess.run(command,capture_output=True,timeout=420,preexec_fn=limits);stdout,stderr=child.stdout,child.stderr;row.update(terminal=True,returncode=child.returncode)
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b'';row.update(terminal=True,returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',failure='ELAPSED_GUARD_NO_RETRY')
        after=resource.getrusage(resource.RUSAGE_CHILDREN);row.update(elapsed_seconds=time.monotonic()-started,child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        (work/'native.stdout').write_bytes(stdout);(work/'native.stderr').write_bytes(stderr);save();actual=json.loads(D.checked(receipt))
        if row['returncode']!=0 or actual['cpu']!=[300]*2 or actual['address_space']!=[4*1024**3]*2 or actual['affinity']!=[31] or actual['nice']!=15:raise ValueError('native/resources failure; no retry')
        if step=='cpu':
            meta=json.loads(stdout);values=sidecar(work/'o.s0.f64')
            check_pfms(work/'o.s0',values)
            if (meta['scene_sha256']!=C.sha(scene) or meta['geometry_sha256']!=old_meta['geometry_sha256']
                    or (meta['width'],meta['height'],meta['spp'],meta['seeds'])!=(320,180,1,[SEED]) or len(meta['runs'])!=1
                    or meta['runs'][0]['seed']!=SEED or (work/'o.hits').read_bytes()!=old_hits):raise ValueError('independent CPU identity/hits differ')
            audit=meta['runs'][0]['all_split']
            if (audit['own_checks']!=audit['component_attempts']-audit['component_nulls']
                    or not all(math.isfinite(audit[k]) and audit[k]>=0 for k in ('max_own_log_error','max_conditioned_error_fraction','max_unconditioned_error_fraction'))
                    or audit['max_own_log_error']>1e-6 or audit['max_conditioned_error_fraction']>1):raise ValueError('CPU proposal/numerical audit failed')
            result['validation']=dict(all57600_pixels_finite_nonnegative=True,original_primary_hits_exact=True,counters={k:meta['runs'][0][k] for k in ('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')},audit=audit,
                mean_indirect=float(values[:,0,2].mean()),scope='Independent CPU one-sample full-frame baseline only')
        else:
            directory=work/'gpu';meta=json.loads((directory/'gpu.json').read_text());scope=json.loads((directory/'scope.json').read_text());values=sidecar(directory/'o.f64');cpu_values=sidecar(WORK/'cpu/o.s0.f64');cpu_meta=json.loads((WORK/'cpu/native.stdout').read_text())['runs'][0]
            check_pfms(directory/'o',values)
            if (meta['schema']!='n010-tiled-depth-split-whole-hybrid/1' or meta['mode']!='full' or meta['backend_id']!=build['backend_id']
                    or meta['scene_sha256']!=C.sha(scene) or meta['net_sha256']!=C.sha(net) or meta['geometry_sha256']!=old_meta['geometry_sha256']
                    or (meta['width'],meta['height'],meta['vertices'],meta['spp'],meta['seed'],meta['begin_spp'],meta['batch'],meta['tile_capacity'],meta['selected_count'])!=(320,180,8,1,SEED,0,1,256,57600)
                    or meta['fault_flags'] or not meta['all_finite'] or meta['reference_admission'] or meta['accepted_timing']
                    or scope['mode']!='full' or scope['selected_pixels']!=list(range(57600)) or scope['reference_admission']
                    or (directory/'o.hits').read_bytes()!=old_hits):raise ValueError('full-frame GPU identity/selection/hits differ')
            stats=np.fromfile(directory/'gpu.stats',dtype=H.STATS_DTYPE);counts=np.fromfile(directory/'sample-counts.bin',dtype='<u4')
            if len(stats)!=57600 or len(counts)!=57600 or not np.all(counts==1):raise ValueError('full-frame stats/sample counts differ')
            if values[:,0].tobytes()!=stats['sum'][:,:,:3].tobytes() or values[:,1].tobytes()!=stats['sum2'][:,:,:3].tobytes():raise ValueError('stats/sidecar bits differ')
            if values[:,:,:2].tobytes()!=cpu_values[:,:,:2].tobytes():raise ValueError('deterministic mean/moment bits differ')
            error=float(np.max(np.abs(values-cpu_values)));num=float(np.sum((values[:,0,2]-cpu_values[:,0,2])**2));den=float(np.sum(cpu_values[:,0,2]**2));nrmse=math.sqrt(num/den) if den else (0 if num==0 else None)
            if error>1e-10 or nrmse is None or nrmse>1e-8:raise ValueError('frozen full-frame numerical tolerance failed')
            keys=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
            if [meta[k] for k in keys]!=[cpu_meta[k] for k in keys] or [meta[k] for k in keys]!=stats['counters'].sum(axis=0).tolist():raise ValueError('full-frame independent scored counts differ')
            audit=meta['all_split'];auditkeys=('proposal_bvh_queries','component_attempts','component_nulls','own_checks');maxima=('max_own_log_error_bound','max_conditioned_error_fraction','max_unconditioned_error_fraction','max_weight')
            if [audit[k] for k in auditkeys]!=[cpu_meta['all_split'][k] for k in auditkeys] or (directory/'audit.bin').read_bytes()!=struct.pack('<4Q4d',*[audit[k] for k in auditkeys],*[audit[k] for k in maxima]):raise ValueError('full-frame proposal count/audit bits differ')
            if not all(math.isfinite(audit[k]) and audit[k]>=0 for k in maxima) or audit[maxima[0]]>1e-6 or audit[maxima[1]]>1 or audit[maxima[3]]>8:raise ValueError('full-frame numerical audit invalid')
            batches=[json.loads(line) for line in (directory/'batches.jsonl').read_text().splitlines()];dispatches=[json.loads(line) for line in (directory/'dispatches.jsonl').read_text().splitlines()]
            if len(batches)!=225 or len(dispatches)!=1575:raise ValueError('missing full-frame tile/depth')
            walls=[]
            for i,row in enumerate(batches):
                if (row['begin'],row['end'],row['tile_begin'],row['selected_count'],row['complete'])!=(0,1,256*i,256,True):raise ValueError('invalid full-frame tile')
                for depth,dispatch in enumerate(dispatches[i*7:i*7+7],1):
                    if (dispatch['begin'],dispatch['end'],dispatch['tile_begin'],dispatch['tile_count'],dispatch['depth'])!=(0,1,256*i,256,depth):raise ValueError('invalid full-frame dispatch')
                    wall=dispatch['submit_wait_wall_seconds_diagnostic'];walls.append(wall)
                    if not math.isfinite(wall) or not 0<=wall<=.250:raise ValueError('stopped full-frame dispatch')
                if row['max_depth_submit_wait_wall_seconds_diagnostic']!=max(walls[-7:]):raise ValueError('tile wall differs')
            if meta['cpu_fallback_paths_new_interval']!=sum(r['cpu_fallback_paths'] for r in batches) or meta['routing_reason_counts']!=[sum(r['reason_counts'][b] for r in batches) for b in range(6)] or meta['new_scored_paths']!=57600 or meta['max_depth_submit_wait_wall_seconds_diagnostic']!=max(walls):raise ValueError('full-frame routing/path annotations differ')
            from readiness_preflight import replay
            ledger=json.loads((directory/'allocation-ledger.json').read_text())
            if not replay(ledger):raise ValueError('owned allocation replay failed')
            result['validation']=dict(full_frame_pixel_count=57600,max_abs_mean_or_second_error=error,indirect_nrmse=nrmse,exact_primary_and_deterministic_bits=True,independent_scored_and_proposal_counts_exact=True,
                cpu_fallback_paths=meta['cpu_fallback_paths_new_interval'],routing_reason_counts=meta['routing_reason_counts'],dispatch_count=len(dispatches),max_depth_submit_wait_wall_diagnostic=max(walls),audit=audit,
                owned_peak_bytes=ledger['true_peak_owned_bytes'],owned_ledger_zero=True,scope='Whole-frame one-sample conformance and operational cost only; not full-count feasibility or GI timing')
        if sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file())>1024**3:raise ValueError('retained-work cap exceeded')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(all_pass=True,classification='FULL_FRAME_ONE_SAMPLE_PART_PASS_NO_ADMISSION')
    except (ValueError,OSError,KeyError,StopIteration,AssertionError,struct.error,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='FULL_FRAME_ONE_SAMPLE_FAILURE_RETAINED')
    result['complete']=True;result['payload_sha256']={str(p):C.sha(p) for p in work.rglob('*') if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure')}));raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':main()

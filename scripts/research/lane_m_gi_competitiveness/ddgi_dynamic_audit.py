#!/usr/bin/env python3
"""Read-only009 CPU audit: deterministic direct, finite atlases, reset/update identities."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import ddgi_dynamic_step as F
from audit_h01_evidence import memory
from audit_quality_step import archive_members,validate_inventory
from score_retained import reference
import score_hdr as S

R=F.R


def data_names(depth):
    return ['geometry-state.bin','frame-state.bin','constants-0.bin','constants-1.bin','pixels.f32','direct.pfm','indirect.pfm','total.pfm']+[
        f'stage-{k}-{role}-{j}.f32' for k in range(depth-1) for role,indices in [('current',range(4)),('previous',range(1,4))] for j in indices]


def same_frame(a,b,depth):
    for name in data_names(depth):R.require((a/name).read_bytes()==(b/name).read_bytes(),'frame byte identity failed: '+name)
    ca,cb=R.read(a/'configuration.json'),R.read(b/'configuration.json')
    ca.pop('setup_wall_us');cb.pop('setup_wall_us');R.require(ca==cb,'frame non-timing configuration differs')


def source_direct():
    ref=reference('H01',2);q=R.read(ref/'qualification.json');spp=q['levels'][-1]['spp']
    return np.mean([R.Q.L.read_sidecar(ref/f'o.n{spp}.s{k}.f64')['mean'] for k in range(4)],axis=0)[...,R.Q.L.COMPONENTS.index('direct'),:]@S.LUMA


def frame_report(path,state_path,depth,direct):
    for name in ('geometry-state.bin','frame-state.bin'):R.require((path/name).read_bytes()==(state_path/name).read_bytes(),'frame physical state differs')
    state=R.Q.L.read_state(state_path);cfg=R.read(path/'configuration.json')
    R.require((cfg['mode'],cfg['grid_side'],cfg['rays'],cfg['vertices'],cfg['seed'])==('scene',4,128,depth,305419896),'frame budget/mode mismatch')
    verts=state['verts'].reshape(-1,3);lo=verts.min(axis=0);hi=verts.max(axis=0);extent=hi-lo
    origin=((hi+lo)*.5).astype(np.float32);spacing=((extent+2*(extent/3))/3).astype(np.float32);bias=float(np.float32(.01)*spacing.min())
    R.require(cfg['origin']==origin.astype(float).tolist() and cfg['spacing']==spacing.astype(float).tolist() and cfg['normal_view_bias']==bias,'geometry-only origin/spacing/bias differs')
    R.require(cfg['hysteresis']==0 and cfg['gamma']==1 and cfg['brightness_threshold']==1e6 and cfg['distance_exponent']==50
        and cfg['rotation_updates_per_volume']==1 and cfg['ray_max']==float(state['camera_forward_far'][3]),'descriptor/encoding/history mismatch')
    R.require((path/'constants-0.bin').read_bytes()==(path/'constants-1.bin').read_bytes() and (path/'constants-0.bin').stat().st_size==128,'packed atlas descriptors differ')
    labels=['fresh-zero-initialize']
    for k in range(depth-1):
        p=f'stage-{k}';labels += [p+'-clear-destination',p+'-trace-0',p+'-trace-4096',p+'-sdk-blend']
        labels += ['readback-'+p+'-current-'+str(j) for j in range(4)]+['readback-'+p+'-previous-'+str(j) for j in range(1,4)]
    labels += ['primary-direct-gather'];events=[json.loads(x) for x in (path/'dispatches.jsonl').read_text().splitlines()]
    R.require(len(events)==2*len(labels),'incomplete/extra dynamic GPU units')
    for k,label in enumerate(labels):
        begin,end=events[2*k:2*k+2]
        R.require(begin=={'event':'begin','unit':label} and end['event']=='complete' and end['unit']==label
            and 0<=end['gpu_us_diagnostic']<=250000,'dynamic GPU order/guard/completion failed')
    pixels=np.fromfile(path/'pixels.f32',dtype='<f4').reshape(180,320,4)
    R.require(np.isfinite(pixels).all() and (pixels[...,3]==1).all(),'nonfinite/incomplete dynamic pixels')
    for j,c in enumerate(('direct','indirect','total')):R.require(np.array_equal(R.Q.L.read_pfm(path/(c+'.pfm')),np.repeat(pixels[...,j,None],3,axis=2)),'dynamic PFM/raw mismatch')
    R.require(np.array_equal(pixels[...,2],pixels[...,0]+pixels[...,1]),'dynamic composite differs')
    for k in range(depth-1):
        for role,indices in [('current',range(4)),('previous',range(1,4))]:
            for j in indices:
                p=path/f'stage-{k}-{role}-{j}.f32';layout=cfg['images'][j];a=np.fromfile(p,dtype='<f4')
                R.require(a.size==layout['w']*layout['h']*layout['layers']*layout['channels'] and np.isfinite(a).all(),'dynamic atlas shape/nonfinite')
                if role=='previous':
                    if k:R.require(p.read_bytes()==(path/f'stage-{k-1}-current-{j}.f32').read_bytes(),'preceding atlas mutated')
                    else:R.require((a==0).all(),'old history survived full frame reset')
    error=float(np.max(np.abs(pixels[...,0]-direct)));metrics=S.metrics(pixels[...,0],direct)
    R.require(error<=1e-5 and metrics['nrmse'] is not None and metrics['nrmse']<=1e-4,'dynamic primary/direct physical mismatch')
    return {'completed_gpu_units':len(labels),'finite_stages':depth-1,'previous_atlas_immutable':True,'initial_history_exactly_zero':True,
            'direct_max_abs_error':error,'direct_metrics':metrics,'configuration':cfg}


def audit(name):
    kind,mode,depth=F.split(name);plan_path,work,archive=F.paths(name);members=archive_members(archive)
    R.require(members['plan.json']==plan_path.read_bytes() and members['result.json']==(work/'result.json').read_bytes(),'dynamic compact proof differs')
    plan=json.loads(members['plan.json']);result=json.loads(members['result.json'])
    R.require(plan['name']==name and plan['command']==F.command(name) and result['name']==name and result['command']==plan['command'] and result['plan_sha256']==R.sha(plan_path)
        and result['semantic_admission'] is False and result['quality_admission'] is False and result['accepted_timing'] is False,'dynamic receipt scope differs')
    validate_inventory(work,result['payload_sha256']);R.require(R.read(work/'started.json')=={'plan_sha256':R.sha(plan_path),'plan':plan},'dynamic started identity differs')
    if not result['complete']:
        R.require(result['classification']=='OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY','dynamic partial falsely accepted')
        return {'name':name,'classification':'OPERATIONAL_FAILURE_RETAINED','semantic_pass':False,'result_sha256':R.sha(work/'result.json'),
            'raw_payloads_rehashed':len(result['payload_sha256']),'error':result.get('error'),'gpu_executed_by_auditor':False,'accepted_timing':False}
    R.require(result['returncode']==0 and result['gpu_executed'] is True,'native dynamic process incomplete')
    R.preflight('H01',2);F.D.audit_states();F.D.audit_oracle(kind)
    for p,h in plan['input_sha256'].items():R.require(R.sha(Path(p))==h,'planned dynamic input drift: '+p)
    commit=plan['source_commit'];R.require(subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=R.ROOT,capture_output=True).returncode==0,'unreachable dynamic source')
    for p in (Path(__file__).resolve(),Path(F.__file__).resolve(),F.PROTOCOL):
        R.require(hashlib.sha256(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)).hexdigest()==plan['input_sha256'][str(p)],'dynamic source not committed')
    capture=work/'capture';allocation=memory(R.read(capture/'allocation-ledger.json'))
    target_state=F.D.WORK/kind;target_direct=R.Q.L.read_sidecar(target_state/'cpu-direct-v1/oracle.s0.f64')['mean'][...,R.Q.L.COMPONENTS.index('direct'),:]@S.LUMA
    frames=[];source=R.LANE/'capture/M001-H01-hwrt'
    if mode=='fresh':frames.append(frame_report(capture,target_state,depth,target_direct))
    else:
        contract=R.read(capture/'transition-contract.json');sequence=[json.loads(x) for x in (capture/'sequence.jsonl').read_text().splitlines()]
        n=1224 if kind=='geometry' else 0
        expected=[{'index':k,'state_index':s,'moved_primitives':m,'reset_both_atlases':True,'finite_stages':depth-1} for k,(s,m) in enumerate(zip((0,1,1,0),(0,n,0,n)))]
        R.require(contract['history_policy']=='reset-all' and contract['frames']==expected and len(sequence)==4,'native dynamic schedule differs')
        fresh=F.paths(f'{kind}-fresh-b{depth}')[1]/'capture';original=F.S.paths('scene-one' if depth==2 else 'scene-seven')[1]/'capture'
        original_direct=source_direct()
        for k in range(4):
            frame=capture/f'frames/{k}';target=k in (1,2);frames.append(frame_report(frame,target_state if target else source,depth,target_direct if target else original_direct))
            row=sequence[k];R.require(row['frame']==k and row['state_index']==expected[k]['state_index'] and row['reset_both_atlases'] is True and row['moved_primitives']==expected[k]['moved_primitives'],'native changed-range/reset mismatch')
            times=('geometry_upload_gpu_us_diagnostic','geometry_upload_wall_us','blas_update_wall_us','tlas_update_wall_us')
            R.require(all(np.isfinite(row[key]) and row[key]>=0 for key in times+('frame_setup_update_wall_us','frame_complete_wall_us')),'invalid update cost diagnostics')
            R.require(all(row[key]>0 if expected[k]['moved_primitives'] else row[key]==0 for key in times),'missing/extra actual AS update diagnostics')
            same_frame(frame,fresh if target else original,depth)
        same_frame(capture/'frames/0',capture/'frames/3',depth)
        R.require(any((capture/'frames/0'/file).read_bytes()!=(capture/'frames/1'/file).read_bytes() for file in ('direct.pfm','stage-0-current-0.f32')),'changed-state experiment is vacuous')
        ledger=R.read(capture/'allocation-ledger.json');image_events=[x for x in ledger['events'] if x['buffer_usage']==15]
        R.require(len(image_events)==24 and sum(x['action']=='allocate' for x in image_events)==12
            and all(x['phase']=='startup' if x['action']=='allocate' else x['phase']=='primary-direct-gather' for x in image_events),'atlas allocation lifecycle differs; not persistent/reset-only')
    return {'schema':'m001-ddgi-dynamic-independent-cpu-audit/1','name':name,'classification':'DYNAMIC_RESET_CONTROL_PASS','semantic_pass':True,
        'result_sha256':R.sha(work/'result.json'),'archive_sha256':R.sha(archive),'raw_payloads_rehashed':len(result['payload_sha256']),
        'frames':frames,'owned_memory':allocation,'persistent_atlas_reset_policy':'reset-all' if mode=='transition' else 'fresh',
        'fresh_target_byte_identity_verified':mode=='transition','source_return_byte_identity_verified':mode=='transition',
        'gpu_executed_by_auditor':False,'quality_admission':False,'accepted_timing':False,'temporal_accumulation_supported':False}

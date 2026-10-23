#!/usr/bin/env python3
"""Independent read-only CPU admission of a single DDGI semantic control."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import ddgi_control_step as F
from audit_quality_step import archive_members,validate_inventory
from audit_h01_evidence import memory
import score_hdr as S
from score_retained import reference

R=F.R


def audit(name):
    plan_path,work,archive=F.paths(name)
    members=archive_members(archive)
    R.require(members['plan.json']==plan_path.read_bytes() and members['result.json']==(work/'result.json').read_bytes(),'control proof identity differs')
    plan=json.loads(members['plan.json']);result=json.loads(members['result.json'])
    R.require(plan['name']==name and plan['command']==F.command(name) and result['name']==name and result['command']==plan['command']
        and result['plan_sha256']==R.sha(plan_path) and result['accepted_timing'] is False and result['semantic_admission'] is False
        and result['quality_admission'] is False,'control receipt scope changed')
    validate_inventory(work,result['payload_sha256'])
    R.require(R.read(work/'started.json')=={'plan_sha256':R.sha(plan_path),'plan':plan},'started identity differs')
    if not result['complete']:
        R.require(result['classification']=='OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY','failed control misclassified')
        return {'name':name,'classification':'OPERATIONAL_FAILURE_RETAINED','semantic_pass':False,'result_sha256':R.sha(work/'result.json'),
            'error':result.get('error'),'raw_payloads_rehashed':len(result['payload_sha256']),'gpu_executed_by_auditor':False,'accepted_timing':False}
    R.require(result['returncode']==0 and result['gpu_executed'] is True,'successful native process missing')
    R.preflight('H01',2)
    for p,h in plan['input_sha256'].items():R.require(R.sha(Path(p))==h,'planned input drift: '+p)
    source=plan['source_commit']
    R.require(subprocess.run(['git','merge-base','--is-ancestor',source,'HEAD'],cwd=R.ROOT,capture_output=True).returncode==0,'unreachable source')
    for p in (Path(__file__).resolve(),Path(F.__file__).resolve(),F.PROTOCOL):
        R.require(hashlib.sha256(subprocess.check_output(['git','show',source+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)).hexdigest()==plan['input_sha256'][str(p)],'uncommitted control source')
    capture=work/'capture';source_state=R.LANE/'capture/M001-H01-hwrt'
    for filename in ('geometry-state.bin','frame-state.bin'):R.require((capture/filename).read_bytes()==(source_state/filename).read_bytes(),'physical state drift')
    cfg=R.read(capture/'configuration.json');depth=1 if name=='direct' else 8 if name=='scene-seven' else 2
    expected_mode={'direct':'direct','black':'constant0','unit':'constant1','hdr':'constant8','scene-one':'scene','scene-seven':'scene'}[name]
    R.require((cfg['mode'],cfg['grid_side'],cfg['rays'],cfg['vertices'],cfg['seed'])==(expected_mode,4,128,depth,305419896),'native budget/mode mismatch')
    R.require(cfg['hysteresis']==0 and cfg['gamma']==1 and cfg['rotation_updates_per_volume']==1 and cfg['brightness_threshold']==1e6,'native encoding/history mismatch')
    R.require((capture/'constants-0.bin').read_bytes()==(capture/'constants-1.bin').read_bytes(),'grid/rotation descriptor differs across atlases')
    allocation=memory(R.read(capture/'allocation-ledger.json'))
    events=[json.loads(line) for line in (capture/'dispatches.jsonl').read_text().splitlines()]
    expected_units=['fresh-zero-initialize']
    for k in range(depth-1):
        prefix=f'stage-{k}';expected_units+=[prefix+'-clear-destination']
        expected_units += [prefix+'-trace-0',prefix+'-trace-4096'] if expected_mode=='scene' else [prefix+'-constant-ray-data']
        expected_units += [prefix+'-sdk-blend']+['readback-'+prefix+'-current-'+str(j) for j in range(4)]+['readback-'+prefix+'-previous-'+str(j) for j in range(1,4)]
    expected_units+=['primary-direct-gather']
    R.require(len(events)==2*len(expected_units),'missing/extra/incomplete GPU unit')
    for k,label in enumerate(expected_units):
        a,z=events[2*k:2*k+2]
        R.require(a=={'event':'begin','unit':label} and z['event']=='complete' and z['unit']==label and 0<=z['gpu_us_diagnostic']<=250000,'GPU unit failed/reordered/guard exceeded')
    pixels=np.fromfile(capture/'pixels.f32',dtype='<f4').reshape(180,320,4)
    R.require(np.isfinite(pixels).all() and (pixels[...,3]==1).all(),'nonfinite/incomplete pixels')
    for channel,component in enumerate(('direct','indirect','total')):
        image=R.Q.L.read_pfm(capture/(component+'.pfm'))
        R.require(np.array_equal(image,np.repeat(pixels[...,channel,None],3,axis=2)),'PFM/raw component mismatch')
    R.require(np.array_equal(pixels[...,2],pixels[...,0]+pixels[...,1]),'linear composite identity failed')
    detail={'completed_gpu_units':len(expected_units),'stage_count':depth-1,'previous_atlas_bytes_immutable':True}
    for k in range(depth-1):
        for kind in ('current','previous'):
            indices=range(4) if kind=='current' else range(1,4)
            for j in indices:
                p=capture/f'stage-{k}-{kind}-{j}.f32';layout=cfg['images'][j]
                data=np.fromfile(p,dtype='<f4');R.require(data.size==layout['w']*layout['h']*layout['layers']*layout['channels'] and np.isfinite(data).all(),'atlas shape/nonfinite')
                if kind=='previous':
                    if k:R.require(p.read_bytes()==(capture/f'stage-{k-1}-current-{j}.f32').read_bytes(),'previous stage atlas changed during production/blending')
                    else:R.require((data==0).all(),'stage0 did not start from black previous atlas')
        if name in ('black','unit','hdr'):
            radiance={'black':0,'unit':1,'hdr':8}[name]
            for j,expected in ((0,radiance),(1,radiance*.5),(2,.5)):
                channels=cfg['images'][j]['channels'];a=np.fromfile(capture/f'stage-{k}-current-{j}.f32',dtype='<f4').reshape(-1,channels)
                checked=a[:,:3] if j<2 else a
                error=float(np.max(np.abs(checked-expected)));R.require(error<=1e-5,'constant ray/blend normalization or HDR clamp failure')
                detail[f'type{j}_max_abs_error']=error
    if name=='direct':
        ref=reference('H01',2);q=R.read(ref/'qualification.json');spp=q['levels'][-1]['spp']
        means=np.mean([R.Q.L.read_sidecar(ref/f'o.n{spp}.s{k}.f64')['mean'] for k in range(4)],axis=0)
        original=means[...,R.Q.L.COMPONENTS.index('direct'),:]@S.LUMA
        direct=pixels[...,0];error=float(np.max(np.abs(direct-original)));metrics=S.metrics(direct,original)
        R.require(error<=1e-5 and metrics['nrmse'] is not None and metrics['nrmse']<=1e-4 and (pixels[...,1]==0).all(),'primary/direct physical oracle mismatch')
        detail.update(direct_max_abs_error=error,direct_metrics=metrics)
    else:
        baseline=F.paths('direct')[1]/'capture';R.require((capture/'direct.pfm').read_bytes()==(baseline/'direct.pfm').read_bytes(),'probe path changed primary/direct')
    if name=='black':R.require((pixels[...,1]==0).all(),'black field leaked indirect light')
    if name=='hdr':
        unit=np.fromfile(F.paths('unit')[1]/'capture/pixels.f32',dtype='<f4').reshape(180,320,4)
        R.require(np.max(unit[...,1])>0 and np.allclose(pixels[...,1],8*unit[...,1],rtol=1e-5,atol=2e-6),'HDR surface gather failed 8x linearity')
        detail['hdr_surface_gather_8x_linearity']=True
    if name=='scene-seven':
        one=F.paths('scene-one')[1]/'capture'
        for j in range(4):R.require((capture/f'stage-0-current-{j}.f32').read_bytes()==(one/f'stage-0-current-{j}.f32').read_bytes(),'B8 first-stage differs from B2 first-stage')
        detail['one_and_seven_stage_prefix_byte_identical']=True
    return {'schema':'m001-ddgi-control-independent-cpu-audit/1','name':name,'classification':'SEMANTIC_CONTROL_PASS','semantic_pass':True,
        'result_sha256':R.sha(work/'result.json'),'archive_sha256':R.sha(archive),'raw_payloads_rehashed':len(result['payload_sha256']),
        'detail':detail,'owned_memory':allocation,'gpu_executed_by_auditor':False,'quality_admission':False,'accepted_timing':False,
        'scope':'Named static semantic control only; no HDR quality decision, temporal/dynamic support, robustness or speed claim'}

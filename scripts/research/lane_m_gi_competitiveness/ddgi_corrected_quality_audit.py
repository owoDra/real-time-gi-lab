#!/usr/bin/env python3
"""Independent012 corrected-copy and whole-image CPU quality audit; no GPU launcher."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
import ddgi_corrected_quality_step as F
import ddgi_border_requalification_audit as Border
import ddgi_border_copy_check as Copy
from types import SimpleNamespace
from audit_h01_evidence import memory
from audit_quality_step import archive_members,validate_inventory,quality_pass as original_quality_pass
from score_retained import reference
import score_hdr as S

R=F.R
SCORES=F.ROOT.with_name('m001-ddgi-border-quality-scores-v1')


def layouts(side,rays):
    dims=[(rays,side*side,side,4),(8*side,8*side,side,4),(16*side,16*side,side,2),
          (side,side,side,4),(6*side,6*side,side,1),((6*side+15)//16,(6*side+15)//16,(side+3)//4,2)]
    return [dict(type=j,w=w,h=h,layers=n,channels=c) for j,(w,h,n,c) in enumerate(dims)]


def quality_pass(components):
    values=[components['total']['nrmse'],components['indirect']['nrmse'],components['indirect']['signed_sum_bias']]
    return (all(v is not None and np.isfinite(v) for v in values)
            and values[0]>=0 and values[1]>=0 and original_quality_pass(components))


def classify(components):
    values=[components['total']['nrmse'],components['indirect']['nrmse'],components['indirect']['signed_sum_bias']]
    R.require(all(v is not None and np.isfinite(v) for v in values)
              and values[0]>=0 and values[1]>=0,'012 undefined/nonfinite quality gate is invalid evidence, not QUALITY_FAIL')
    return 'PASS' if quality_pass(components) else 'QUALITY_FAIL'


def unit_labels(side,rays,depth):
    return Border.unit_labels(SimpleNamespace(side=side,rays=rays,depth=depth,mode='scene'))


def check_units(events,labels):
    R.require(len(events)==2*len(labels),'incomplete/extra012 GPU units/coverage')
    times=[]
    for k,label in enumerate(labels):
        begin,end=events[2*k:2*k+2]
        R.require(begin=={'event':'begin','unit':label} and end['event']=='complete' and end['unit']==label
            and np.isfinite(end['gpu_us_diagnostic']) and 0<=end['gpu_us_diagnostic']<=250000,'012 tile order/completion/guard failed')
        times.append(end['gpu_us_diagnostic'])
    return {'completed_gpu_units':len(labels),'sum_gpu_us_diagnostic':float(sum(times)),'max_unit_gpu_us_diagnostic':float(max(times)),
            'classification':'DIAGNOSTIC_UNCALIBRATED_NO_SPEED_CLAIM'}


def native_report(case):
    path=case.work/'capture';side,rays=case.budget;state_path=R.LANE/f'capture/M001-{case.cell}-hwrt'
    for n in ('geometry-state.bin','frame-state.bin'):R.require((path/n).read_bytes()==(state_path/n).read_bytes(),'012 physical state mismatch')
    state=R.Q.L.read_state(path);R.require(state['sha256']==R.CAPTURE_SHA[case.cell],'012 full state hash differs')
    R.require(hashlib.sha256(R.Q.scene_for_state(state,case.depth).text().encode()).hexdigest()==R.CORRECTED_SHA[case.cell][case.depth],'012 complete physical scene mismatch')
    cfg=R.read(path/'configuration.json')
    R.require((cfg['mode'],cfg['grid_side'],cfg['rays'],cfg['vertices'],cfg['seed'])==('scene',side,rays,case.depth,305419896),'012 native budget/mode differs')
    verts=state['verts'].reshape(-1,3);lo=verts.min(axis=0);hi=verts.max(axis=0);extent=hi-lo
    origin=((hi+lo)*.5).astype(np.float32);spacing=((extent+2*(extent/(side-1)))/(side-1)).astype(np.float32)
    bias=float(np.float32(.01)*spacing.min())
    R.require(cfg['origin']==origin.astype(float).tolist() and cfg['spacing']==spacing.astype(float).tolist() and cfg['normal_view_bias']==bias,'012 geometry-only grid/bias mismatch')
    R.require(cfg['hysteresis']==0 and cfg['gamma']==1 and cfg['brightness_threshold']==1e6 and cfg['distance_exponent']==50
        and cfg['rotation_updates_per_volume']==1 and cfg['ray_max']==float(state['camera_forward_far'][3]),'012 encoding/history descriptor mismatch')
    R.require(cfg['images']==layouts(side,rays),'012 official SDK image dimensions/channels differ')
    b=(path/'constants-0.bin').read_bytes();R.require(len(b)==128 and b==(path/'constants-1.bin').read_bytes(),'012 atlas constants differ')
    f=np.frombuffer(b,dtype='<f4');p0,p1,p2,p3,p4=struct.unpack_from('<5I',b,92)
    R.require(np.array_equal(f[:3],origin) and f[3]==0 and np.array_equal(f[20:23],spacing)
        and tuple(map(float,f[12:19]))==(cfg['ray_max'],bias,bias,50.,1.,1e6,1e6),'012 packed floating descriptor differs')
    baseline=(F.B.S.paths('scene-one')[1]/'capture/constants-0.bin').read_bytes()
    R.require(b[16:48]==baseline[16:48] and p0==(side|(side<<10)|(side<<20)) and p2==(rays|(6<<16)|(14<<24))
        and p3==0 and p4==struct.unpack_from('<I',baseline,108)[0],'012 rotation/count/format/feature flags differ')
    contract=R.read(path/'cpu-contract.json');R.require(contract==R.read(Path(R.read(case.plan)['native_cpu_contract']['path']))['contract'],'012 actual CPU shape differs from prepared native check')
    complete=R.read(path/'complete.json');R.require(complete['capture_complete'] is True and complete['semantic_admission'] is False and complete['quality_admission'] is False and complete['speed_admission'] is False,'012 native claims inappropriate admission')
    labels=unit_labels(side,rays,case.depth);events=[json.loads(x) for x in (path/'dispatches.jsonl').read_text().splitlines()]
    units=check_units(events,labels)
    pixels=np.fromfile(path/'pixels.f32',dtype='<f4').reshape(180,320,4)
    R.require(np.isfinite(pixels).all() and (pixels[...,3]==1).all(),'012 nonfinite/incomplete pixels')
    for j,c in enumerate(('direct','indirect','total')):R.require(np.array_equal(R.Q.L.read_pfm(path/(c+'.pfm')),np.repeat(pixels[...,j,None],3,axis=2)),'012 raw/PFM mismatch')
    R.require(np.array_equal(pixels[...,2],pixels[...,0]+pixels[...,1]),'012 linear composite mismatch')
    for k in range(case.depth-1):
        for role,indices in [('current',range(4)),('previous',range(1,4))]:
            for j in indices:
                p=path/f'stage-{k}-{role}-{j}.f32';layout=cfg['images'][j];a=np.fromfile(p,dtype='<f4')
                R.require(a.size==layout['w']*layout['h']*layout['layers']*layout['channels'] and np.isfinite(a).all(),'012 nonfinite/incorrect atlas')
                if role=='previous':
                    if k:R.require(R.sha(p)==R.sha(path/f'stage-{k-1}-current-{j}.f32'),'012 previous stage atlas mutated')
                    else:R.require((a.view('<u4')==0).all(),'012 initial history not exactly +0')
    copies=[]
    for k in range(case.depth-1):
        for j,tile in ((1,8),(2,16)):
            before=Border.atlas(path/f'stage-{k}-pre-border-{j}.f32',cfg['images'][j])
            after=Border.atlas(path/f'stage-{k}-current-{j}.f32',cfg['images'][j])
            copies.append(dict(stage=k,type=j,**Copy.check_copy(before,after,tile,side)))
        metadata=Border.atlas(path/f'stage-{k}-current-3.f32',cfg['images'][3])
        R.require((metadata==0).all(),'012 disabled probe metadata changed')
    ledger=R.read(path/'allocation-ledger.json');allocation=memory(ledger)
    images=[x for x in ledger['events'] if x['action']=='allocate' and x['buffer_usage']==15]
    R.require(len(images)==12 and all(x['phase']=='startup' for x in images),'012 missing persistent pair of six SDK images')
    R.require(all(images[j]['bytes']>=d['w']*d['h']*d['layers']*d['channels']*4 for j,d in enumerate(cfg['images']*2)),
        '012 image allocation smaller than exact SDK format/extent')
    return {'configuration':cfg,'timing':units,'owned_memory':allocation,'full_physical_state_verified':True,
        'previous_atlas_immutable':True,'initial_history_exactly_zero':True,'full_disjoint_ray_tile_coverage':True,
        'copies':copies,'full_copy_exact':True,'interior_unchanged':True}


def audit(case,save=False):
    members=archive_members(case.archive);R.require(members['plan.json']==case.plan.read_bytes() and members['result.json']==(case.work/'result.json').read_bytes(),'012 compact proof identity mismatch')
    plan=json.loads(members['plan.json']);result=json.loads(members['result.json'])
    R.require(plan['scope']==case.scope and plan['command']==F.command(case) and result['scope']==case.scope and result['command']==plan['command']
        and result['schema']=='m001-ddgi-corrected-quality-result/1'
        and result['plan_sha256']==R.sha(case.plan) and result['quality_admission'] is False and result['accepted_timing'] is False,'012 receipt scope differs')
    validate_inventory(case.work,result['payload_sha256'])
    R.require(R.read(case.work/'started.json')=={'plan_sha256':R.sha(case.plan),'plan':plan},'012 started identity mismatch')
    if not result['complete']:
        R.require(result['classification']=='OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY','012 partial falsely classified')
        return {'name':case.name,'classification':'OPERATIONAL_FAILURE_RETAINED','quality_evidence_valid':False,'result_sha256':R.sha(case.work/'result.json'),
            'raw_payloads_rehashed':len(result['payload_sha256']),'error':result.get('error'),'gpu_executed_by_auditor':False,'accepted_timing':False}
    R.require(result['returncode']==0 and result['gpu_executed'] is True and result['classification']=='RAW_QUALITY_CAPTURE_RETAINED_AUDIT_REQUIRED','012 native incomplete/falsely scored')
    R.require(plan['schema']=='m001-ddgi-corrected-quality-plan/1' and plan['unblinded_cohort'] is True
        and plan['gpu_executed'] is False and plan['accepted_timing'] is False,'012 source plan scope differs')
    for p,h in plan['input_sha256'].items():R.require(R.sha(Path(p))==h,'012 planned input drift: '+p)
    commit=plan['source_commit'];R.require(subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=R.ROOT,capture_output=True).returncode==0,'012 unreachable source')
    for p in F.source_paths():
        R.require(hashlib.sha256(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)).hexdigest()==plan['input_sha256'][str(p)],'012 source not committed')
    R.require(F.requalification({})==plan['requalification'],'012 full011qualification identity differs')
    refs=F.verify_references({});R.require(refs==plan['reference_verification'],'012 reference admission/provenance differs')
    native=native_report(case);ref=reference(case.cell,case.depth);q=R.read(ref/'qualification.json');R.require(q['levels'][-1]['spp']==16384,'012 reference level differs')
    means=np.mean([R.Q.L.read_sidecar(ref/f'o.n16384.s{k}.f64')['mean'] for k in range(4)],axis=0)
    components={};errors={}
    for component in ('direct','indirect','total'):
        g=R.Q.L.read_pfm(case.work/f'capture/{component}.pfm')@S.LUMA;r=means[...,R.Q.L.COMPONENTS.index(component),:]@S.LUMA
        components[component]=S.metrics(g,r);errors[component]=g-r
    # Physical primary path must remain correct independently of indirect quality.
    R.require(components['direct']['nrmse'] is not None and components['direct']['nrmse']<=1e-4
        and components['direct']['whole_image_max_absolute']<=1e-5,'012 primary/direct physical oracle mismatch')
    report={'schema':'m001-ddgi-corrected-quality-independent-cpu-audit/1','name':case.name,'scope':case.scope,
        'classification':classify(components),'quality_evidence_valid':True,
        'result_sha256':R.sha(case.work/'result.json'),'archive_sha256':R.sha(case.archive),'raw_payloads_rehashed':len(result['payload_sha256']),
        'reference_verification':refs[f'{case.cell}_T_B{case.depth}'],'components':components,'native':native,
        'unblinded_cohort':True,'scoring_exclusions':0,'gpu_executed_by_auditor':False,'accepted_timing':False,'superiority_claim':False}
    derived=SCORES/case.name
    if save:
        R.require(not derived.exists(),'existing012 CPU score; replay audit without --save, never overwrite')
        derived.mkdir(parents=True)
        for c,e in errors.items():np.save(derived/f'{c}.error.npy',e)
        report['payload_sha256']={p.name:R.sha(p) for p in sorted(derived.iterdir())};R.write_new(derived/'result.json',report)
    else:
        stored=R.read(derived/'result.json');validate_inventory(derived,stored['payload_sha256'])
        R.require({k:v for k,v in stored.items() if k!='payload_sha256'}==report,'012 independent metric/native/memory replay differs')
        for c,e in errors.items():R.require(np.array_equal(np.load(derived/f'{c}.error.npy',allow_pickle=False),e),'012 full error map differs')
        report=stored
    return dict(report,derived_record_sha256=R.sha(derived/'result.json'))

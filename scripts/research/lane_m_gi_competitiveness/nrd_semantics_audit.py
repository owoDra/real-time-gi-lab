#!/usr/bin/env python3
"""027: reflect saved SDK constants and independently check guide semantics."""
import argparse
import hashlib
import json
import resource
import struct
import subprocess
import sys
from pathlib import Path
import numpy as np
import nrd_quality_build as B
import nrd_quality_process as P
import nrd_source_contract as S
import closest_primary_metrics as M

ROOT=B.ROOT;BASE=B.BASE
LANE=ROOT/'research/lanes/lane-m-gi-competitiveness'
PROTOCOL=LANE/'experiments/027-nrd-saved-input-semantic-audit.md'
OWN=[Path(__file__).resolve(),Path(__file__).with_name('test_nrd_semantics.py'),PROTOCOL]
BASE_COMMIT='209af1d5bec7a88588719e096140b8279d45208b'
SOURCE_NAMES=['README.md','Include/NRDDescs.h','Include/NRDSettings.h','Shaders/NRD.hlsli','Shaders/RELAX_Config.hlsli','Shaders/RELAX_Common.hlsli','Source/Relax.cpp','Source/InstanceImpl.cpp']
GEOMETRY=['gWorldToClip','gWorldToClipPrev','gFrustumRight','gFrustumUp','gFrustumForward','gPrevFrustumRight','gPrevFrustumUp','gPrevFrustumForward','gRectSizeInv','gRectSize','gResourceSize','gInputRectOrigin','gOutputRectOrigin','gDispatchInputRectOrigin','gDispatchOutputRectOrigin','gCameraDelta','gMvBias','gJitter','gOrthoMode','gDenoisingRange','gViewZScale']
DEFAULTS={'gDiffBlurRadius':30.,'gDiffPhiLuminance':2.,'gHistoryFixFrameNum':4.,'gHistoryFixBasePixelStride':14.,'gHistoryFixAlternatePixelStride':14.,'gHistoryThreshold':3.,'gMinHitDistanceWeight':float(np.float32(.1)*np.float32(2)),'gLuminanceEdgeStoppingRelaxation':1.}
REQUIRED=GEOMETRY+list(DEFAULTS)+['gDiffMaxAccumulatedFrameNum','gDiffMaxFastAccumulatedFrameNum']

def need(value,message):
    if not value:raise ValueError(message)

def committed():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'Commit027 code/protocol before execution')
    subprocess.run(['git','merge-base','--is-ancestor',BASE_COMMIT,head],cwd=ROOT,check=True)
    return head

def reflect(raw,shared=True):
    """Read real typed constant descriptors and member layout decorations."""
    need(len(raw)>=20 and len(raw)%4==0,'SPIR-V size')
    w=struct.unpack('<'+'I'*(len(raw)//4),raw);need(w[0]==0x07230203,'SPIR-V magic')
    names={};member_names={};decs={};member_decs={};types={};variables={};constants={};definitions={};matrix_ops=[];at=5
    while at<len(w):
        count=w[at]>>16;op=w[at]&65535;need(count>0 and at+count<=len(w),'SPIR-V instruction range');a=w[at+1:at+count]
        def string(words):return struct.pack('<'+'I'*len(words),*words).split(b'\0')[0].decode('utf8')
        if op==5:names[a[0]]=string(a[1:])
        elif op==6:member_names[(a[0],a[1])]=string(a[2:])
        elif op==71:decs.setdefault(a[0],{})[a[1]]=list(a[2:])
        elif op==72:member_decs.setdefault((a[0],a[1]),{})[a[2]]=list(a[3:])
        elif op in (20,21,22,23,24,30,32):types[a[0]]=(op,list(a[1:]))
        elif op==59:variables[a[1]]=(a[0],a[2])
        elif op==43 and len(a)==3:constants[a[1]]=a[2]
        elif op in (61,65,83,84):definitions[a[1]]=(op,list(a[2:]))
        elif op in (144,145):matrix_ops.append((op,list(a)))
        at+=count
    candidates=[k for k in variables if decs.get(k,{}).get(34)==[1] and decs.get(k,{}).get(33)==[2]]
    need(len(candidates)==1,'one set1/binding2 constant descriptor')
    pointer,storage=variables[candidates[0]];need(storage==2 and types[pointer][0]==32 and types[pointer][1][0]==2,'uniform constant pointer')
    root=types[pointer][1][1];need(types[root][0]==30 and 2 in decs.get(root,{}),'constant block structure')
    def describe(t):
        op,a=types[t]
        if op==22:need(a==[32],'float32 constants');return dict(kind='float',count=1,bytes=4)
        if op==21:need(a[0]==32,'int32 constants');return dict(kind='int' if a[1] else 'uint',count=1,bytes=4)
        if op==23:
            s=describe(a[0]);need(s['count']==1,'scalar vector base');return dict(kind=s['kind'],count=a[1],bytes=4*a[1])
        if op==24:
            v=describe(a[0]);need(v['kind']=='float' and v['count']==a[1]==4,'float4x4 constants');return dict(kind='matrix',count=16,bytes=64)
        raise ValueError('unsupported constant type '+str(op))
    fields={}
    for i,t in enumerate(types[root][1]):
        key=(root,i);name=member_names.get(key);need(name is not None and name not in fields,'unique named constant members')
        d=member_decs.get(key,{});need(35 in d and len(d[35])==1,'member byte offset')
        spec=describe(t);spec['offset']=d[35][0]
        if spec['kind']=='matrix':
            need(d.get(7)==[16] and ((4 in d) != (5 in d)),'matrix stride/major decoration')
            spec['major']='row' if 4 in d else 'column'
        fields[name]=spec
    if shared:need(set(REQUIRED)<=set(fields),'RELAX common member coverage')
    def matrix_origin(identifier,transposed=False):
        op,a=definitions.get(identifier,(None,[]))
        if op==84:return matrix_origin(a[0],not transposed)
        if op==83:return matrix_origin(a[0],transposed)
        if op==61:
            pointer_op,pointer_a=definitions.get(a[0],(None,[]))
            if pointer_op==65 and pointer_a[0]==candidates[0] and len(pointer_a)==2:
                member=constants.get(pointer_a[1]);name=member_names.get((root,member))
                if name in fields and fields[name]['kind']=='matrix':return name,transposed
        return None
    uses={}
    for op,a in matrix_ops:
        origin=matrix_origin(a[3] if op==144 else a[2])
        if origin:
            name,transposed=origin;entry=dict(opcode=op,operand_transposed=transposed,transpose_logical_matrix_for_column_apply=bool((op==144)^transposed))
            if entry not in uses.setdefault(name,[]):uses[name].append(entry)
    return dict(descriptor_set=1,binding=2,fields=fields,matrix_uses=uses)

def field(raw,layout,name):
    f=layout['fields'][name];o=f['offset'];need(o>=0 and o+f['bytes']<=len(raw),'constant offset outside record')
    kind=f['kind'];fmt='f' if kind in ('matrix','float') else 'i' if kind=='int' else 'I'
    a=np.array(struct.unpack_from('<'+fmt*f['count'],raw,o));need(np.isfinite(a).all(),'nonfinite constants')
    if kind=='matrix':return a.reshape(4,4) if f['major']=='row' else a.reshape(4,4).T
    return a if f['count']>1 else a[0].item()

def decode_normals(packed):
    p=np.stack([((packed>>s)&1023)/1023. for s in (0,10,20)],axis=-1)
    x=p[:,0]-p[:,1];y=p[:,0]+p[:,1]-1.;z=np.where(p[:,2]*2-1<0,-1.,1.)*(1-np.abs(x)-np.abs(y))
    n=np.stack([x,y,z],axis=-1);length=np.linalg.norm(n,axis=1)
    need(np.isfinite(n).all() and (length>0).all(),'decoded normal nonfinite/zero')
    return n/length[:,None],np.abs(p[:,2]*2-1),(packed>>30)

def geometry(camera,hits,z,packed,motion,values,width=320,height=180):
    n=width*height;need(len(hits)==n and z.shape==(n,) and packed.shape==(n,) and motion.shape==(n,4),'guide shape')
    active=hits['flag']==1;idx=np.arange(n);xy=np.stack([2*(idx%width+.5)/width-1,1-2*(idx//width+.5)/height],axis=1)
    ray=camera[4:7]+xy[:,0,None]*camera[11]*camera[8:11]+xy[:,1,None]*camera[15]*camera[12:15];ray/=np.linalg.norm(ray,axis=1)[:,None]
    expected=ray*hits['t'].astype(float)[:,None]
    uv=np.stack([(idx%width+.5)*values['gRectSizeInv'][0]*2-1,(idx//width+.5)*values['gRectSizeInv'][1]*2-1],axis=1)
    def reconstruct(prefix):
        return z[:,None]*(values[prefix+'FrustumForward'][:3]+uv[:,0,None]*values[prefix+'FrustumRight'][:3]-uv[:,1,None]*values[prefix+'FrustumUp'][:3])
    current=reconstruct('g');previous=reconstruct('gPrev');error=current-expected;prev_error=previous-expected
    bound=np.maximum(2e-5,32*np.spacing(np.abs(expected).astype('<f4')).astype(float))
    flags=dict(position=bool(np.isfinite(current).all() and (np.abs(error[active])<=bound[active]).all()),previous_position=bool(np.isfinite(previous).all() and (np.abs(prev_error[active])<=bound[active]).all()),positive_viewz=bool(np.isfinite(z).all() and (z>0).all() and (z[~active]>values['gDenoisingRange']).all()),static_motion=bool((motion==0).all()))
    clip_errors={};clip_metrics={}
    homogeneous=np.column_stack([expected,np.ones(n)])
    for name in ('gWorldToClip','gWorldToClipPrev'):
        clip=homogeneous@values[name].T;safe=np.where(clip[:,3]!=0,clip[:,3],1.)
        ndc=clip[:,:3]/safe[:,None];residual=ndc[:,:2]-xy
        flags[name]=bool(np.isfinite(clip[active]).all() and (clip[active,3]>0).all() and (ndc[active,2]>=0).all() and (ndc[active,2]<=1).all() and (np.abs(residual[active])<=2e-5).all())
        clip_errors[name]=residual;clip_metrics[name]=float(np.abs(residual[active]).max(initial=0))
    decoded,roughness,material=decode_normals(packed);normal_error=decoded-hits['n'].astype(float)
    flags.update(normal=bool((np.abs(normal_error[active])<=4/1023).all()),roughness=bool((roughness==1).all()),material=bool((material==0).all()))
    metrics=dict(pass_=all(flags.values()),checks=flags,pixels=n,active_primary_pixels=int(active.sum()),sky_pixels=int((~active).sum()),maximum_position_coordinate_error=float(np.abs(error[active]).max(initial=0)),maximum_previous_position_coordinate_error=float(np.abs(prev_error[active]).max(initial=0)),maximum_normal_coordinate_error=float(np.abs(normal_error[active]).max(initial=0)),maximum_ndc_xy_errors=clip_metrics)
    maps=dict(active_primary=active,expected_camera_relative_position=expected,sdk_camera_relative_position=current,position_coordinate_error=error,previous_position_coordinate_error=prev_error,position_coordinate_bound=bound,decoded_normal=decoded,normal_coordinate_error=normal_error,**clip_errors)
    return metrics,maps

def bounds(out):
    resource.setrlimit(resource.RLIMIT_CPU,(240,240));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    out=out.resolve();need(out.is_relative_to(BASE) and not out.exists(),'027 exclusive output under repository out required');return out

def execute(out,contracts=None):
    head=committed();out=bounds(out);out.mkdir()
    r=dict(schema='m001-nrd027-saved-input-semantics/1',source_commit=head,complete=False,valid=False,all_pass=False,classification='AUDIT_IMPLEMENTATION_OR_PROVENANCE_FAIL',gpu_executed=False,sdk_api_executed=False,new_image_or_reference_samples=0,original_quality_metrics_rerun=False,old_successful_cohorts_rerun=False,accepted_timing=False,lane_m_complete=False,input_sha256={str(p):B.SHA(p) for p in OWN},rows=[],geometry=[])
    def pin(p,expected=None):
        p=Path(p);h=B.SHA(p);need(expected is None or h==expected,'027 consumed identity differs: '+str(p));r['input_sha256'][str(p)]=h;return p
    def parent(p):
        p=pin(p);need(subprocess.check_output(['git','show',BASE_COMMIT+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'027 parent report bytes differ');return B.read(p)
    try:
        if contracts is None:
            fixture=BASE/'m001-nrd026-gpu-h01-b2-n1-v1';fixture_receipt=B.read(pin(fixture/'result.json'))
            pin(fixture/'capture/pipelines/9.spv',fixture_receipt['payload_sha256']['capture/pipelines/9.spv'])
            import unittest
            import test_nrd_semantics as tests
            suite=unittest.defaultTestLoader.loadTestsFromModule(tests);count=suite.countTestCases()
            with (out/'contracts.log').open('x') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
            r.update(complete=True,valid=True,all_pass=result.wasSuccessful(),classification='CPU_AUDIT_CONTRACTS_PASS' if result.wasSuccessful() else 'CPU_AUDIT_CONTRACTS_FAIL',actual_python_tests=count,test_failures=len(result.failures),test_errors=len(result.errors))
        else:
            c=B.read(pin(contracts));need(c['complete'] and c['all_pass'] and c['classification']=='CPU_AUDIT_CONTRACTS_PASS','027 contracts before semantic evidence');B.rehash(c['input_sha256']);need(c['source_commit']==head,'027 exact qualified audit source')
            summary=parent(LANE/'results/163-nrd-cold-warm-six-targets-summary.json');preservation=parent(LANE/'results/165-nrd-cold-warm-six-targets-verification.json');need(summary['study_complete'] and preservation['all_checks_pass'],'027 terminal026 proof')
            pin(preservation['raw_receipt'],preservation['raw_receipt_sha256'])
            source=S.EXTERNAL/'NRD-e06852bd';need(subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==S.PINS['NRD-e06852bd'] and not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source),'027 pinned clean SDK source')
            text={name:pin(source/name).read_text() for name in SOURCE_NAMES}
            host=text['Source/Relax.cpp'];settings=text['Include/NRDSettings.h'].split('struct RelaxSettings',1)[1]
            need('consts->gLuminanceEdgeStoppingRelaxation = settings.roughnessEdgeStoppingRelaxation;' in host and 'float luminanceEdgeStoppingRelaxation = 0.5f;' in settings and 'float roughnessEdgeStoppingRelaxation = 1.0f;' in settings,'027 disclosed source/default mapping')
            for token in ['out.diffHitDist += normHitDist;','out.diffHitDist *= diffNorm;','accumulatedHitDist = hitDist;']:need(token in text['README.md'],'027 documented diffuse convention')
            for path in [S.O.PT,Path(S.__file__),ROOT/'scripts/research/lane_m_gi_competitiveness/nrd_vulkan_overlay.py',ROOT/'shaders/research/lane_m_gi_competitiveness/nrd_pack_guides.hlsl',ROOT/'shaders/research/lane_m_gi_competitiveness/nrd_composite_rgb.hlsl']:
                pin(path);need(subprocess.check_output(['git','show',BASE_COMMIT+':'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'027 physical/packing source unchanged')
            physical=S.O.PT.read_text();need('grey rho=1' in physical and 'vec3 wi=cosine_direction(n)' in physical and 'indirect+=direct_light(next_position,next_normal,next_primitive);' in physical,'027 homogeneous all-diffuse physical boundary')
            prep=parent(LANE/'results/146-nrd-cold-warm-hdr-cpu-preparation.json')
            for x in prep['records']:pin(x['raw_receipt'],x['raw_receipt_sha256'])
            native_build=B.read(prep['records'][0]['raw_receipt'])
            pin(native_build['sdk_library'],native_build['input_sha256'][native_build['sdk_library']])
            pin(native_build['executable'],native_build['payload_sha256'][str(Path(native_build['executable']).relative_to(Path(prep['records'][0]['raw_receipt']).parent))])
            canonical_layouts=None;geometry_bytes={};geometry_values={};guide_bytes={};sdk_records=relax_records=clear_records=0;all_numeric=True
            for target in summary['targets']:
                cell=target['cell'];depth=target['depth'];report=parent(LANE/'results'/target['report']);need(B.SHA(LANE/'results'/target['report'])==target['report_sha256'],'027 target outcome identity')
                for row in report['rows']:
                    native_path=pin(row['native_receipt'],row['native_receipt_sha256']);native=B.read(native_path);audit=B.read(pin(row['audit_receipt'],row['audit_receipt_sha256']));need(native['complete'] and native['valid'] and audit['complete'] and audit['valid'],'027 original audit validity')
                    work=native_path.parent;plan=B.read(pin(work/'plan.json',native['plan_sha256']));capture=work/'capture'
                    def payload(path):
                        p=Path(path);return pin(p,native['payload_sha256'][str(p.relative_to(work))])
                    cpu=Path(plan['proof']['sdk_cpu_capture']);config=B.read(pin(cpu/'instance.json',plan['input_sha256'][str(cpu/'instance.json')]))
                    need(config['default_settings']==dict(diffuse_history=30,fast_history=6,atrous_iterations=5,diffuse_prepass_radius=30,antifirefly=False,checkerboard=0,hit_distance_reconstruction=0),'027 registered default settings')
                    need(config['normal_encoding']==2 and config['roughness_encoding']==1,'027 actual encoding ABI')
                    layouts=[];pipeline_hashes=[]
                    for j in range(15):
                        p=payload(capture/f'pipelines/{j}.spv');pipeline_hashes.append(B.SHA(p));layouts.append(reflect(p.read_bytes(),j<13))
                        pin(cpu/f'pipelines/{j}.spv',pipeline_hashes[-1])
                    layout_identity=dict(layouts=layouts,pipeline_sha256=pipeline_hashes)
                    if canonical_layouts is None:canonical_layouts=layout_identity
                    need(layout_identity==canonical_layouts,'027 all captured pipeline/layout identities')
                    matrix_convention={}
                    for name in ('gWorldToClip','gWorldToClipPrev'):
                        orientations={u['transpose_logical_matrix_for_column_apply'] for layout in layouts for u in layout['matrix_uses'].get(name,[])}
                        need(len(orientations)==1,'027 unique actual shader matrix operand convention: '+name)
                        matrix_convention[name]=orientations.pop()
                    cpuf=pin(cpu/'dispatches.jsonl',plan['input_sha256'][str(cpu/'dispatches.jsonl')]);reference=[json.loads(x) for x in cpuf.read_text().splitlines()][:64]
                    entries=[json.loads(x) for x in payload(capture/'sdk-dispatches.jsonl').read_text().splitlines()];need(len(entries)==651,'027651 actual SDK records')
                    camera=np.fromfile(payload(capture/'frame-0/camera.f32'),dtype='<f4').astype(float);failures=[];rrelax=rclear=0
                    for entry in entries:
                        i=entry['iteration'];j=entry['dispatch'];pipeline=entry['pipeline'];raw=payload(capture/f'frame-{i}/constants/{j}.bin').read_bytes()
                        old=reference[i]['dispatches'][j];cp=cpu/'constants'/old['constant_file'];pin(cp,plan['input_sha256'][str(cp)]);need(raw==cp.read_bytes() and len(raw)==entry['constant_bytes'] and pipeline==old['pipeline'],'027 exact actual-to025 CPU constant record')
                        sdk_records+=1
                        if pipeline>=13:clear_records+=1;rclear+=1;need(i==0,'027 CLEAR dispatch outside initial frame');continue
                        relax_records+=1;rrelax+=1;layout=layouts[pipeline];values={k:field(raw,layout,k) for k in REQUIRED}
                        # DXC may lower HLSL mul(M,v) to OpVectorTimesMatrix.
                        # Follow actual SPIR-V operands, including OpTranspose.
                        for name,transpose in matrix_convention.items():
                            if transpose:values[name]=values[name].T
                        key=b''.join(raw[layout['fields'][k]['offset']:layout['fields'][k]['offset']+layout['fields'][k]['bytes']] for k in GEOMETRY)
                        if cell not in geometry_bytes:geometry_bytes[cell]=key;geometry_values[cell]=values
                        need(geometry_bytes[cell]==key,'027 static per-cell geometry constant bytes')
                        expected=dict(DEFAULTS,gDiffMaxAccumulatedFrameNum=0. if i==0 else 30.,gDiffMaxFastAccumulatedFrameNum=0. if i==0 else 6.,gOrthoMode=0.,gViewZScale=1.,gDenoisingRange=camera[7])
                        checks={k:bool(values[k]==v) for k,v in expected.items()}
                        checks.update(rect_size=bool(np.array_equal(values['gRectSize'],[320,180])),resource_size=bool(np.array_equal(values['gResourceSize'],[320,180])),rect_size_inv=bool(np.array_equal(values['gRectSizeInv'],np.array([1/320,1/180],dtype='<f4'))))
                        for k in ['gInputRectOrigin','gOutputRectOrigin','gDispatchInputRectOrigin','gDispatchOutputRectOrigin','gCameraDelta','gMvBias','gJitter']:checks[k]=bool((values[k]==0).all())
                        if not all(checks.values()):failures.append(dict(frame=i,dispatch=j,pipeline=pipeline,failed_checks=[k for k,v in checks.items() if not v]))
                    need(rrelax==640 and rclear==11,'027 exact RELAX/Clear record coverage')
                    for i in (0,1,63):
                        saved={name:payload(capture/f'frame-{i}'/name) for name in ['camera.f32','hits.u32','view-z.bin','normal-roughness.bin','motion.bin']}
                        identities={name:B.SHA(p) for name,p in saved.items()}
                        if cell not in guide_bytes:
                            guide_bytes[cell]=identities;hits=np.fromfile(saved['hits.u32'],dtype=M.GPU_DTYPE)
                            metrics,maps=geometry(np.fromfile(saved['camera.f32'],dtype='<f4').astype(float),hits,np.fromfile(saved['view-z.bin'],dtype='<f4').astype(float),np.fromfile(saved['normal-roughness.bin'],dtype='<u4'),np.fromfile(saved['motion.bin'],dtype='<f4').reshape(-1,4),geometry_values[cell])
                            np.savez(out/(cell.lower()+'-full-geometry-errors.npz'),**maps);r['geometry'].append(dict(cell=cell,representative_capture=str(capture),representative_frame=i,**metrics));all_numeric &= metrics['pass_']
                        need(guide_bytes[cell]==identities,'027 static per-cell primary guide bytes')
                    all_numeric &= not failures
                    r['rows'].append(dict(cell=cell,depth=depth,spp=row['spp'],sdk_records=len(entries),relax_records=rrelax,clear_records=rclear,all_constant_predicates_pass=not failures,constant_failures=failures,guide_frames=[0,1,63],static_guide_identity_verified=True))
                    print(cell,depth,row['spp'],'640 RELAX/11 Clear records; three saved frames checked',flush=True)
            need(len(r['rows'])==24 and len(r['geometry'])==3 and sdk_records==15624 and relax_records==15360 and clear_records==264,'027 full registered coverage')
            r.update(complete=True,valid=True,all_pass=bool(all_numeric),classification='SEMANTIC_BOUNDARY_PASS_CONFIGURED_QUALITY_FAIL_RETAINED' if all_numeric else 'SEMANTIC_BOUNDARY_FAIL_PRIOR_NUMBERS_DIAGNOSTIC',sdk_constant_records=sdk_records,relax_constant_records=relax_records,clear_constant_records=clear_records,saved_guide_frame_instances=72,unique_geometry_maps=3,pipeline_reflections=canonical_layouts,static_geometry_member_identity_proof={k:hashlib.sha256(v).hexdigest() for k,v in geometry_bytes.items()},static_guide_identity_proof=guide_bytes,source_default_discrepancy=dict(setting='luminanceEdgeStoppingRelaxation',declared_default=.5,constant='gLuminanceEdgeStoppingRelaxation',actual_source_setting='roughnessEdgeStoppingRelaxation',actual_default_constant=1.,actual_constant_records_verified=relax_records,quality_impact_tested=False),source_conventions=dict(first_secondary_cosine_diffuse_average=True,homogeneous_rho1_zero_specular_material_factor=1,linear_rgb_direct_separate=True,existing_all_sample_packing_physical_hdr_lifetime_audits_reused=True),old_quality_joint_pass_targets=0,parent_preservation_receipt_sha256=B.SHA(LANE/'results/165-nrd-cold-warm-six-targets-verification.json'),timing_selected=False)
    except Exception as e:r.update(error=type(e).__name__+': '+str(e),classification='AUDIT_IMPLEMENTATION_OR_PROVENANCE_FAIL')
    try:B.rehash(r['input_sha256'])
    except Exception as e:r.update(complete=False,valid=False,all_pass=False,classification='AUDIT_IMPLEMENTATION_OR_PROVENANCE_FAIL',postcheck_error=str(e))
    r['payload_sha256']=B.inventory(out);B.write(out/'result.json',r)
    print(json.dumps({k:r.get(k) for k in ('complete','valid','all_pass','classification','error','actual_python_tests','sdk_constant_records')}));return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--contracts',type=Path);args=ap.parse_args()
    result=execute(args.out,args.contracts);raise SystemExit(0 if result['all_pass'] else 2)

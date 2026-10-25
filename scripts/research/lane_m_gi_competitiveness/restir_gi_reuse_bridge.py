#!/usr/bin/env python3
"""042 receiver-frame SDK ReSTIR GI reuse: CPU preparation, ordered GPU cases, supervised replay and quality audit."""
import argparse
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import numpy as np
import restir_gi_local_bridge as G
import restir_gi_reuse_model as R

C,I,S=G.C,G.I,G.S
ROOT,BASE=G.ROOT,G.BASE
EXP=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments'
PROTOCOLS=[EXP/'042-receiver-frame-restir-gi-reuse.md',EXP/'042a-replay-boundary-addendum.md',EXP/'042b-development-smoke-disclosure.md']
CPP=I.SOURCE/'restir_gi_reuse_gpu.cpp';TOOL=I.SOURCE/'restir_gi_reuse_visibility.cpp';HLSL=I.SHADERS/'restir_gi_reuse.hlsl'
OWN=[*PROTOCOLS,CPP,TOOL,HLSL,Path(__file__).resolve(),Path(R.__file__),Path(__file__).with_name('test_restir_gi_reuse.py')]
PREP=BASE/'m001-restir042-cpu-build-v1'
OLD022=BASE/'m001-integrated022-cpu-build-v1';OLD033=BASE/'m001-restir033-cpu-build-v3';OLD041=BASE/'m001-restir041-cpu-build-v1'
OFFSETS=OLD033/'host-data/neighbor-offsets.u8'
TARGETS=(('H01',2),('H01',8),('H02',2),('H02',8),('H03',2),('H03',8))
NUMERIC=dict(cpu=[1200,1200],address=[C.ADDRESS,C.ADDRESS],core=[0,0],sigxcpu_default=True,sigxcpu_unblocked=True)
need=R.need;read=G.read;sha=G.sha


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def committed():
    head=git('rev-parse','HEAD');need(git('branch','--show-current')=='research-lane-m-gi-competitiveness','research branch')
    for anchor in ('d576bc75','7e9dbef3','7c41269a'):subprocess.run(['git','merge-base','--is-ancestor',anchor,head],cwd=ROOT,check=True)
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit all042 sources before use '+p.name)
    return head


def proof(cell,depth):
    plan=read(BASE/f'm001-integrated022-gpu-{cell.lower()}-b{depth}-v1/plan.json');return plan['proof']


def reference(cell,depth,pins=None):
    directory=Path(proof(cell,depth)['reference']['directory']);q=read(directory/'qualification.json')
    need(q['classification']=='STATISTICALLY_ELIGIBLE' and q['levels'][-1]['spp']==16384,'admitted16384 reference')
    payload={str(directory/k):v for k,v in q['levels'][-1]['all_payload_sha256'].items()};G.rehash(payload)
    if pins is not None:pins.update(payload);pins[str(directory/'qualification.json')]=sha(directory/'qualification.json')
    import n008lib as L
    means=np.mean([L.read_sidecar(directory/f'o.n16384.s{i}.f64')['mean'] for i in range(4)],axis=0)
    return {name:means[...,L.COMPONENTS.index(name),:]@R.LUMA for name in ('direct','indirect','total')},directory


def imports():
    official,trees=S.source_pins();pins=dict(official)
    pins.update({str(p):sha(p) for p in [*OWN,Path(C.__file__),Path(G.__file__),Path(I.__file__),Path(R.D.__file__),Path(R.M.__file__),Path(sys.executable),I.VAL,I.VAL.parent/'spirv-dis',S.N.DXC]})
    for p in S.N.DXC.parent.parent.rglob('*'):
        if p.is_file():pins[str(p)]=sha(p)
    old022=G.pin_archive(OLD022/'result.json',pins);need(not old022['gpu_executed'],'original022 CPU build')
    old033=read(OLD033/'result.json');need(old033['all_pass'] and old033['payload_sha256']['host-data/neighbor-offsets.u8']==sha(OFFSETS),'qualified033 neighbor offsets');pins[str(OFFSETS)]=sha(OFFSETS);pins[str(OLD033/'result.json')]=sha(OLD033/'result.json')
    old041=G.pin_archive(OLD041/'result.json',pins);need(old041['all_pass'] and old041['classification']=='CPU_FIXED_RADIANCE_UNIT_RANGE_PREPARATION_PASS','qualified041 preparation')
    sys.path.insert(0,str(ROOT/'scripts/research/n008_hdr_oracle'))
    for cell,depth in TARGETS:G.source_state(cell,depth,pins);reference(cell,depth,pins)
    return pins,old022,old041,trees


def build():
    head=committed();need(not PREP.exists() and shutil.disk_usage(BASE).free>=16*1024**3,'exclusive042 preparation/16GiB');pins,old022,old041,trees=imports();PREP.mkdir()
    C.write(PREP/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir042-cpu-preparation/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,input_sha256=pins,official_source_trees=trees,rows=[],compiled_dependency_sha256={})
    try:
        r['effective_parent']=C.limits();os.chdir(I.BUILD)
        os.environ.update(VK_ICD_FILENAMES='/042-no-gpu.json',VK_DRIVER_FILES='/042-no-gpu.json',RESTIR042_TOOL=str(PREP/'reuse-visibility'))
        os.environ['LD_LIBRARY_PATH']=str(S.N.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))
        shutil.copyfile(OLD041/'physical_producer.spv',PREP/'physical_producer.spv');need(sha(PREP/'physical_producer.spv')==old041['payload_sha256']['physical_producer.spv'],'exact041 producer SPIR-V')
        command=list(next(x['command'] for x in old022['rows'] if x['label']=='host-compile'))
        for flag,value in (('-c',CPP),('-o',PREP/'host.o'),('-MT',PREP/'host.o'),('-MF',PREP/'host.d')):command[command.index(flag)+1]=str(value)
        rows=[('host-compile',command)]
        command=list(next(x['command'] for x in old022['rows'] if x['label']=='host-link'))
        command=[str(PREP/'host.o') if x==str(OLD022/'host.o') else '-Wl,--dependency-file='+str(PREP/'link.d') if x.startswith('-Wl,--dependency-file=') else x for x in command]
        command[command.index('-o')+1]=str(PREP/'reuse-gpu');rows.append(('host-link',command))
        rows.append(('visibility-compile',['c++','-O2','-std=c++20','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror','-o',PREP/'reuse-visibility',TOOL]))
        for stage in range(5):
            stem=f'reuse_s{stage}';args=[S.N.DXC,HLSL,'-HV','2021','-T','cs_6_5','-E','main','-spirv','-fspv-target-env=vulkan1.3','-fvk-use-dx-layout','-Od','-WX','-D',f'STAGE={stage}','-I',S.LIB/'Include']
            rows.extend([(stem+'-dependencies',args+['-Fo',PREP/(stem+'.spv'),'-MD','-MF',PREP/(stem+'.shader.d')]),(stem+'-compile',args+['-Fo',PREP/(stem+'.spv')]),(stem+'-validate',[I.VAL,'--target-env','vulkan1.3',PREP/(stem+'.spv')]),(stem+'-disassemble',[I.VAL.parent/'spirv-dis',PREP/(stem+'.spv'),'-o',PREP/(stem+'.spvasm')])])
        rows.append(('new-python-contracts',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_reuse.py','-v']))
        for cell,depth in TARGETS:
            state=G.source_state(cell,depth,pins);rows.append((f'cpu-{cell.lower()}-b{depth}',[PREP/'reuse-gpu','--cpu-check','--state',state,'--out',PREP/f'cpu-{cell.lower()}-b{depth}','--vertices',depth,'--shaders',PREP,'--offsets',OFFSETS,'--stream-base',0]))
        for label,args in rows:
            print('042',label,'START',flush=True);r['rows'].append(dict(label=label,process=G.guard(args,PREP,label)));print('042',label,'PASS',flush=True)
        for stage in range(5):
            asm=(PREP/f'reuse_s{stage}.spvasm').read_text();dep=(PREP/f'reuse_s{stage}.shader.d').read_text()
            need('ArrayStride 32' in asm and 'ArrayStride 48' in asm and 'ArrayStride 144' in asm and 'Reservoir.hlsli' in dep and 'TemporalResampling.hlsli' in dep and 'SpatialResampling.hlsli' in dep,'stage ABI/official SDK dependencies')
            need(('OpRayQueryInitializeKHR' in asm)==(stage in (1,2,3)),'actual real-BVH visibility only in reuse/shading stages')
            need(stage not in (1,2) or 'NoContraction' in asm,'precise receiver-frame transform')
        for name in shlex.split((PREP/'host.d').read_text().replace('\\\n',' '))[1:]:
            file=Path(name);file=file if file.is_absolute() else I.BUILD/file
            if file.is_file():r['compiled_dependency_sha256'][str(file)]=sha(file)
        epsilon={}
        for cell,depth in TARGETS:
            j=read(PREP/f'cpu-{cell.lower()}-b{depth}/complete.json');need(j['complete'] and not j['gpu_initialized'] and j['vertices']==depth,'actual unusable-ICD native input check');epsilon[f'{cell}/B{depth}']=j['epsilon']
        G.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_REUSE_PREPARATION_PASS',new_python_contracts=True,new_native_compilations=2,new_shader_compilations=5,native_cpu_input_checks=6,old_successful_tests_reexecuted=False,epsilon=epsilon)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(PREP,r)


def case_root(cell,depth):
    need((cell,depth) in TARGETS,'registered042 case');return BASE/f'm001-restir042-{cell.lower()}-b{depth}-v1'


def native_command(root,state,depth):
    return [str(PREP/'reuse-gpu'),'--gpu','--state',str(state),'--out',str(root/'capture'),'--vertices',str(depth),'--shaders',str(PREP),'--offsets',str(OFFSETS),'--stream-base','0']


def native_audit(capture,depth,state,base=0):
    j=read(capture/'complete.json');need(j['complete'] and j['gpu_initialized'] and j['frames']==256 and j['streams']==4 and j['dispatches']==256*458 and j['vertices']==depth and j['stream_base']==base and j['variants']==2 and j['record_frames']==list(R.RECORD),'complete native work')
    need(not j['quality_admitted'] and not j['accepted_timing'] and j['input_images_uploaded']==0 and j['input_candidates_uploaded']==0,'actual residency/admission boundary')
    for name in ('geometry-state.bin','frame-state.bin'):need((capture/name).read_bytes()==(state/name).read_bytes(),'exact original scene/frame')
    ledger=read(capture/'allocation-ledger.json');need(ledger['teardown_zero'] and ledger['device_contexts']==1 and ledger['live_bytes_at_teardown']==0,'single-context zero ownership')
    live={};peak=0;live_bytes=0;allocations=[]
    for index,e in enumerate(ledger['events']):
        need(e['sequence']==index and e['device_context']==1 and e['bytes']>0,'owned event')
        key=e['allocation_id']
        if e['action']=='allocate':need(key not in live,'unique allocation');live[key]=e;live_bytes+=e['bytes'];allocations.append(e)
        else:
            need(e['action']=='free' and key in live,'matching free');old=live.pop(key)
            need(all(old[k]==e[k] for k in ('bytes','buffer_usage','memory_type','requested_properties','device_context')),'matching allocation identity');live_bytes-=e['bytes']
        need(live_bytes==e['live_bytes'],'live bytes');peak=max(peak,live_bytes)
    need(not live and peak==ledger['true_peak_owned_bytes']==j['aggregate_reserved_peak'] and peak<=8*1024**3 and j['aggregate_reserved_at_teardown']==0,'true peak/teardown/cap')
    n=R.N;sizes=[16*n,32*n,4*n,80*n*depth,128*n,16*n,128,32*R.PITCH*6,16*R.PITCH*6,96*n,8*8192,64*n,16*n,144,24*n,32]
    pipeline=[e for e in allocations if e['requested_properties']==6 and e['buffer_usage'] in (16,32)][-16:]
    need(len(pipeline)==16 and [e['buffer_usage'] for e in pipeline]==[32]*6+[16]+[32]*9 and all(e['bytes']>=s+256 for e,s in zip(pipeline,sizes)),'all pipeline allocations plus guards')
    need(any(e['buffer_usage']&0x100000 for e in allocations) and any(e['buffer_usage']&0x20000 for e in allocations),'AS/scratch allocation coverage')
    device=read(capture/'device.json');need(device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and device['vendor_id']==4098 and device['device_id']==5510,'same qualified GPU identity')
    bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];need(1<=bits<=64 and math.isfinite(period) and period>0,'timestamp precision')
    journal=[json.loads(line) for line in (capture/'frames.jsonl').read_text().splitlines()];need(len(journal)==256,'complete frame journal')
    passes=np.zeros((256,9))
    for k,row in enumerate(journal):
        s,f=divmod(k,64);fi=4096*(base+s)+f
        need(row['stream']==s and row['frame']==f and row['frame_index']==fi and row['producer_seed']==R.producer_seed(base+s,f) and row['uniform_random']==int(R.jenkins(fi)) and row['errors']==0,'registered seeds/order/no shader errors')
        t=row['timestamps'];us=[((t[a+1]-t[a])&((1<<bits)-1))*period/1000 for a in range(9)]
        need(np.allclose(us,row['pass_gpu_us_diagnostic'],rtol=1e-12,atol=1e-9) and all(0<=x<=250000 for x in us),'pass timestamps');passes[k]=us
    need(np.isclose(passes.sum(),j['active_gpu_us_diagnostic'],rtol=1e-9),'all active passes charged')
    for s in range(4):
        need((capture/f'stream-{s}/frames.f32').stat().st_size==64*n*16,'complete per-frame images')
        for f in R.RECORD:
            folder=capture/f'stream-{s}/frame-{f}'
            expect={'producer-image.f32':16*n,'hits.u32':32*n,'candidates.bin':128*n,'local-endpoints.f32':16*n,'reservoirs.bin':32*R.PITCH*6,'owners.f32':16*R.PITCH*6,'surfaces.bin':96*n,'shading.f32':64*n,'frame-image.f32':16*n,'diagnostics.u32':24*n,'counters.u32':32,
                    'history-reservoirs-null.bin':32*R.PITCH,'history-reservoirs-m0.bin':32*R.PITCH,'history-owners-null.bin':16*R.PITCH,'history-owners-m0.bin':16*R.PITCH,'previous-surfaces.bin':48*n}
            need({p.name:p.stat().st_size for p in folder.iterdir()}==expect,'complete full-record frame files')
    names=['producer','initial','temporal-null','temporal-m0','spatial-null','spatial-m0','shade-null','shade-m0','surface-copy']
    return dict(true_peak_owned_bytes=peak,allocation_pairs=len(allocations),teardown_zero=True,driver_private_and_cpu_excluded=True,frames=256,dispatches=j['dispatches'],device=device,
                pass_gpu_us_mean_diagnostic=dict(zip(names,passes.mean(axis=0).tolist())),frame_gpu_us_mean_diagnostic=float(passes.sum(axis=1).mean()),accepted_timing=False)


def controls(capture,state):
    raw=(capture/'controls.bin').read_bytes();need(len(raw)==144,'controls ABI');f=np.frombuffer(raw,'<f4');u=np.frombuffer(raw,'<u4')
    params=(capture/'params.bin').read_bytes();need(params==(state/'frame-state.bin').read_bytes()[20:20+len(params)],'producer params exact frame state')
    p=np.frombuffer(params,'<f4',count=16).reshape(4,4)
    need(np.array_equal(f[0:3],p[0,:3]) and np.array_equal(f[4:7],p[3,:3]),'camera/forward controls')
    need(list(u[7:16])==[320,180,R.N,64,0,8191,0,0,0] and list(u[16:20])==[R.ROW,R.PITCH,0,0],'viewport/unit/runtime/reservoir controls')
    need(np.array_equal(f[20:22],np.array([.1,.6],np.float32)) and list(u[22:28])==[8,1,3,30,0,0] and u[27]==0,'registered temporal parameters RAY_TRACED')
    need(np.array_equal(f[28:30],np.array([.1,.6],np.float32)) and u[30]==2 and f[31]==32 and list(u[32:36])==[3,0,0,0],'registered spatial parameters RAY_TRACED')
    offsets=np.fromfile(capture/'neighbor-offsets.f32','<f4').reshape(8192,2);raw33=np.fromfile(OFFSETS,np.int8).reshape(8192,2)
    need(np.array_equal(offsets,np.maximum(raw33.astype(np.float32)/np.float32(127),np.float32(-1))),'exact SNORM decode of qualified033 offsets')
    return dict(camera=f[0:3].astype(float),epsilon=float(f[3]),forward=f[4:7].astype(float)),offsets


def metrics(image,reference):
    g=np.asarray(image,float).ravel();r=np.asarray(reference,float).ravel();need(np.isfinite(g).all() and (g>=0).all(),'finite nonnegative scored image')
    e=g-r;rms=math.sqrt(float(np.mean(r*r)));return dict(nrmse=math.sqrt(float(np.mean(e*e)))/rms,signed_sum_bias=float(e.sum()/r.sum()))


def fsum_metrics(image,reference):
    g=np.asarray(image,float).ravel();r=np.asarray(reference,float).ravel();e=g-r
    return dict(nrmse=math.sqrt(math.fsum((e*e).tolist())/len(e))/math.sqrt(math.fsum((r*r).tolist())/len(r)),signed_sum_bias=math.fsum(e.tolist())/math.fsum(r.tolist()))


def passes(m):return m['total']['nrmse']<=.05 and m['indirect']['nrmse']<=.10 and abs(m['indirect']['signed_sum_bias'])<=.05


def score(direct,indirect,ref):
    return {name:metrics(value,ref[name]) for name,value in (('direct',direct),('indirect',indirect),('total',direct.astype(float)+indirect))}


def quality(images,ref):
    """images: (4 streams,64 frames,N,4) float32: direct, PT, V1 null-trial, V0 MISS-M0."""
    methods={'pt':1,'v1_null_trial':2,'v0_miss_m0':3};frames=[];streams=[]
    for s in range(4):
        row=dict(stream=s)
        for m,c in methods.items():
            per=[score(images[s,f,:,0],images[s,f,:,c],ref) for f in range(64)]
            for f,x in enumerate(per):frames.append(dict(stream=s,frame=f,method=m,metrics=x,quality_pass=passes(x)))
            if m=='v1_null_trial':row['q1_cold_pass']=passes(per[0]);row['q1_warm_pass']=all(passes(x) for x in per[48:]);row['q1_joint_pass']=row['q1_cold_pass'] and row['q1_warm_pass']
            mean=images[s,:,:,c].astype(float).mean(axis=0);acc=score(images[s,0,:,0],mean,ref)
            check=fsum_metrics(mean,ref['indirect']);need(math.isclose(check['nrmse'],acc['indirect']['nrmse'],rel_tol=1e-9) and math.isclose(check['signed_sum_bias'],acc['indirect']['signed_sum_bias'],rel_tol=1e-9,abs_tol=1e-15),'independent fsum metrics')
            row[f'q2_{m}']=dict(metrics=acc,quality_pass=passes(acc))
        streams.append(row)
    b1=np.array([r['q2_v1_null_trial']['metrics']['indirect']['signed_sum_bias'] for r in streams]);b0=np.array([r['q2_v0_miss_m0']['metrics']['indirect']['signed_sum_bias'] for r in streams]);bp=np.array([r['q2_pt']['metrics']['indirect']['signed_sum_bias'] for r in streams])
    d=b0-b1;se=float(d.std(ddof=1)/2)
    pooled={m:score(images[0,0,:,0],images[:,:,:,c].astype(float).mean(axis=(0,1)),ref) for m,c in methods.items()}
    return dict(frames=frames,streams=streams,
        q1_target_pass=all(r['q1_joint_pass'] for r in streams),q1_streams_passing=sum(r['q1_joint_pass'] for r in streams),
        q2_streams_passing={m:sum(r[f'q2_{m}']['quality_pass'] for r in streams) for m in methods},
        q2_nrmse_ratio_pt_over_v1=[r['q2_pt']['metrics']['indirect']['nrmse']/r['q2_v1_null_trial']['metrics']['indirect']['nrmse'] for r in streams],
        b1=dict(stream_bias_v1=b1.tolist(),stream_bias_v0=b0.tolist(),difference_mean=float(d.mean()),difference_standard_error=se,h_null_holds=bool(d.mean()>3*se)),
        b2=dict(pooled_v1_indirect_bias=pooled['v1_null_trial']['indirect']['signed_sum_bias'],pooled_pt_indirect_bias=pooled['pt']['indirect']['signed_sum_bias'],pooled_v0_indirect_bias=pooled['v0_miss_m0']['indirect']['signed_sum_bias'],
                v1_within_5_percent=abs(pooled['v1_null_trial']['indirect']['signed_sum_bias'])<=.05),pooled=pooled)


def audit_worker(root,capture,cell,depth):
    need(C.state()==NUMERIC,'numeric worker actual inherited envelope');need(not root.exists(),'exclusive numeric worker');root.mkdir()
    C.write(root/'effective-worker.json',dict(pid=os.getpid(),effective=C.state()))
    r=dict(schema='m001-restir042-numeric-worker/1',source_commit=committed(),cell=cell,depth=depth,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',pid=os.getpid(),effective_worker=NUMERIC,frames=[])
    try:
        state=G.source_state(cell,depth,{});k,offsets=controls(capture,state);data=(capture/'geometry-state.bin').read_bytes();triangles=int(np.frombuffer(data,'<u4',1,4)[0])
        journal=[json.loads(line) for line in (capture/'frames.jsonl').read_text().splitlines()];images=np.stack([np.fromfile(capture/f'stream-{s}/frames.f32','<f4').reshape(64,R.N,4) for s in range(4)])
        need(np.isfinite(images).all() and (images>=0).all(),'all frames finite nonnegative')
        need((R.bits(images[...,0])==R.bits(images[0,0,:,0])).all(),'primary direct bit-identical in all256 frames')
        tool=PREP/'reuse-visibility';work=root/'visibility';work.mkdir()
        for s in range(4):
            for f in R.RECORD:
                row=journal[s*64+f];fr=R.Frame(capture/f'stream-{s}/frame-{f}',k,row['frame_index'],row['uniform_random'])
                need(np.array_equal(R.bits(fr.frame),R.bits(images[s,f])),'record frame equals per-frame readback')
                w=work/f'stream-{s}-frame-{f}';w.mkdir();summary,arrays=R.audit_frame(fr,tool,capture/'geometry-state.bin',triangles,w,offsets)
                with (root/f'stream-{s}-frame-{f}-replay.npz').open('xb') as out:np.savez_compressed(out,**arrays)
                r['frames'].append(dict(stream=s,frame=f,**summary));print('042 replay stream',s,'frame',f,'PASS',flush=True)
        ref,directory=reference(cell,depth);q=quality(images,ref)
        with (root/'quality-frames.json').open('x') as out:json.dump(q.pop('frames'),out)
        need(C.state()==NUMERIC,'numeric profile unchanged')
        r.update(complete=True,all_pass=True,classification='REUSE_REPLAY_AND_QUALITY_SCORED',reference_directory=str(directory),quality=q,
                 replay_frames=len(r['frames']),visibility_queries=sum(x['visibility_queries'] for x in r['frames']),
                 explained_divergences=sum(v[s]['explained'] for x in r['frames'] for v in x['variants'] for s in ('temporal','spatial')))
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(root,r)


def case(cell,depth):
    head=committed();root=case_root(cell,depth);need(not root.exists(),'one exclusive GPU case, no retry')
    pins={str(p):sha(p) for p in OWN};prep=G.pin_archive(PREP/'result.json',pins);need(prep['all_pass'] and not prep['gpu_executed'],'CPU preparation before GPU')
    for c,b in TARGETS[:TARGETS.index((cell,depth))]:
        previous=G.pin_archive(case_root(c,b)/'result.json',pins);need(previous['classification']=='REUSE_CASE_AUDIT_PASS','previous case full audit PASS')
    state=G.source_state(cell,depth,pins);need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB free disk')
    import integrated_pt_process as Q
    Q.quiet();root.mkdir();args=native_command(root,state,depth)
    C.write(root/'inputs-before.json',dict(source_commit=head,input_sha256=pins,command=args,gpu_processes_authorized=1))
    r=dict(schema='m001-restir042-gpu-case/1',source_commit=head,cell=cell,depth=depth,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',input_sha256=pins,gpu_executed=False)
    try:
        r['effective_parent']=C.limits();r['gpu_executed']=True;r['native_process']=G.guard(args,root,'native');r['native_audit']=native_audit(root/'capture',depth,state)
        worker=[sys.executable,Path(__file__).resolve(),'audit-worker','--root',root/'audit','--capture',root/'capture','--cell',cell,'--depth',depth]
        r['numeric_process']=G.guard(worker,root,'numeric',1200,1800);a=read(root/'audit/result.json')
        need(a['all_pass'] and a['pid']==r['numeric_process']['pid'] and a['replay_frames']==12,'supervised full replay/quality audit')
        G.rehash(pins);r.update(complete=True,all_pass=True,classification='REUSE_CASE_AUDIT_PASS',numeric_audit=a,accepted_timing=False)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return G.finish(root,r)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('build')
    p=sub.add_parser('case');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',type=int,choices=[2,8],required=True)
    p=sub.add_parser('audit-worker');p.add_argument('--root',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',type=int,choices=[2,8],required=True)
    args=parser.parse_args()
    if args.mode=='build':sys.exit(build())
    elif args.mode=='case':sys.exit(case(args.cell,args.depth))
    else:sys.exit(audit_worker(args.root,args.capture,args.cell,args.depth))

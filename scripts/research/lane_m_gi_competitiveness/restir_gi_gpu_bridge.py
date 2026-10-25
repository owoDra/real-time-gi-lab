#!/usr/bin/env python3
"""037 exclusive CPU preparation and ordered supervised physical GPU bridge."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import numpy as np
import anchor_process_limits as C
import build_integrated_pt as I
import restir_gi_source_build as S
import restir_gi_gpu_overlay as O
import restir_gi_gpu_model as M

ROOT,BASE=I.ROOT,I.BASE
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/037-restir-gi-on-device-physical-candidate-bridge.md'
CPP=I.SOURCE/'restir_gi_physical_gpu.cpp';HLSL=I.SHADERS/'restir_gi_physical_make.hlsl'
OWN=[PROTOCOL,CPP,HLSL,Path(__file__).resolve(),Path(O.__file__),Path(M.__file__),Path(__file__).with_name('test_restir_gi_gpu_bridge.py')]
PREP=BASE/'m001-restir037-cpu-build-v1';OLD=BASE/'m001-integrated022-cpu-build-v1'
read=S.B.read;sha=S.B.SHA;need=M.need


def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'result.json'}
def rehash(pins):
    for p,h in pins.items():need(Path(p).is_file() and sha(p)==h,'immutable input '+p)
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def committed():
    head=git('rev-parse','HEAD');need(git('branch','--show-current')=='research-lane-m-gi-competitiveness','research branch')
    subprocess.run(['git','merge-base','--is-ancestor','2d427d0b',head],cwd=ROOT,check=True)
    for p in OWN:need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit complete037 source before execution')
    return head


def pin_archive(path,pins):
    j=read(path);need(j['complete'] and j.get('all_pass',j.get('valid',False)),'qualified imported receipt '+str(path))
    payload={str(path.parent/k):v for k,v in j['payload_sha256'].items()};rehash(payload)
    need(inventory(path.parent)==j['payload_sha256'],'complete imported inventory '+str(path))
    pins.update(payload);pins[str(path)]=sha(path)
    for key in ('input_sha256','compiled_dependency_sha256'):
        if key in j:rehash(j[key]);pins.update(j[key])
    return j


def source_state(cell,depth,pins):
    native=BASE/f'm001-integrated022-gpu-{cell.lower()}-b{depth}-v1/result.json'
    j=read(native);need(j['complete'] and j['valid'],'original physical022 native receipt')
    plan=native.parent/'plan.json';need(sha(plan)==j['payload_sha256']['plan.json'],'original022 plan identity')
    p=read(plan);folder=Path(p['proof']['primary_capture']);pins[str(native)]=sha(native);pins[str(plan)]=sha(plan)
    for name in ('geometry-state.bin','frame-state.bin'):
        file=folder/name;need(sha(file)==p['input_sha256'][str(file)],'original admitted state identity');pins[str(file)]=sha(file)
    return folder


def imports():
    pins,trees=S.source_pins();pins.update({str(p):sha(p) for p in [*OWN,Path(C.__file__),Path(I.__file__),Path(I.D.__file__),Path(O.O.__file__),Path(M.D.__file__),Path(S.__file__),Path(sys.executable),I.GLSLANG,I.VAL,I.VAL.parent/'spirv-dis',S.N.DXC,I.D.LOADER]})
    old=pin_archive(OLD/'result.json',pins);need(not old['gpu_executed'],'original022 CPU build')
    for name in ('130-integrated-pt-reconstruction-six-targets-raw-replay.json','219-restir-gi-physical-audit-envelope-supersession.json','225-restir-gi-supervised-audit-verification.json'):
        p=ROOT/'research/lanes/lane-m-gi-competitiveness/results'/name
        need(subprocess.check_output(['git','show','8403b491:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'original prerequisite publication');pins[str(p)]=sha(p)
    for p in S.N.DXC.parent.parent.rglob('*'):
        if p.is_file():pins[str(p)]=sha(p)
    for cell,depth in M.TARGETS:source_state(cell,depth,pins)
    return pins,old,trees


def guard(command,root,label,cpu=120,wall=180):
    args=list(map(str,command));row=C.guarded(args,root,label,cpu=cpu,wall=wall)
    specification=read(root/(label+'.command.json'));effective=read(root/(label+'.child-limits.json'));terminal=read(root/(label+'.process.json'));pid=read(root/(label+'.pid.json'))['pid']
    need(specification['command']==args and specification['cpu_limit']==cpu and specification['wall_limit']==wall and specification['address_limit']==C.ADDRESS,'actual outer registered envelope')
    need(effective==dict(cpu=[cpu,cpu],address=[C.ADDRESS,C.ADDRESS],core=[0,0],sigxcpu_default=True,sigxcpu_unblocked=True),'actual child limits')
    need(row['pid']==terminal['pid']==pid and row['returncode']==0 and terminal['returncode']==0 and terminal['reaped'] and not terminal['timed_out'],'successful reaped actual child; stop/no retry')
    return row


def finish(root,r):
    r['payload_sha256']=inventory(root);C.write(root/'result.json',r)
    print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}),flush=True)
    return 0 if r['all_pass'] else 1


def build():
    head=committed();need(not PREP.exists(),'one exclusive037 preparation');need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB free disk')
    pins,old,trees=imports();PREP.mkdir();C.write(PREP/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir037-cpu-preparation/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,input_sha256=pins,official_source_trees=trees,rows=[],compiled_dependency_sha256={})
    try:
        r['effective_parent']=C.limits();os.chdir(I.BUILD)
        os.environ.update(VK_ICD_FILENAMES='/037-no-gpu.json',VK_DRIVER_FILES='/037-no-gpu.json')
        os.environ['LD_LIBRARY_PATH']=str(S.N.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))
        shutil.copyfile(CPP,PREP/CPP.name);shutil.copyfile(HLSL,PREP/HLSL.name)
        (PREP/'physical_producer.comp.glsl').write_bytes(O.producer(O.O.PT.read_bytes()))
        shutil.copyfile(OLD/'integrated_producer.spv',PREP/'original_producer.spv')
        command=list(next(x['command'] for x in old['rows'] if x['label']=='host-compile'))
        for flag,value in (('-c',PREP/CPP.name),('-o',PREP/'host.o'),('-MT',PREP/'host.o'),('-MF',PREP/'host.d')):command[command.index(flag)+1]=str(value)
        rows=[('host-compile',command)]
        command=list(next(x['command'] for x in old['rows'] if x['label']=='host-link'))
        command=[str(PREP/'host.o') if x==str(OLD/'host.o') else '-Wl,--dependency-file='+str(PREP/'link.d') if x.startswith('-Wl,--dependency-file=') else x for x in command]
        command[command.index('-o')+1]=str(PREP/'physical-gpu');rows.append(('host-link',command))
        rows.extend([('producer-compile',[I.GLSLANG,'-V','--target-env','vulkan1.3',PREP/'physical_producer.comp.glsl','-o',PREP/'physical_producer.spv']),('producer-validate',[I.VAL,'--target-env','vulkan1.3',PREP/'physical_producer.spv']),('producer-disassemble',[I.VAL.parent/'spirv-dis',PREP/'physical_producer.spv','-o',PREP/'physical_producer.spvasm'])])
        for name,packed in (('make',0),('load',1)):
            stem='physical_'+name
            args=[S.N.DXC,PREP/HLSL.name,'-T','cs_6_5','-E','main','-spirv','-fspv-target-env=vulkan1.3','-fvk-use-dx-layout','-Od','-WX','-D',f'PACKED={packed}','-I',S.LIB/'Include']
            rows.extend([(name+'-dependencies',args+['-Fo',PREP/(stem+'.spv'),'-MD','-MF',PREP/(stem+'.shader.d')]),(name+'-compile',args+['-Fo',PREP/(stem+'.spv')]),(name+'-validate',[I.VAL,'--target-env','vulkan1.3',PREP/(stem+'.spv')]),(name+'-disassemble',[I.VAL.parent/'spirv-dis',PREP/(stem+'.spv'),'-o',PREP/(stem+'.spvasm')])])
        rows.append(('new-python-contracts',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_gpu_bridge.py','-v']))
        for cell,depth in M.TARGETS:
            state=source_state(cell,depth,pins);rows.append((f'cpu-{cell.lower()}-b{depth}',[PREP/'physical-gpu','--cpu-check','--state',state,'--out',PREP/f'cpu-{cell.lower()}-b{depth}','--vertices',depth,'--shaders',PREP]))
        for label,args in rows:
            print('037',label,'START',flush=True);r['rows'].append(dict(label=label,process=guard(args,PREP,label)));print('037',label,'PASS',flush=True)
        for name in ('make','load'):
            asm=(PREP/f'physical_{name}.spvasm').read_text();need('OpRayQueryInitializeKHR' in asm and 'OpRayQueryProceedKHR' in asm,'actual compiled real BVH visibility')
            need('ArrayStride 128' in asm and 'ArrayStride 32' in asm and 'ArrayStride 16' in asm,'actual candidate/packed/output ABI')
            dependencies=(PREP/f'physical_{name}.shader.d').read_text();need('Reservoir.hlsli' in dependencies and 'TypePacking.hlsli' in dependencies,'actual official SDK dependencies')
        for p in (PREP/'host.d',):
            for name in shlex.split(p.read_text().replace('\\\n',' '))[1:]:
                file=Path(name);file=file if file.is_absolute() else I.BUILD/file
                if file.is_file():r['compiled_dependency_sha256'][str(file)]=sha(file)
        need(sha(PREP/'original_producer.spv')==old['payload_sha256']['integrated_producer.spv'],'original022 producer identity')
        for cell,depth in M.TARGETS:
            j=read(PREP/f'cpu-{cell.lower()}-b{depth}/complete.json');need(j['complete'] and not j['gpu_initialized'] and j['vertices']==depth,'actual unusable-ICD native input check')
        rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_GPU_BRIDGE_PREPARATION_PASS',new_python_contracts=8,new_native_compilations=1,new_shader_compilations=3,native_cpu_input_checks=6,old_successful_tests_reexecuted=False)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return finish(PREP,r)


def case_root(cell,depth):
    need((cell,depth) in M.TARGETS,'registered case');return BASE/f'm001-restir037-{cell.lower()}-b{depth}-v1'


def native_command(root,state,depth):return [str(PREP/'physical-gpu'),'--gpu','--state',str(state),'--out',str(root/'capture'),'--vertices',str(depth),'--shaders',str(PREP)]


def audit_worker(root,capture,depth):
    expected=dict(cpu=[1200,1200],address=[C.ADDRESS,C.ADDRESS],core=[0,0],sigxcpu_default=True,sigxcpu_unblocked=True)
    need(C.state()==expected,'numeric worker actual inherited envelope');need(not root.exists(),'exclusive numeric worker');root.mkdir()
    C.write(root/'effective-worker.json',dict(pid=os.getpid(),effective=C.state()))
    r=dict(schema='m001-restir037-numeric-worker/1',source_commit=committed(),complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',pid=os.getpid(),rows=[],effective_worker=expected)
    try:
        data=(capture/'geometry-state.bin').read_bytes();count=int(np.frombuffer(data,'<u4',1,4)[0]);need(len(data)==8+52*count,'geometry ABI')
        geometry=np.frombuffer(data,np.dtype([('vertices','<f4',(3,3)),('metadata','<u4',4)]),offset=8)
        triangles=geometry['vertices'];metadata=geometry['metadata']
        for index,seed in enumerate(M.SEEDS):
            folder=capture/f'seed-{index}'
            load=lambda name,dtype,shape:np.fromfile(folder/name,dtype).reshape(shape)
            original=load('original.f32','<f4',(57600,4));observed=load('observed.f32','<f4',(57600,4))
            w=load('witnesses.bin',M.WITNESS,(57600,depth));c=load('candidates.bin',M.CANDIDATE,(57600,));packed=load('reservoirs.bin',M.D.PACKED,(57600,));output=load('sdk-output.f32','<f4',(57600,6,4))
            args=[load(name,dtype,shape) for name,dtype,shape in [('original-hits.u32','<u4',(57600,8)),('observed-hits.u32','<u4',(57600,8)),('original-source.f32','<f4',(57600,)),('observed-source.f32','<f4',(57600,))]]
            arrays,summary=M.audit(original,observed,*args,w,c,packed,output,triangles,(folder/'params.bin').read_bytes(),seed,metadata)
            with (root/f'seed-{index}-full-errors.npz').open('xb') as f:np.savez_compressed(f,**arrays)
            r['rows'].append(dict(seed=seed,all_pass=True,**summary));print('037 full pixel/vertex/SDK audit seed',index,'PASS',flush=True)
        need(C.state()==expected,'numeric profile unchanged');r.update(complete=True,all_pass=True,classification='PHYSICAL_GPU_BRIDGE_NUMERIC_PASS')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return finish(root,r)


def native_audit(capture,depth,state):
    j=read(capture/'complete.json');need(j['complete'] and j['gpu_initialized'] and j['units']==7200 and j['vertices']==depth and j['paths_per_role']==230400 and j['roles']==2,'complete native path work')
    need(not j['quality_admitted'] and not j['accepted_timing'] and j['completed_images_read_back']==4 and all(j[k]==0 for k in ('input_images_uploaded','input_candidates_uploaded','intermediate_readbacks')),'actual residency/admission boundary')
    for name in ('geometry-state.bin','frame-state.bin'):need((capture/name).read_bytes()==(state/name).read_bytes(),'exact original scene/frame')
    for path in capture.rglob('*.guard'):need(path.read_bytes()==bytes([0xa7])*256,'all trailing guard bytes')
    need(len(list(capture.rglob('*.guard')))==44,'all four images/all11guards')
    ledger=read(capture/'allocation-ledger.json');need(ledger['teardown_zero'] and ledger['device_contexts']==1 and ledger['live_bytes_at_teardown']==0,'actual single-context zero ownership')
    live={};peak=0;live_bytes=0;allocations=[]
    for index,e in enumerate(ledger['events']):
        need(e['sequence']==index and e['device_context']==1 and e['bytes']>0,'actual owned event')
        key=e['allocation_id']
        if e['action']=='allocate':need(key not in live,'unique allocation');live[key]=e;live_bytes+=e['bytes'];allocations.append(e)
        else:
            need(e['action']=='free' and key in live,'matching free');old=live.pop(key)
            need(all(old[k]==e[k] for k in ('bytes','buffer_usage','memory_type','requested_properties','device_context')),'matching complete allocation identity');live_bytes-=e['bytes']
        need(live_bytes==e['live_bytes'],'actual live bytes');peak=max(peak,live_bytes)
    need(not live and live_bytes==0 and peak==ledger['true_peak_owned_bytes']==j['aggregate_reserved_peak'] and peak<=8*1024**3 and j['aggregate_reserved_at_teardown']==0,'true peak/teardown/cap')
    sizes=[16*57600,32*57600,4*57600,16*57600,32*57600,4*57600,80*57600*depth,128*57600,32*57600,96*57600,128]
    pipeline=[e for e in allocations if e['requested_properties']==6 and e['buffer_usage'] in (16,32)][-11:]
    need(len(pipeline)==11 and [e['buffer_usage'] for e in pipeline]==[32]*10+[16] and all(e['bytes']>=size+256 for e,size in zip(pipeline,sizes)),'all pipeline allocations plus guards')
    need(any(e['buffer_usage']&0x100000 for e in allocations) and any(e['buffer_usage']&0x20000 for e in allocations),'AS/scratch allocation coverage')
    device=read(capture/'device.json');need(device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and device['vendor_id']==4098 and device['device_id']==5510,'same qualified022 GPU identity')
    bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];need(1<=bits<=64 and np.isfinite(period) and period>0,'actual timestamp precision')
    events=[json.loads(line) for line in (capture/'dispatches.jsonl').read_text().splitlines()];need(len(events)==14400,'complete journal')
    sums=np.zeros(4);maximum=0.
    for unit,(begin,end) in enumerate(zip(events[::2],events[1::2])):
        seed=unit//1800;stage=(unit%1800)//450;start=(unit%450)*128
        need(begin==dict(event='begin',unit=unit,seed_index=seed,stage=stage,start=start,count=128) and end['event']=='complete' and end['unit']==unit,'all exact dispatch boundaries')
        us=((end['timestamp_end']-end['timestamp_begin'])&((1<<bits)-1))*period/1000
        need(0<=us<=250000 and np.isclose(us,end['gpu_us_diagnostic'],rtol=1e-12,atol=1e-12),'actual unit timestamp limit');sums[seed]+=us;maximum=max(maximum,us)
    for seed in range(4):
        envelope=read(capture/f'envelope-seed-{seed}.json');us=((envelope['timestamp_end']-envelope['timestamp_begin'])&((1<<bits)-1))*period/1000
        need(not envelope['accepted_timing'] and sums[seed]<=us<=180e6 and np.isclose(us,envelope['gpu_us_including_fences_pauses'],rtol=1e-12),'full GPU fence/pause envelope')
    need(np.isclose(sum(sums),j['active_gpu_us_diagnostic'],rtol=1e-12,atol=1e-7),'all active units charged')
    return dict(true_peak_owned_bytes=peak,allocation_pairs=len(allocations),teardown_zero=True,all_owned_as_scratch_staging_pipeline=True,driver_private_and_cpu_excluded=True,completed_units=7200,maximum_unit_gpu_us_diagnostic=maximum,device=device,accepted_timing=False)


def case(cell,depth):
    head=committed();root=case_root(cell,depth);need(not root.exists(),'one exclusive GPU case, no retry')
    pins={str(p):sha(p) for p in OWN};prep=pin_archive(PREP/'result.json',pins);need(prep['all_pass'] and not prep['gpu_executed'],'CPU preparation before GPU')
    for c,b in M.TARGETS[:M.TARGETS.index((cell,depth))]:
        previous=pin_archive(case_root(c,b)/'result.json',pins);need(previous['classification']=='ON_DEVICE_PHYSICAL_CANDIDATE_BRIDGE_CASE_PASS','previous full audit PASS')
    state=source_state(cell,depth,pins);need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB free disk')
    # Original quiet gate checks desktop/load and disallows other research jobs.
    import integrated_pt_process as Q
    Q.quiet();root.mkdir();args=native_command(root,state,depth)
    C.write(root/'inputs-before.json',dict(source_commit=head,input_sha256=pins,command=args,gpu_processes_authorized=1))
    r=dict(schema='m001-restir037-physical-gpu-case/1',source_commit=head,cell=cell,depth=depth,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',input_sha256=pins,gpu_executed=False)
    try:
        r['effective_parent']=C.limits();r['gpu_executed']=True;r['native_process']=guard(args,root,'native');r['native_audit']=native_audit(root/'capture',depth,state)
        worker=[sys.executable,Path(__file__).resolve(),'audit-worker','--root',root/'audit','--capture',root/'capture','--depth',depth]
        r['numeric_process']=guard(worker,root,'numeric',1200,1800);a=read(root/'audit/result.json')
        need(a['all_pass'] and a['pid']==r['numeric_process']['pid'] and len(a['rows'])==4,'actual supervised full numeric audit')
        rehash(pins);r.update(complete=True,all_pass=True,classification='ON_DEVICE_PHYSICAL_CANDIDATE_BRIDGE_CASE_PASS',numeric_audit=a,quality_admitted=False,accepted_timing=False)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return finish(root,r)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('build')
    p=sub.add_parser('case');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',type=int,choices=[2,8],required=True)
    p=sub.add_parser('audit-worker');p.add_argument('--root',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--depth',type=int,choices=[2,8],required=True)
    args=parser.parse_args()
    if args.mode=='build':sys.exit(build())
    elif args.mode=='case':sys.exit(case(args.cell,args.depth))
    else:sys.exit(audit_worker(args.root,args.capture,args.depth))

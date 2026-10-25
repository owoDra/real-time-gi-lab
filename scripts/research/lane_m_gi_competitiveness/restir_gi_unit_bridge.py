#!/usr/bin/env python3
"""041 supervised frozen codec diagnosis and fixed-unit physical GPU bridge."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import restir_gi_local_bridge as G
import restir_gi_unit_codec as U
import restir_gi_unit_model as M
ROOT,BASE,C=G.ROOT,G.BASE,G.C
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/041-sdk-radiance-unit-range-correction.md'
ADDENDUM=PROTOCOL.with_name('041a-exact-sdk-black-bin-addendum.md')
OWN=[PROTOCOL,ADDENDUM,Path(__file__).resolve(),Path(U.__file__),Path(M.__file__),Path(__file__).with_name('test_restir_gi_unit_codec.py')]
OLD=G.PREP;PREP=BASE/'m001-restir041-cpu-build-v1';FROZEN=G.case_root('H02',2)
ORIGINAL_COMMITTED=G.committed;ORIGINAL_SOURCE_STATE=G.source_state;ORIGINAL_FINISH=G.finish


def committed():
    head=ORIGINAL_COMMITTED();subprocess.run(['git','merge-base','--is-ancestor','6f379d55',head],cwd=ROOT,check=True)
    for p in OWN:G.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'commit041 before use')
    for p in G.OWN:G.need(subprocess.check_output(['git','show','cc21fd5b:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'all original040 source unchanged')
    return head


def source_state(cell,depth,pins):
    pins.update({str(p):G.sha(p) for p in OWN});return ORIGINAL_SOURCE_STATE(cell,depth,pins)


def finish(root,r):
    if 'schema' in r:r['schema']=r['schema'].replace('m001-restir040-','m001-restir041-')
    r.update(study='041',original_physical_source_commit='cc21fd5b',preregistration_commit='7eb7af4f',exact_black_bin_addendum_commit='6f379d55',sdk_radiance_unit=64,old040_still_stopped=True)
    return ORIGINAL_FINISH(root,r)


def case_root(cell,depth):
    G.need((cell,depth) in M.TARGETS,'registered041 case');return BASE/f'm001-restir041-{cell.lower()}-b{depth}-v1'


G.committed=committed;G.source_state=source_state;G.finish=finish;G.PREP=PREP;G.case_root=case_root;G.M=M


def imports():
    pins={str(p):G.sha(p) for p in [*OWN,*G.OWN,Path(C.__file__),Path(sys.executable)]};old=G.pin_archive(OLD/'result.json',pins)
    official,trees=G.S.source_pins();pins.update(official)
    p=ROOT/'research/lanes/lane-m-gi-competitiveness/results/237-restir-gi-local-candidates-first-three-conditions.json'
    G.need(subprocess.check_output(['git','show','1522f198:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'immutable040 stop publication');pub=G.read(p);pins[str(p)]=G.sha(p)
    G.need(pub['gpu_conditions_admitted']==2 and pub['gpu_conditions_failed']==1 and pub['gpu_conditions_not_run']==3,'preserve original040 decisions')
    for row in pub['records']:
        path=Path(row['native_receipt']);j=G.read(path);G.need(G.sha(path)==row['native_receipt_sha256'] and G.inventory(path.parent)==j['payload_sha256'],'exact040 complete native artifacts')
        G.rehash(j['input_sha256']);pins.update(j['input_sha256']);pins[str(path)]=G.sha(path);pins.update({str(path.parent/k):v for k,v in j['payload_sha256'].items()})
    G.rehash(pins);return pins,old


def diagnosis():
    wanted=dict(cpu=[1200,1200],address=[C.ADDRESS,C.ADDRESS],core=[0,0],sigxcpu_default=True,sigxcpu_unblocked=True)
    G.need(C.state()==wanted,'actual numeric profile');root=PREP/'diagnosis';G.need(not root.exists(),'exclusive diagnosis');root.mkdir()
    C.write(root/'effective-before.json',dict(pid=os.getpid(),effective=C.state()));pins,old=imports()
    r=dict(schema='m001-restir041-targeted-codec-worker/1',source_commit=committed(),complete=False,all_pass=False,pid=os.getpid(),effective_worker=wanted,input_sha256=pins,rows=[],gpu_executed=False,full040_audit_reexecuted=False)
    try:
        unexplained=0;totalbad=0;newbad=0
        for seed in range(4):
            folder=FROZEN/'capture'/f'seed-{seed}';c=np.fromfile(folder/'candidates.bin',M.CANDIDATE);packed=np.fromfile(folder/'reservoirs.bin',M.D.PACKED);local=np.fromfile(folder/'local-endpoints.f32','<f4').reshape(57600,4)
            rgb=c['radiance_trial'][:,:3];status=M.bits(c['normal_status'][:,3]);hit=status==2
            G.need(c.shape==packed.shape==(57600,) and np.isfinite(rgb).all() and (rgb>=0).all() and np.array_equal(rgb[:,0],rgb[:,1]) and np.array_equal(rgb[:,0],rgb[:,2]),'complete finite original grey radiance')
            G.need((rgb<=U.UPPER+3e-6).all() and (packed['misc']==hit.astype(M.U)).all() and (packed['unused']==0).all() and np.array_equal(packed['position'],local[:,:3]),'targeted range/position/M/reserved integrity')
            weight=np.zeros(57600);weight[hit]=1/c['origin_pdf'][hit,3].astype(float)
            G.need(M.near(packed['weight'],weight,2e-5,2e-6).all(),'targeted weight integrity')
            G.need(M.near(M.decode_normal(packed['normal'])[hit],c['endpoint_normal'][hit,:3]).all() and (packed['normal'][~hit]==0).all(),'targeted normal integrity')
            actual=M.D.decode(packed['radiance']);bad,why=U.underflow_failures(rgb,packed['radiance']);predicted_codes=U.encode(rgb*U.UNIT);predicted=U.decode(predicted_codes)
            newfail=(np.abs(predicted.astype(float)-rgb)>U.budget(rgb)).any(axis=1)
            unexplained+=int((bad&~why).sum());totalbad+=int(bad.sum());newbad+=int(newfail.sum())
            with (root/f'seed-{seed}-full-codec-fields.npz').open('xb') as f:np.savez_compressed(f,original_rgb=rgb,actual_codes=packed['radiance'],actual_decoded=actual,actual_error=actual.astype(float)-rgb,actual_failed=bad,underflow_explained=why,scaled_codes=predicted_codes,scaled_decoded=predicted,scaled_error=predicted.astype(float)-rgb,scaled_failed=newfail)
            failures=[dict(pixel=int(i),source=rgb[i].tolist(),code=int(packed['radiance'][i]),decoded=actual[i].tolist(),absolute_error=np.abs(actual[i].astype(float)-rgb[i]).tolist(),underflow_explained=bool(why[i])) for i in np.flatnonzero(bad)]
            C.write(root/f'seed-{seed}-every-codec-failure.json',failures)
            r['rows'].append(dict(seed=M.SEEDS[seed],pixels=57600,actual_failed_pixels=int(bad.sum()),actual_unexplained_pixels=int((bad&~why).sum()),scaled_predicted_failed_pixels=int(newfail.sum()),maximum_original_rgb=float(rgb.max()),actual_failed_max_rgb=float(rgb[bad].max()) if bad.any() else 0,maximum_scaled_absolute_error=float(np.max(np.abs(predicted.astype(float)-rgb)))))
            print('041 frozen seed',seed,'actual_bad',int(bad.sum()),'unexplained',int((bad&~why).sum()),'scaled_bad',int(newfail.sum()),flush=True)
        grid=U.critical_grid();rgb=np.repeat(grid[:,None],3,axis=1);codes=U.encode(rgb*U.UNIT);decoded=U.decode(codes);error=np.abs(decoded.astype(float)-rgb);budget=U.budget(rgb);failed=(error>budget).any(axis=1)
        G.need(np.isfinite(decoded).all() and np.isfinite(error).all(),'finite complete critical grid')
        with (root/'complete-neutral-grey-critical-grid.npz').open('xb') as f:np.savez_compressed(f,original=rgb,encoded=codes,decoded=decoded,absolute_error=error,budget=budget,failed=failed)
        r.update(actual_failed_pixels=totalbad,unexplained_failures=unexplained,scaled_frozen_failed_pixels=newbad,critical_grid_samples=len(grid),critical_grid_failed_samples=int(failed.sum()),critical_grid_max_budget_ratio=float(np.max(error/budget)),exact_black_bound=U.BLACK_BOUND,scaled_black_bound=U.BLACK_BOUND/64,unit=64,upper_scaled_radiance=U.UPPER*64)
        G.need(totalbad>0 and unexplained==0 and newbad==0 and not failed.any() and (codes>>18).max()<16383,'all frozen failures explained and fixed-unit full critical grid PASS')
        G.rehash(pins);G.need(C.state()==wanted,'numeric profile unchanged');r.update(complete=True,all_pass=True,classification='CPU_FIXED_RADIANCE_UNIT_RANGE_PASS_NO_GPU_ADMISSION')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return finish(root,r)


def build():
    head=committed();G.need(not PREP.exists() and shutil.disk_usage(BASE).free>=16*1024**3,'exclusive041/16GiB');pins,old=imports();PREP.mkdir()
    C.write(PREP/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir041-unit-preparation/1',source_commit=head,complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',gpu_executed=False,input_sha256=pins,compiled_dependency_sha256=old['compiled_dependency_sha256'],rows=[],new_host_compilations=0,new_glsl_compilations=0,old_successful_tests_reexecuted=False,native_cpu_input_checks_reexecuted=0)
    try:
        r['effective_parent']=C.limits();r['diagnosis_process']=G.guard([sys.executable,Path(__file__).resolve(),'diagnose-worker'],PREP,'diagnosis',1200,1800)
        diagnostic=G.read(PREP/'diagnosis/result.json');G.need(diagnostic['all_pass'] and diagnostic['pid']==r['diagnosis_process']['pid'],'actual supervised range qualification before compile/GPU')
        os.environ.update(VK_ICD_FILENAMES='/041-no-gpu.json',VK_DRIVER_FILES='/041-no-gpu.json');os.environ['LD_LIBRARY_PATH']=str(G.S.N.DXC.parent.parent/'lib')+':'+os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))
        for name in ('host.o','host.d','physical-gpu','physical_producer.spv','physical_producer.spvasm','physical_producer.comp.glsl','original_producer.spv'):
            shutil.copyfile(OLD/name,PREP/name);G.need(G.sha(PREP/name)==old['payload_sha256'][name],'exact040 native/GLSL reuse')
        shutil.copymode(OLD/'physical-gpu',PREP/'physical-gpu');(PREP/G.HLSL.name).write_bytes(U.shader(G.HLSL.read_bytes()))
        rows=[('new-python-contracts',[sys.executable,'-m','unittest','discover','-s',Path(__file__).parent,'-p','test_restir_gi_unit_codec.py','-v'])]
        for name,packed in (('make',0),('load',1)):
            stem='physical_'+name;args=[G.S.N.DXC,PREP/G.HLSL.name,'-T','cs_6_5','-E','main','-spirv','-fspv-target-env=vulkan1.3','-fvk-use-dx-layout','-Od','-WX','-D',f'PACKED={packed}','-I',G.S.LIB/'Include']
            rows.extend([(name+'-dependencies',args+['-Fo',PREP/(stem+'.spv'),'-MD','-MF',PREP/(stem+'.shader.d')]),(name+'-compile',args+['-Fo',PREP/(stem+'.spv')]),(name+'-validate',[G.I.VAL,'--target-env','vulkan1.3',PREP/(stem+'.spv')]),(name+'-disassemble',[G.I.VAL.parent/'spirv-dis',PREP/(stem+'.spv'),'-o',PREP/(stem+'.spvasm')])])
        for label,args in rows:
            print('041',label,'START',flush=True);r['rows'].append(dict(label=label,process=G.guard(args,PREP,label)));print('041',label,'PASS',flush=True)
        for name in ('make','load'):
            asm=(PREP/f'physical_{name}.spvasm').read_text();G.need('OpRayQueryInitializeKHR' in asm and 'ArrayStride 128' in asm and 'ArrayStride 32' in asm and 'ArrayStride 16' in asm,'compiled physical SDK visibility and ABI')
        G.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_FIXED_RADIANCE_UNIT_RANGE_PREPARATION_PASS',new_python_contracts=8,new_hlsl_compilations=2,reused_native_cpu_input_checks=6,reused040_executable_and_physical_producer=True,diagnostic=diagnostic)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    return finish(PREP,r)


def case(cell,depth):
    original=G.__file__;G.__file__=__file__
    try:return G.case(cell,depth)
    finally:G.__file__=original


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True);sub.add_parser('build');sub.add_parser('diagnose-worker')
    p=sub.add_parser('case');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',choices=[2,8],type=int,required=True)
    p=sub.add_parser('audit-worker');p.add_argument('--root',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--depth',choices=[2,8],type=int,required=True)
    args=parser.parse_args()
    if args.mode=='build':sys.exit(build())
    elif args.mode=='diagnose-worker':sys.exit(diagnosis())
    elif args.mode=='case':sys.exit(case(args.cell,args.depth))
    else:sys.exit(G.audit_worker(args.root,args.capture,args.depth))

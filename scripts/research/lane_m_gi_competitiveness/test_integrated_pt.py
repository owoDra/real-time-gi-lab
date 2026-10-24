#!/usr/bin/env python3
"""022 new CPU contracts for real integration code; no GPU initialization."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import numpy as np
import build_integrated_pt as B
import integrated_pt_overlay as O
import surface_quadratic_gpu_process as T


def run(build,out):
    commit=B.committed();out=out.resolve()
    if not out.is_relative_to(B.BASE) or out.exists():raise ValueError('022 new exclusive CPU contract output required')
    inputs={str(p):O.sha(p) for p in B.OWN};b=T.Q.pin_inventory(build,inputs)
    if not b['complete'] or not b['all_pass'] or b['gpu_executed']:raise ValueError('022 native build not qualified')
    T.F.rehash(b['input_sha256']);T.F.rehash(b['compiled_dependency_sha256']);inputs.update(b['input_sha256']);inputs.update(b['compiled_dependency_sha256'])
    out.mkdir(parents=True);rows=[]
    env={**os.environ,'VK_ICD_FILENAMES':'/m001-022-deliberately-unusable-icd.json','VK_DRIVER_FILES':'/m001-022-deliberately-unusable-icd.json','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
    def check(name,condition,**detail):
        row=dict(name=name,pass_=bool(condition),**detail);rows.append(row)
        if not condition:raise ValueError('022 CPU contract failed: '+name)
    def child(name,args,expected=0):
        p=subprocess.run(args,cwd=B.ROOT,env=env,capture_output=True,timeout=180,preexec_fn=B.limits)
        (out/(name+'.stdout.txt')).write_bytes(p.stdout);(out/(name+'.stderr.txt')).write_bytes(p.stderr)
        check(name,p.returncode==expected,command=args,returncode=p.returncode,expected_returncode=expected)
        return p
    result=dict(schema='m001-integrated022-new-cpu-contracts/1',source_commit=commit,complete=False,all_pass=False,gpu_executed=False,new_render_paths=0,new_reference_paths=0,input_sha256=inputs,rows=rows)
    try:
        for name,p,kind in (('producer',O.PT,'producer'),('context',O.CONTEXT,'context'),('hwrt',O.HWRT,'hwrt')):
            raw=p.read_bytes();actual=O.producer(raw) if kind=='producer' else O.bounded(raw,kind)
            check(name+'-private-overlay-byte-exact',actual==(Path(b['shader_directory'])/('integrated_producer.comp.glsl' if name=='producer' else 'integrated_b002_'+('vulkan' if name=='context' else 'hwrt')+'.cpp')).read_bytes())
            try:
                if kind=='producer':O.producer(raw+b'\n')
                else:O.bounded(raw+b'\n',kind)
            except ValueError:changed_rejected=True
            else:changed_rejected=False
            check(name+'-changed-original-rejected',changed_rejected)
        generated=O.producer(O.PT.read_bytes()).decode();original=O.PT.read_text()
        # The exact reversible transform plus unchanged function bodies/RNG
        # establish per-pixel sample stream invariants before device execution.
        for begin,end in (('uint mix32(', 'bool trace('),('bool blocked(', 'void main()')):
            check('unchanged-functions-'+begin.split('(')[0],generated[generated.index(begin):generated.index(end)]==original[original.index(begin):original.index(end)])
        check('unchanged-rng-and-sample-loop',original[original.index('    rng=mix32'):original.index('            vec3 wi=')]==generated[generated.index('    rng=mix32'):generated.index('            vec3 wi=')])
        check('no-original-wait-or-allocation-bypass',sum((Path(b['shader_directory'])/n).read_text().count('250000000ull') for n in ('integrated_b002_vulkan.cpp','integrated_b002_hwrt.cpp'))==3 and (Path(b['shader_directory'])/'integrated_b002_vulkan.cpp').read_text().count('m022::reserve(allocation_info.allocationSize)')==1)
        c=child('actual-scalar-and-safety-contracts',[b['contract_executable']]);scalar=json.loads(c.stdout);check('actual-new-scalar-safety-count',scalar['complete'] and scalar['actual_new_contracts']==9 and scalar['stage_comparisons']==3630 and not scalar['gpu_executed']);result['scalar_safety_contracts']=scalar
        fixture=out/'synthetic-incomplete';child('actual-incomplete-fence-path',[b['contract_executable'],'--incomplete',str(fixture)],3)
        failure=json.loads((fixture/'failure.json').read_text());check('incomplete-preserves-no-teardown-claim',failure['classification']=='INCOMPLETE_FENCE' and not failure['gpu_completion_proven'] and not failure['teardown_claim'] and (fixture/'allocation-ledger.json').is_file())
        states=[]
        for cell in ('H01','H02','H03'):
            pins,proof=T.prepare_inputs(cell,2);inputs.update(pins);state=Path(proof['primary_capture']);states.append(state)
            target=out/(cell.lower()+'-input-check');cmd=[b['executable'],'--cpu-check','--state',str(state),'--out',str(target),'--spp','16','--vertices','2','--seed','305419896'];child(cell+'-canonical-native-input',cmd)
            actual=np.fromfile(target/'camera.f32',dtype='<f4');expected=T.Q.input_arrays(proof)['camera'];expected[17]=1
            check(cell+'-camera-epsilon-exact',np.array_equal(actual,expected),actual_epsilon=float(actual[16]),expected_epsilon=float(expected[16]))
            check(cell+'-original-state-bytes',all((target/n).read_bytes()==(state/n).read_bytes() for n in ('geometry-state.bin','frame-state.bin')))
        state=states[0]
        def native(name,patch=None,options=None,gpu=False,expected=2):
            directory=state
            if patch is not None:
                directory=out/(name+'-input');directory.mkdir()
                for n in ('geometry-state.bin','frame-state.bin'):shutil.copyfile(state/n,directory/n)
                patch(directory)
            target=out/(name+'-native');args=[b['executable'],'--gpu' if gpu else '--cpu-check','--state',str(directory),'--out',str(target),'--spp','16','--vertices','2','--seed','305419896']
            if options:args=options(args)
            child(name,args,expected);check(name+'-before-vulkan-and-output',not target.exists())
        def bytes_patch(file,offset,data):
            def patch(d):
                p=d/file;raw=bytearray(p.read_bytes());raw[offset:offset+len(data)]=data;p.write_bytes(raw)
            return patch
        def number(file,offset,value,fmt='<I'):return bytes_patch(file,offset,struct.pack(fmt,value))
        for name,patch in (
            ('geometry-version',number('geometry-state.bin',0,0)),('geometry-count-zero',number('geometry-state.bin',4,0)),('geometry-count-cap',number('geometry-state.bin',4,2049)),
            ('vertex-nonfinite',number('geometry-state.bin',8,float('nan'),'<f')),('primitive-invalid',number('geometry-state.bin',44,0xffffffff)),('instance-invalid',number('geometry-state.bin',52,0xffffffff)),('two-sided-zero',number('geometry-state.bin',56,0)),
            ('duplicate-primitive',number('geometry-state.bin',96,struct.unpack_from('<I',(state/'geometry-state.bin').read_bytes(),44)[0])),
            ('frame-magic',bytes_patch('frame-state.bin',0,b'X')),('viewport-width',number('frame-state.bin',12,321)),('frame-triangle-count',number('frame-state.bin',116,0)),
            ('frame-nonfinite',number('frame-state.bin',20,float('inf'),'<f')),('camera-unit',number('frame-state.bin',68,2.,'<f')),('camera-tangent',number('frame-state.bin',48,0.,'<f')),('camera-far',number('frame-state.bin',80,-1.,'<f')),('light-scale',number('frame-state.bin',112,0.,'<f'))):native(name,patch)
        for file in ('geometry-state.bin','frame-state.bin'):
            native(file+'-truncated',lambda d,f=file:(d/f).write_bytes((d/f).read_bytes()[:-1]))
            native(file+'-missing',lambda d,f=file:(d/f).unlink())
        native('degenerate-triangle',bytes_patch('geometry-state.bin',20,(state/'geometry-state.bin').read_bytes()[8:20]))
        native('camera-nonorthogonal',bytes_patch('frame-state.bin',36,(state/'frame-state.bin').read_bytes()[68:80]))
        for key,value in (('--spp','0'),('--spp','32'),('--vertices','1'),('--vertices','4'),('--seed','0'),('--seed','-1'),('--seed','4294967296'),('--seed','305419896junk')):
            native('budget-'+key[2:]+'-'+value,options=lambda a,k=key,v=value:[v if j==a.index(k)+1 else x for j,x in enumerate(a)])
        native('unknown-option',options=lambda a:a+['--unknown','1']);native('duplicate-option',options=lambda a:a+['--spp','16']);native('missing-value',options=lambda a:a[:-1]);native('missing-required',options=lambda a:a[:-2])
        native('existing-output',options=lambda a:[str(out/'h01-input-check') if j==a.index('--out')+1 else x for j,x in enumerate(a)])
        for name,data in (('missing',None),('short',b'\x03\x02\x23\x07'),('unaligned',b'X'*21),('bad-magic',b'X'*20)):
            sd=out/('shader-'+name);sd.mkdir()
            if data is not None:
                for n in ('integrated_producer.spv','surface_quadratic_device.spv','integrated_composite.spv'):(sd/n).write_bytes(data)
            native('shader-'+name,gpu=True,options=lambda a,d=sd:a+['--shaders',str(d)])
        # Audit-only one->five transformation, not native/GPU upload.
        source=np.arange(57600,dtype='<f4').reshape(180,320)*np.float32(.0001);replica=np.repeat(source[None],5,axis=0)
        check('audit-only-one-five-indexing',all(np.array_equal(replica[j],source) for j in range(5)) and replica.nbytes==5*source.nbytes)
        T.F.rehash(inputs);result.update(all_pass=True,complete=True,total_python_contracts=len(rows),new_native_scalar_safety_contracts=scalar['actual_new_contracts'],input_hashes_reverified=True)
    except Exception as e:result.update(complete=True,all_pass=False,error=str(e));print(str(e),file=sys.stderr)
    result['payload_sha256']=B.inventory(out)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result.get(k) for k in ('all_pass','error','total_python_contracts','new_native_scalar_safety_contracts','gpu_executed')}));return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=run(a.build.resolve(),a.out);sys.exit(0 if r['all_pass'] else 2)

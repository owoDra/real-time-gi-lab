#!/usr/bin/env python3
"""023 real SDK CPU/API/guide contracts; deliberately unusable Vulkan ICD."""
import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import struct
import subprocess
import sys
import build_nrd_cpu as B

ROOT=B.ROOT; BASE=B.BASE; sha=B.sha
PRIOR='9f94c2c5af9f993354c13a6f9fb10f9091c5feaa'


def need(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(Path(path).read_text())


def check_hashes(mapping,base=None):
    for name,digest in mapping.items():
        path=Path(name) if base is None else base/name
        need(path.is_file() and sha(path)==digest,'023 changed evidence: '+str(path))


def spirv(path):
    """Read actual SPIR-V instructions, independently of SDK descriptor metadata."""
    data=Path(path).read_bytes();need(len(data)>=20 and len(data)%4==0,'023 SPIR-V size')
    words=struct.unpack('<'+'I'*(len(data)//4),data);need(words[0]==0x07230203,'023 SPIR-V magic')
    def string(a):return struct.pack('<'+'I'*len(a),*a).split(b'\0')[0].decode()
    at=5; caps=[]; extensions=[]; entries=[]; bindings={}; sets={}; local=[]
    while at<len(words):
        count=words[at]>>16;op=words[at]&65535;need(count>0 and at+count<=len(words),'023 malformed SPIR-V instruction');a=words[at+1:at+count]
        if op==17:caps.append(a[0])
        if op==10:extensions.append(string(a))
        if op==15:entries.append(dict(model=a[0],id=a[1],name=string(a[2:])))
        if op==16 and a[1]==17:local.append(list(a[2:5]))
        if op==71 and a[1]==33:bindings[a[0]]=a[2]
        if op==71 and a[1]==34:sets[a[0]]=a[2]
        at+=count
    need(at==len(words) and len(entries)==1 and len(local)==1,'023 entrypoint/local size')
    need(set(bindings)==set(sets),'023 binding without descriptor set')
    descriptors=sorted([[sets[k],v] for k,v in bindings.items()]);need(len(descriptors)==len(set(map(tuple,descriptors))),'023 duplicate binding')
    return dict(sha256=sha(path),capabilities=sorted(caps),extensions=sorted(extensions),entry=entries[0],local_size=local[0],descriptors=descriptors)


def audit_probe(out,state,camera):
    complete=read(out/'complete.json');config=read(out/'instance.json');common=read(out/'common.json')
    need(complete['complete'] and complete['gpu_initialized'] is False and complete['api_frames']==65,'023 incomplete API run')
    need(config['version']==[4,18,0] and config['normal_encoding']==2 and config['roughness_encoding']==1,'023 ABI/encodings')
    need(config['spaces']==dict(constants_samplers=1,resources=0) and config['offsets']==dict(s=0,b=2,u=3,t=20),'023 binding offsets/spaces')
    need(config['constant_register']==0 and config['samplers']==[0,1],'023 constant/sampler registers')
    need(config['default_settings']==dict(diffuse_history=30,fast_history=6,atrous_iterations=5,diffuse_prepass_radius=30,antifirefly=False,checkerboard=0,hit_distance_reconstruction=0),'023 changed defaults')
    need([p['downsample'] for p in config['pools']['permanent']]==[1]*6 and [p['downsample'] for p in config['pools']['transient']]==[1,1,16,1],'023 upstream pool contract')
    for n in ('geometry-state.bin','frame-state.bin'):need((state/n).read_bytes()==(out/n).read_bytes(),'023 copied physical input differs')
    need((out/'camera.f32').read_bytes()==camera.read_bytes(),'023 original camera differs')
    c=struct.unpack('<20f',camera.read_bytes());v=common['world_to_view'];p=common['view_to_clip'];projection_checks=0
    need(common['world_normals'] and common['static_motion_zero'] and abs(common['time_delta_ms']-1000/60)<1e-5 and common['denoising_range']==c[7],'023 common guide contract')
    for y in (0,89,179):
        for x in (0,159,319):
            nx=2*(x+.5)/320-1;ny=1-2*(y+.5)/180;z=7
            world=[c[k]+z*(c[4+k]+nx*c[11]*c[8+k]+ny*c[15]*c[12+k]) for k in range(3)]+[1]
            view=[sum(v[k*4+r]*world[k] for k in range(4)) for r in range(4)]
            clip=[sum(p[k*4+r]*view[k] for k in range(4)) for r in range(4)]
            need(abs(clip[0]/clip[3]-nx)<2e-6 and abs(clip[1]/clip[3]-ny)<2e-6 and abs(view[2]-z)<2e-6,'023 independent physical projection')
            projection_checks+=1
    pipelines=config['pipelines'];need(len(pipelines)==complete['pipelines'] and len(pipelines)>1,'023 pipeline exports')
    reflections=[]
    for j,pipe in enumerate(pipelines):
        need(pipe['index']==j,'023 pipeline index');r=spirv(out/'pipelines'/f'{j}.spv')
        need(r['entry']['model']==5 and r['entry']['name']==config['entrypoint'] and r['local_size'][2]==1,'023 pipeline entry')
        allowed={(1,config['offsets']['s']+k) for k in range(len(config['samplers']))}
        if pipe['constant_data']:allowed.add((1,config['offsets']['b']))
        counts=collections.Counter()
        for rng in pipe['ranges']:
            need(rng['type'] in (0,1) and rng['count']>0,'023 resource range')
            for k in range(rng['count']):allowed.add((0,config['offsets']['t' if rng['type']==0 else 'u']+counts[rng['type']]+k))
            counts[rng['type']]+=rng['count']
        need(set(map(tuple,r['descriptors']))<=allowed,'023 SPIR-V binding outside actual SDK layout')
        need(any(a==0 for a,b in r['descriptors']),'023 pipeline missing resource bindings')
        reflections.append(r)
    frames=[json.loads(line) for line in (out/'dispatches.jsonl').read_text().splitlines()];need(len(frames)==65,'023 frame journal')
    users=set();dispatches=0;constant_bytes=0;grid_checks=0;history_frames=0;transient_cycles=0
    for i,frame in enumerate(frames):
        need(frame['iteration']==i and frame['frame']==(0 if i==64 else i) and frame['clear']==(i in (0,64)),'023 frame/reset sequence')
        prev=None;reads=set();writes=set();atrous=[]
        for d in frame['dispatches']:
            dispatches+=1;pipe=pipelines[d['pipeline']];r=reflections[d['pipeline']]
            need(d['identifier']==23 and len(d['grid'])==2 and all(0<n<=4096 for n in d['grid']),'023 dispatch index/grid')
            raw=(out/'constants'/d['constant_file']).read_bytes();need(len(raw)==d['constant_bytes']<=config['constant_max_bytes'] and (len(raw)>0)==pipe['constant_data'],'023 constants range')
            if d['matches_previous']:need(prev==raw,'023 constant reuse differs')
            prev=raw;constant_bytes+=len(raw)
            expected=[rng['type'] for rng in pipe['ranges'] for _ in range(rng['count'])]
            need([a['descriptor_type'] for a in d['resources']]==expected,'023 dispatch resource descriptors')
            for a in d['resources']:
                if a['name'] in ('PERMANENT_POOL','TRANSIENT_POOL'):
                    pool=config['pools']['permanent' if a['name']=='PERMANENT_POOL' else 'transient']
                    need(0<=a['pool_index']<len(pool),'023 resource pool index')
                    if a['name']=='PERMANENT_POOL':(reads if a['descriptor_type']==0 else writes).add(a['pool_index'])
                else:users.add(a['name'])
            # Upstream all selected RELAX dispatches use downsample1. Clear
            # uses its actual output dimensions, including 16x tile pool.
            w,h=320,180
            if d['name'].startswith('Clear ('):
                a=d['resources'][0]
                if a['name']=='TRANSIENT_POOL':
                    down=config['pools']['transient'][a['pool_index']]['downsample'];w=(w+down-1)//down;h=(h+down-1)//down
            gx,gy,_=r['local_size']
            if d['name'].endswith(' - Classify tiles'):
                # Official shader has 8x4 threads, each covering 2x4 pixels.
                # SDK's ClassifyTilesGroupX/Y is the 16x16 coverage, rather
                # than SPIR-V LocalSize. No shader or dispatch is changed.
                need((gx,gy)==(8,4),'023 changed tile classifier thread size');gx*=2;gy*=4
            need(d['grid']==[(w+gx-1)//gx,(h+gy-1)//gy],'023 independent grid/texture dimensions');grid_checks+=1
            if ' - A-trous' in d['name']:
                atrous.append(d)
        need(reads==set(range(6)) and writes==set(range(6)),'023 six actual permanent histories read/write')
        need(len(atrous)==5,'023 default five a-trous iterations')
        # Consecutive middle passes consume the exact preceding transient
        # illumination write; terminal output is the user diffuse texture.
        for a,b in zip(atrous,atrous[1:]):
            out_slots={v['pool_index'] for v in a['resources'] if v['name']=='TRANSIENT_POOL' and v['descriptor_type']==1}
            in_slots={v['pool_index'] for v in b['resources'] if v['name']=='TRANSIENT_POOL' and v['descriptor_type']==0}
            need(out_slots and out_slots<=in_slots,'023 broken transient illumination dependency');transient_cycles+=1
        history_frames+=1
    need({'IN_MV','IN_NORMAL_ROUGHNESS','IN_VIEWZ','IN_DIFF_RADIANCE_HITDIST','OUT_DIFF_RADIANCE_HITDIST'}<=users,'023 required guide resources')
    def cold(frame):
        return [(dict((k,v) for k,v in d.items() if k!='constant_file'),(out/'constants'/d['constant_file']).read_bytes()) for d in frame['dispatches']]
    need(cold(frames[0])==cold(frames[64]),'023 reset differs from cold dispatch/constants')
    need(dispatches==complete['dispatches'],'023 total dispatches')
    return dict(projection_checks=projection_checks,dispatches=dispatches,grid_checks=grid_checks,constant_bytes=constant_bytes,history_frames=history_frames,transient_dependencies=transient_cycles,reset_to_cold_exact=True,inter_frame_pool_index_swaps=0,required_user_resources=sorted(users),reflections=reflections)


def run(build,work,reuse):
    commit=B.committed();build=build.resolve();work=work.resolve();b=read(build/'result.json')
    need(b['complete'] and b['all_pass'] and b['gpu_executed'] is False,'023 actual complete build required')
    for name,digest in b['input_sha256'].items():
        if Path(name)==Path(__file__).resolve():
            original=subprocess.check_output(['git','show',b['source_commit']+':'+str(Path(name).relative_to(ROOT))],cwd=ROOT)
            need(hashlib.sha256(original).hexdigest()==digest,'023 original build-time test bytes changed')
        else:check_hashes({name:digest})
    check_hashes(b['compiled_dependency_sha256']);check_hashes(b['payload_sha256'],build)
    need(sha(reuse)=='98e8419b078ca5ffe43bacfa44f2e230b9983def40a7cd5a7030cf150dce4397','023 pinned first audit failure required')
    first=read(reuse);check_hashes(first['payload_sha256'],reuse.parent)
    need(first['error']=='ValueError: 023 independent grid/texture dimensions' and first['build_receipt_sha256']==sha(build/'result.json'),'023 identified audit-only repair')
    need(work.is_relative_to(BASE) and not work.exists(),'023 exclusive contract output');work.mkdir(parents=True)
    result=dict(schema='m001-nrd023-real-sdk-cpu-contracts/1',source_commit=commit,complete=False,all_pass=False,gpu_executed=False,sdk_api_executed=False,build_receipt=str(build/'result.json'),build_receipt_sha256=sha(build/'result.json'),rows=[],probes=[],input_sha256={str(p):sha(p) for p in B.OWN})
    result['input_sha256'][str(reuse)]=sha(reuse);result['preserved_first_failure']=str(reuse)
    env={**os.environ,'VK_ICD_FILENAMES':'/nonexistent/m023-no-gpu.json','VK_DRIVER_FILES':'/nonexistent/m023-no-gpu.json','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','LD_LIBRARY_PATH':os.environ.get('NIX_LD_LIBRARY_PATH',os.environ.get('LD_LIBRARY_PATH',''))}
    def command(label,args,expect=0):
        if label in ('cpp-scalar-contract','native-undefined-symbols','h01-real-sdk'):
            old=next(r for r in first['rows'] if r['label']==label);need(old['pass_'] and old['returncode']==expect,'023 reused actual CPU command not successful')
            row={**old,'reused_from_receipt':str(reuse),'executed_again':False};result['rows'].append(row)
            return subprocess.CompletedProcess(old['command'],old['returncode'],(reuse.parent/(label+'.stdout.txt')).read_bytes(),(reuse.parent/(label+'.stderr.txt')).read_bytes())
        def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
        p=subprocess.run(list(map(str,args)),env=env,capture_output=True,timeout=180,preexec_fn=limits)
        for key,value in (('stdout',p.stdout),('stderr',p.stderr)):(work/(label+'.'+key+'.txt')).write_bytes(value)
        row=dict(label=label,command=list(map(str,args)),returncode=p.returncode,expected_returncode=expect,pass_=p.returncode==expect);result['rows'].append(row);need(row['pass_'],'023 actual command failed: '+label);return p
    try:
        p=command('cpp-scalar-contract',[build/'nrd-guide-contract']);cpp=json.loads(p.stdout);need(cpp['complete'] and cpp['actual_cpp_checks']==38 and cpp['gpu_initialized'] is False,'023 C++ scalar checks');result['cpp_checks']=cpp['actual_cpp_checks']
        # No link to Vulkan or unresolved graphics API in the executable.
        p=command('native-undefined-symbols',['nm','-u',build/'nrd-api-probe']);need(not any(line.split()[-1].startswith(('vkCreate','vkGet','vkCmd','vkQueue','vkAllocate')) for line in p.stdout.decode().splitlines() if line.split()),'023 graphics symbol in CPU probe')
        raw=B.S.O.PT.read_bytes();generated=B.S.producer(raw);need(generated==(build/'nrd_producer.comp.glsl').read_bytes(),'023 actual shader/source mismatch')
        old=B.S.O.producer(raw).decode();new=generated.decode()
        for token in ('rng=mix32','cosine_direction(', 'trace_closest(', 'direct_light('):need(new.count(token)==old.count(token),'023 additional RNG/ray/sample operation')
        try:B.S.producer(raw+b'\n')
        except ValueError:pass
        else:raise ValueError('023 changed historical PT accepted')
        pack=spirv(build/'nrd_pack_guides.spv');need(pack['entry']['name']=='main' and pack['local_size']==[8,8,1] and pack['descriptors']==[[0,k] for k in range(9)],'023 actual packing shader ABI');result['packing_reflection']=pack
        publication=ROOT/'research/lanes/lane-m-gi-competitiveness/results/130-integrated-pt-reconstruction-six-targets-raw-replay.json'
        need(publication.read_bytes()==subprocess.check_output(['git','show',PRIOR+':'+str(publication.relative_to(ROOT))],cwd=ROOT),'023 changed published022receipt')
        result['input_sha256'][str(publication)]=sha(publication);published=read(publication);states=[]
        for cell in ('H01','H02','H03'):
            record=next(r for r in published['records'] if r['cell']==cell and r['depth']==2);receipt=Path(record['native_receipt']);need(sha(receipt)==record['native_receipt_sha256'],'023 changed022native receipt')
            prior=read(receipt);check_hashes(prior['payload_sha256'],receipt.parent);plan=receipt.parent/'plan.json';need(sha(plan)==prior['plan_sha256'],'023 changed022plan')
            state=Path(read(plan)['proof']['primary_capture']);camera=receipt.parent/'capture/camera.f32';states.append(state)
            for p in (receipt,plan,camera,state/'geometry-state.bin',state/'frame-state.bin'):result['input_sha256'][str(p)]=sha(p)
            out=(reuse.parent if cell=='H01' else work)/cell.lower();command(cell.lower()+'-real-sdk',[build/'nrd-api-probe','--cpu-inspect','--state',state,'--out',out]);result['sdk_api_executed']=True
            audit=audit_probe(out,state,camera);result['probes'].append(dict(cell=cell,directory=str(out),audit=audit));print(cell,'actual SDK audit PASS',audit['dispatches'],flush=True)
        reflections=result['probes'][0]['audit']['reflections']
        need(all(p['audit']['reflections']==reflections for p in result['probes']),'023 static-scene pipeline bytes differ')
        # Every exported pipeline is independently validated once; the other
        # two scenes prove byte identity, rather than repeat identical binaries.
        for i in range(len(reflections)):command('sdk-spv-'+str(i),[B.VAL,'--target-env','vulkan1.2',reuse.parent/'h01/pipelines'/f'{i}.spv'])
        result['validated_pipelines']=len(reflections);result['identical_pipeline_exports_reused']=2*len(reflections)
        exe=build/'nrd-api-probe';state=states[0];original_state={n:(state/n).read_bytes() for n in ('geometry-state.bin','frame-state.bin')}
        command('reject-gpu-mode',[exe,'--gpu-inspect','--state',state,'--out',work/'forbidden-gpu'],2);need(not (work/'forbidden-gpu').exists(),'023 unknown mode created output')
        command('reject-absent-arguments',[exe],2)
        before=B.inventory(reuse.parent/'h01');command('reject-overwrite',[exe,'--cpu-inspect','--state',state,'--out',reuse.parent/'h01'],2);need(B.inventory(reuse.parent/'h01')==before,'023 existing output changed')
        for label,offset,value in (('near-zero',32,0.),('far-before-near',80,.0001),('near-nan',32,float('nan'))):
            invalid=work/('invalid-'+label);invalid.mkdir()
            for n,data in original_state.items():(invalid/n).write_bytes(data)
            frame=bytearray(original_state['frame-state.bin']);struct.pack_into('<f',frame,offset,value);(invalid/'frame-state.bin').write_bytes(frame)
            out=work/('rejected-'+label);command('reject-'+label,[exe,'--cpu-inspect','--state',invalid,'--out',out],2);need(not out.exists(),'023 malformed camera allocated SDK/output')
        result['all_pass']=True
    except Exception as error:result['error']=type(error).__name__+': '+str(error)
    check_hashes(result['input_sha256']);check_hashes(b['payload_sha256'],build);check_hashes(first['payload_sha256'],reuse.parent)
    result.update(complete=True,payload_sha256=B.inventory(work),quality_admitted=False,accepted_timing=False,lane_m_complete=False)
    with (work/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result.get(k) for k in ('all_pass','cpp_checks','validated_pipelines','sdk_api_executed','gpu_executed','error')}));return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--build',required=True,type=Path);ap.add_argument('--work',required=True,type=Path);ap.add_argument('--reuse-first-failure',required=True,type=Path);a=ap.parse_args();r=run(a.build,a.work,a.reuse_first_failure.resolve());sys.exit(0 if r['all_pass'] else 2)

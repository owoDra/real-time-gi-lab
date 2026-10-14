#!/usr/bin/env python3
"""Retained selected-path diagnostic; no reference admission or exclusions."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np

from diagnose_gpu_deep_sampling import BASE, LANE, ROOT, invoke, payload, replace_once, sha
from compile_gpu_reference import decorate

CPU_TRACE = r'''
    std::vector<DTrace> cpuTraces(selected.size()*spp*7);
    std::vector<GStats> manual(pixels);
    auto vec=[](D4 a){return N::V3{a.v[0],a.v[1],a.v[2]};};
    for(size_t slot=0;slot<selected.size();++slot)for(uint32_t sample=0;sample<spp;++sample) {
        uint32_t pixel=selected[slot];auto p=primary[pixel];
        N::N010NetRng rng(seed,pixel,sample);N::Rgb indirect{};
        N::RenderCounters cnt{p.counters[0],p.counters[1],p.counters[2],p.counters[3]};
        if(p.origin.v[3]>0 && scene.max_bounces>1){
            N::V3 origin=vec(p.origin),normal=vec(p.normal);
            N::Rgb throughput{p.rho.v[0],p.rho.v[1],p.rho.v[2]};
            uint32_t ignore=uint32_t(p.normal.v[3]);
            for(uint32_t bounce=1;bounce<scene.max_bounces;++bounce){
                auto& entry=cpuTraces[(slot*spp+sample)*7+bounce-1];
                double u1=rng.uniform(),u2=rng.uniform();auto direction=N::Oracle::cosine_sample(normal,u1,u2);
                entry.origin=d4(origin);entry.direction=d4(direction);entry.info[0]=UINT32_MAX;entry.info[1]=1;
                auto hit=oracle.bvh().closest({origin,direction},0,scene.secondary_far_camera?scene.camera.far:N::kInf,ignore);
                entry.hit=d4(origin+direction*hit.t,hit.t);
                if(!hit.hit())break;
                entry.info[0]=hit.tri;entry.info[1]=2;
                auto tri=scene.triangles[hit.tri];auto m=scene.materials[tri.material];
                auto ng=N::normalize(N::cross(tri.v1-tri.v0,tri.v2-tri.v0));bool front=N::dot(ng,direction)<0;
                if(!front && !m.two_sided){++cnt.backface_absorbed;entry.info[1]=3;break;}
                normal=front?ng:ng*-1.;entry.normal=d4(normal);
                origin=oracle.nudge_inside(tri,origin+direction*hit.t)+normal*oracle.offset();entry.nudged=d4(origin);
                N::Rgb f{m.rho[0]/N::kPi,m.rho[1]/N::kPi,m.rho[2]/N::kPi};
                if(f[0]==0&&f[1]==0&&f[2]==0){entry.info[1]=4;break;}
                auto tests=cnt.shadow_tests,blocked=cnt.shadow_blocked;NoDraw unused;
                auto e=oracle.direct(origin,normal,hit.tri,unused,cnt);entry.irradiance=d4(e);
                entry.info[2]=cnt.shadow_tests-tests;entry.info[3]=cnt.shadow_blocked-blocked;
                for(int c=0;c<3;++c){indirect[c]+=throughput[c]*f[c]*e[c];throughput[c]*=m.rho[c];}
                entry.indirect=d4(indirect);ignore=hit.tri;
            }
        }
        auto& st=manual[pixel];
        for(int c=0;c<3;++c){double values[4]={p.emit.v[c],p.direct.v[c],indirect[c],(p.emit.v[c]+p.direct.v[c])+indirect[c]};
            for(int k=0;k<4;++k){st.sum[k].v[c]+=values[k];st.sum2[k].v[c]+=values[k]*values[k];}}
        st.counters[0]+=cnt.primary_hits;st.counters[1]+=cnt.shadow_tests;st.counters[2]+=cnt.shadow_blocked;st.counters[3]+=cnt.backface_absorbed;
    }
    sidecar(out/"manual.f64",scene,seed,spp,manual.data());
    std::ofstream manualraw(out/"manual.stats",std::ios::binary);
    for(auto pixel:selected)manualraw.write(reinterpret_cast<const char*>(&manual[pixel]),sizeof(GStats));manualraw.close();
    std::ofstream cputrace(out/"cpu.trace",std::ios::binary);cputrace.write(reinterpret_cast<const char*>(cpuTraces.data()),cpuTraces.size()*sizeof(DTrace));cputrace.close();
'''


def run(args):
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing path diagnostic')
    args.work.mkdir(parents=True)
    prior = LANE / 'results/087-deep-sampling-intervention.json'
    evidence = json.loads(prior.read_text())
    if not evidence.get('replay_valid'):
        raise ValueError('requires exact original replay')
    previous = BASE / 'deep-sampling-diagnostic-v2'
    inputs = [prior, LANE / 'experiments/023-posthoc-deep-path-trace.md',
              previous / 'roi.comp.glsl', previous / 'polynomial.cpp',
              previous / 'cpu-trigonometry.cpp', Path(__file__)]
    report = dict(schema='n010-selected-path-trace/1', complete=False,
                  gpu_run=False, eligible_for_references=False,
                  classification='POSTHOC_DIAGNOSTIC_NOT_ADMISSION',
                  selected_pixels=evidence['selected_pixels'],
                  input_sha256={str(p.relative_to(ROOT)): sha(p) for p in inputs}, steps=[])
    try:
        shader = inputs[2].read_text()
        shader = replace_once(shader, 'uint diagnosticSlot,diagnosticSample,diagnosticBounce;', '''
struct DebugTrace { dvec4 origin,direction,hit,normal,irradiance,nudged,indirect; u64vec4 info; };
layout(std430,binding=11) buffer Debug { DebugTrace entries[]; };
uint diagnosticSlot,diagnosticSample,diagnosticBounce;''')
        shader = replace_once(shader, 'Hit hit=trace(origin,direction,0.0LF,physical.w,ignore,false);if(hit.tri==MISS)break;', '''
                uint traceIndex=(diagnosticSlot*interval.z+sampleIndex)*7u+bounce-1u;
                entries[traceIndex]=DebugTrace(dvec4(origin,0.0LF),dvec4(direction,0.0LF),dvec4(0.0LF),dvec4(0.0LF),dvec4(0.0LF),dvec4(0.0LF),dvec4(0.0LF),u64vec4(uint64_t(MISS),uint64_t(1),uint64_t(0),uint64_t(0)));
                Hit hit=trace(origin,direction,0.0LF,physical.w,ignore,false);
                entries[traceIndex].hit=dvec4(origin+direction*hit.t,hit.t);
                if(hit.tri==MISS)break;
                entries[traceIndex].info.x=uint64_t(hit.tri);entries[traceIndex].info.y=uint64_t(2);
''')
        shader = replace_once(shader, 'counters.w+=uint64_t(1);break;', 'counters.w+=uint64_t(1);entries[traceIndex].info.y=uint64_t(3);break;')
        shader = replace_once(shader, 'normal=front?ng:-ng;', 'normal=front?ng:-ng;entries[traceIndex].normal=dvec4(normal,0.0LF);')
        shader = replace_once(shader, 'origin=position+normal*physical.x;', 'origin=position+normal*physical.x;entries[traceIndex].nudged=dvec4(origin,0.0LF);')
        shader = replace_once(shader, 'if(all(equal(f,dvec3(0.0LF))))break;', 'if(all(equal(f,dvec3(0.0LF)))){entries[traceIndex].info.y=uint64_t(4);break;}')
        shader = replace_once(shader, 'dvec3 e=direct_term(origin,normal,hit.tri,counters);', '''
                u64vec4 beforeDirect=counters;
                dvec3 e=direct_term(origin,normal,hit.tri,counters);
                entries[traceIndex].irradiance=dvec4(e,0.0LF);
                entries[traceIndex].info.z=counters.y-beforeDirect.y;entries[traceIndex].info.w=counters.z-beforeDirect.z;
''')
        shader = replace_once(shader, 'indirect+=(throughput*f)*e;throughput*=', 'indirect+=(throughput*f)*e;entries[traceIndex].indirect=dvec4(indirect,0.0LF);throughput*=')
        shader_path=args.work/'trace.comp.glsl';shader_path.write_text(shader)
        spv=args.work/'trace.spv';raw=args.work/'raw.spv'
        command=[str(ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'),'-V','--target-env','vulkan1.2','-S','comp',str(shader_path),'-o',str(raw)]
        report['steps'].append(invoke(command,args.work,'shader-build'))
        data,count=decorate(raw.read_bytes());spv.write_bytes(data);report['shader_sha256']=sha(spv)
        report['no_contraction_results']=count
        for name in ('polynomial','cpu-trigonometry'):
            host=(previous/(name+'.cpp')).read_text()
            host=replace_once(host, 'static_assert(sizeof(GNode)', '''struct alignas(32) DTrace { D4 origin,direction,hit,normal,irradiance,nudged,indirect; uint64_t info[4]{}; };
static_assert(sizeof(DTrace)==256);
static_assert(sizeof(GNode)''')
            host=replace_once(host,'    Context c;c.init();',CPU_TRACE+'\n    Context c;c.init();')
            host=replace_once(host,'upload(trig.data(),trig.size()*sizeof(trig[0]));', 'upload(trig.data(),trig.size()*sizeof(trig[0]));std::vector<DTrace> emptyTrace(cpuTraces.size());upload(emptyTrace.data(),emptyTrace.size()*sizeof(DTrace));')
            for old,new in [('LayoutBinding,11>','LayoutBinding,12>'),('j<11;','j<12;'),('STORAGE_BUFFER,11}','STORAGE_BUFFER,12}'),('BufferInfo,11>','BufferInfo,12>'),('DescriptorSet,11>','DescriptorSet,12>'),('c.device,11,writes','c.device,12,writes')]:
                if old not in host:raise ValueError('missing trace host anchor: '+old)
                host=host.replace(old,new)
            host=replace_once(host,'    std::ofstream gpuRaw', '    std::ofstream gpuTrace(out/"gpu.trace",std::ios::binary);gpuTrace.write(static_cast<const char*>(c.buffers[11].mapped),cpuTraces.size()*sizeof(DTrace));gpuTrace.close();\n    std::ofstream gpuRaw')
            source=args.work/(name+'.cpp');source.write_text(host)
            binary=args.work/('phos-n010-trace-'+name)
            build=json.loads((previous/(name+'-build.json')).read_text())['command']
            old_source=previous/(name+'.cpp');old_binary=previous/('phos-n010-roi-'+name)
            build=[str(source) if x in (str(old_source),str(old_source.relative_to(ROOT))) else str(binary) if x in (str(old_binary),str(old_binary.relative_to(ROOT))) else x for x in build]
            if str(source) not in build or build[-1]!=str(binary) or binary.exists():
                raise ValueError('build must use new diagnostic source/output only')
            report['steps'].append(invoke(build,args.work,name+'-build'))
            output=args.work/name
            runtime=['bash',str(ROOT/'scripts/run_with_vulkan.sh'),str(binary),str(BASE/'references-v1/C1_T_B8/scene.n008'),str(BASE/'sobol16x262144.bin'),str(spv),'305419896','8192','16',str(output)]
            report['steps'].append(invoke(runtime,args.work,name+'-runtime'))
            report['gpu_run']=True
            report.setdefault('artifact_sha256',{})[name]={f:sha(output/f) for f in ('cpu.trace','gpu.trace','manual.f64','manual.stats','cpu.f64','cpu.stats','o.f64','gpu.stats','allocation-ledger.json')}
        replays=[];divergences=[]
        for name in ('polynomial','cpu-trigonometry'):
            out=args.work/name
            cpu=payload(out/'cpu.f64');manual=payload(out/'manual.f64');gpu=payload(out/'o.f64');oldgpu=payload(previous/name/'o.f64')
            cs=(out/'cpu.stats').read_bytes();ms=(out/'manual.stats').read_bytes()
            shape=(8,8192,7,32)
            c=np.fromfile(out/'cpu.trace',dtype='<f8').reshape(shape);g=np.fromfile(out/'gpu.trace',dtype='<f8').reshape(shape)
            ci=c.view('<u8')[...,28:32];gi=g.view('<u8')[...,28:32]
            active=ci[...,1]!=0
            semantic=np.any(ci!=gi,axis=-1)&(active|(gi[...,1]!=0))
            for slot,pixel in enumerate(evidence['selected_pixels']):
                start=28+pixel*192
                replays.append(dict(mode=name,pixel=pixel,cpu_manual_payload_equal=cpu[start:start+192]==manual[start:start+192],cpu_manual_counters_equal=cs[slot*288+256:(slot+1)*288]==ms[slot*288+256:(slot+1)*288],gpu_payload_reproduces_087=gpu[start:start+192]==oldgpu[start:start+192]))
                samples=np.where(semantic[slot].any(axis=-1))[0]
                for sample in samples:
                    bounce=int(np.where(semantic[slot,sample])[0][0])
                    def entry(a,info):
                        d={k:[float(x) if np.isfinite(x) else str(x) for x in a[j:j+3]] for k,j in [('origin',0),('direction',4),('hit_position',8),('normal',12),('irradiance',16),('nudged_origin',20),('indirect',24)]}
                        d.update(t=float(a[11]) if np.isfinite(a[11]) else 'inf',primitive=int(info[0]),flag=int(info[1]),shadow_tests=int(info[2]),shadow_blocked=int(info[3]));return d
                    prior=[]
                    for j in range(bounce):
                        ca=c[slot,sample,j,:28];ga=g[slot,sample,j,:28];finite=np.isfinite(ca)&np.isfinite(ga)
                        prior.append(dict(bounce=j+1,max_abs_finite_numeric_difference=float(np.max(np.abs(ca[finite]-ga[finite])))))
                    divergences.append(dict(mode=name,pixel=pixel,sample=int(sample),bounce=bounce+1,cpu=entry(c[slot,sample,bounce],ci[slot,sample,bounce]),gpu=entry(g[slot,sample,bounce],gi[slot,sample,bounce]),prior_bounces=prior))
        report['replays']=replays
        report['replay_valid']=all(all(r[k] for k in ('cpu_manual_payload_equal','cpu_manual_counters_equal','gpu_payload_reproduces_087')) for r in replays)
        report['first_semantic_divergences']=divergences
        report['scope']='Post-hoc selected-path diagnosis. Full frame and all admission gates remain required. No threshold changes or excluded paths.'
    except Exception as error:report['failure']=str(error)
    report['gpu_run']=any(args.work.glob('*/gpu.json'))
    report['complete']=True
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report.get(k) for k in ('complete','failure','replay_valid')}))
    return 2 if report.get('failure') else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))

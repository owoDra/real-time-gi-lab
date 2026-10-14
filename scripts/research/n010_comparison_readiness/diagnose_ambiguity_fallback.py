#!/usr/bin/env python3
"""Whole-path CPU fallback feasibility on fixed post-hoc pixels; no admission."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np
from diagnose_gpu_deep_sampling import BASE, LANE, ROOT, invoke, payload, replace_once, sha
from compile_gpu_reference import decorate

FALLBACK = r'''
    auto paths=static_cast<const GPath*>(c.buffers[11].mapped);
    auto flagsPath=static_cast<const uint32_t*>(c.buffers[12].mapped);
    std::vector<GStats> corrected(pixels);
    std::ofstream fallbackCounts(out/"fallback-counts.json");fallbackCounts<<"[";
    for(size_t slot=0;slot<selected.size();++slot){
        auto pixel=selected[slot];N::Oracle::PrimaryCache cache;uint32_t flagged=0;
        for(uint32_t sample=0;sample<spp;++sample){
            auto index=slot*spp+sample;GPath path=paths[index];
            if(flagsPath[index]){
                ++flagged;N::N010NetRng rng(seed,pixel,sample);N::Rgb comp[N::kComponents]{};N::RenderCounters cnt{};
                oracle.sample(pixel%scene.width,pixel/scene.width,rng,comp,cnt,nullptr,&cache);
                for(int k=0;k<3;++k)path.components[k]=d4(comp[k]);
                for(int ch=0;ch<3;++ch)path.components[3].v[ch]=(comp[0][ch]+comp[1][ch])+comp[2][ch];
                path.counters[0]=cnt.primary_hits;path.counters[1]=cnt.shadow_tests;path.counters[2]=cnt.shadow_blocked;path.counters[3]=cnt.backface_absorbed;
            }
            auto& st=corrected[pixel];
            for(int k=0;k<4;++k)for(int ch=0;ch<3;++ch){double value=path.components[k].v[ch];st.sum[k].v[ch]+=value;st.sum2[k].v[ch]+=value*value;}
            for(int k=0;k<4;++k)st.counters[k]+=path.counters[k];
        }
        if(slot)fallbackCounts<<",";fallbackCounts<<"{\"pixel\":"<<pixel<<",\"flagged_samples\":"<<flagged<<"}";
    }
    fallbackCounts<<"]\n";fallbackCounts.close();
    sidecar(out/"corrected.f64",scene,seed,spp,corrected.data());
    std::ofstream correctedRaw(out/"corrected.stats",std::ios::binary);
    for(auto pixel:selected)correctedRaw.write(reinterpret_cast<const char*>(&corrected[pixel]),sizeof(GStats));correctedRaw.close();
    std::ofstream flagsRaw(out/"path-flags.bin",std::ios::binary);flagsRaw.write(reinterpret_cast<const char*>(flagsPath),selected.size()*spp*4);flagsRaw.close();
'''


def run(args):
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing fallback diagnostic')
    args.work.mkdir(parents=True)
    previous=BASE/'deep-sampling-diagnostic-v2'
    proof=LANE/'results/087-deep-sampling-intervention.json'
    data=json.loads(proof.read_text())
    if not data.get('replay_valid'):raise ValueError('exact original replay required')
    inputs=[proof,LANE/'experiments/024-prospective-ambiguity-fallback-diagnostic.md',previous/'roi.comp.glsl',previous/'polynomial.cpp',Path(__file__)]
    report=dict(schema='n010-ambiguity-fallback-diagnostic/1',complete=False,gpu_run=False,eligible_for_references=False,
        classification='SELECTED_POSTHOC_FEASIBILITY_NOT_ADMISSION',selected_pixels=data['selected_pixels'],
        input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},steps=[],guard_binary64_epsilon_multiplier=64,
        guard_scale='max(abs(best_t), scene_diagonal)',scoring_exclusions=0)
    try:
        shader=inputs[2].read_text()
        shader=replace_once(shader,'uint diagnosticSlot,diagnosticSample,diagnosticBounce;', '''
struct PathValue { dvec4 components[4]; u64vec4 counters; };
layout(std430,binding=11) buffer Paths { PathValue paths[]; };
layout(std430,binding=12) buffer Flags { uint pathFlags[]; };
bool pathAmbiguous;
double ambiguityRadius(double t){return 1.42108547152020037174224853515625e-14LF*max(abs(t),physical.x*1e12LF);}
uint diagnosticSlot,diagnosticSample,diagnosticBounce;''')
        shader=replace_once(shader,'if(!slab(node,origin,inv,tmin,best.t))continue;', 'double upper=best.t;if(!shadow && best.tri!=MISS)upper+=ambiguityRadius(best.t);if(!slab(node,origin,inv,tmin,upper))continue;')
        shader=replace_once(shader,'''if(id==ignore || !(t<infinity()) || !(t>tmin) || t>best.t)continue;
            if(shadow){if(t<limit)return Hit(t,id);continue;}''', '''if(id==ignore || !(t<infinity()) || !(t>tmin))continue;
            if(shadow){if(abs(t-limit)<=ambiguityRadius(limit))pathAmbiguous=true;if(t<limit)return Hit(t,id);continue;}
            if(best.tri!=MISS && id!=best.tri && abs(t-best.t)<=ambiguityRadius(best.t))pathAmbiguous=true;
            if(t>best.t)continue;''')
        shader=replace_once(shader,'diagnosticSample=sampleIndex;', 'pathAmbiguous=false;diagnosticSample=sampleIndex;')
        shader=replace_once(shader,'for(int k=0;k<4;++k){precise', 'for(int k=0;k<4;++k){precise') if 'for(int k=0;k<4;++k){precise' in shader else shader
        shader=replace_once(shader,'stats[pixel].counters+=counters;', '''stats[pixel].counters+=counters;
        uint pathIndex=diagnosticSlot*interval.z+sampleIndex;
        for(int k=0;k<4;++k)paths[pathIndex].components[k]=dvec4(components[k],0.0LF);
        paths[pathIndex].counters=counters;pathFlags[pathIndex]=pathAmbiguous?1u:0u;''')
        source_shader=args.work/'fallback.comp.glsl';source_shader.write_text(shader)
        raw=args.work/'raw.spv';spv=args.work/'fallback.spv'
        command=[str(ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'),'-V','--target-env','vulkan1.2','-S','comp',str(source_shader),'-o',str(raw)]
        report['steps'].append(invoke(command,args.work,'shader-build'))
        decorated,count=decorate(raw.read_bytes());spv.write_bytes(decorated)
        report['no_contraction_results']=count
        host=inputs[3].read_text()
        host=replace_once(host,'static_assert(sizeof(GNode)', '''struct alignas(32) GPath {D4 components[4];uint64_t counters[4]{};};
static_assert(sizeof(GPath)==160);
static_assert(sizeof(GNode)''')
        host=replace_once(host,'upload(trig.data(),trig.size()*sizeof(trig[0]));','upload(trig.data(),trig.size()*sizeof(trig[0]));std::vector<GPath> emptyPath(selected.size()*spp);upload(emptyPath.data(),emptyPath.size()*sizeof(GPath));std::vector<uint32_t> emptyFlags(emptyPath.size());upload(emptyFlags.data(),emptyFlags.size()*4);')
        for old,new in [('LayoutBinding,11>','LayoutBinding,13>'),('j<11;','j<13;'),('STORAGE_BUFFER,11}','STORAGE_BUFFER,13}'),('BufferInfo,11>','BufferInfo,13>'),('DescriptorSet,11>','DescriptorSet,13>'),('c.device,11,writes','c.device,13,writes')]:
            if old not in host:raise ValueError('missing binding anchor '+old)
            host=host.replace(old,new)
        host=replace_once(host,'    std::ofstream gpuRaw',FALLBACK+'\n    std::ofstream gpuRaw')
        source=args.work/'fallback.cpp';source.write_text(host);binary=args.work/'phos-n010-fallback-diagnostic'
        build=json.loads((previous/'polynomial-build.json').read_text())['command']
        old_source=previous/'polynomial.cpp';old_binary=previous/'phos-n010-roi-polynomial'
        build=[str(source)if x in (str(old_source),str(old_source.relative_to(ROOT))) else str(binary)if x in (str(old_binary),str(old_binary.relative_to(ROOT)))else x for x in build]
        if str(source)not in build or build[-1]!=str(binary)or binary.exists():raise ValueError('build requires new source/output')
        report['steps'].append(invoke(build,args.work,'host-build'))
        report['generated_sha256']=dict(source=sha(source),binary=sha(binary),shader=sha(spv))
        output=args.work/'gpu'
        runtime=['bash',str(ROOT/'scripts/run_with_vulkan.sh'),str(binary),str(BASE/'references-v1/C1_T_B8/scene.n008'),str(BASE/'sobol16x262144.bin'),str(spv),'305419896','8192','16',str(output)]
        report['steps'].append(invoke(runtime,args.work,'runtime'))
        saved=payload(BASE/'references-v1/C1_T_B8/o.n8192.s0.f64');cpu=payload(output/'cpu.f64');fixed=payload(output/'corrected.f64')
        cs=(output/'cpu.stats').read_bytes();fs=(output/'corrected.stats').read_bytes()
        report['flag_counts']=json.loads((output/'fallback-counts.json').read_text());report['rows']=[]
        for slot,pixel in enumerate(data['selected_pixels']):
            start=28+pixel*192;a=np.array(struct.unpack_from('<24d',cpu,start));b=np.array(struct.unpack_from('<24d',fixed,start));cc=struct.unpack_from('<4Q',cs,slot*288+256);fc=struct.unpack_from('<4Q',fs,slot*288+256)
            mean=float(np.max(abs(a[:12]-b[:12])));moment=float(np.max(abs(a[12:]-b[12:])));ind=float(np.linalg.norm(a[6:9]-b[6:9])/np.linalg.norm(a[6:9]))
            report['rows'].append(dict(pixel=pixel,cpu_reproduces_original=cpu[start:start+192]==saved[start:start+192],max_abs_mean=mean,max_abs_moment=moment,indirect_nrmse=ind,cpu_counters=cc,corrected_counters=fc,counters_equal=cc==fc,direct_emission_byte_equal=cpu[start:start+48]==fixed[start:start+48],finite=bool(np.isfinite(b).all()),passes_selected_numerical_gates=bool(mean<=1e-10 and moment<=1e-10 and ind<=1e-8 and cc==fc and np.isfinite(b).all()and cpu[start:start+48]==fixed[start:start+48])))
        report['all_selected_pass']=all(r['cpu_reproduces_original']and r['passes_selected_numerical_gates']for r in report['rows'])
        report['artifact_sha256']={p.name:sha(p)for p in output.iterdir()if p.is_file()}
        report['scope']='Selected-pixel feasibility only. No stored reference values or forced hit/sign used by fallback; every flagged whole path recomputed with original CPU oracle. Full admission and prefix gates remain required.'
    except Exception as error:report['failure']=str(error)
    report['gpu_run']=any(args.work.glob('*/gpu.json'));report['complete']=True
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report.get(k)for k in ('complete','failure','all_selected_pass','flag_counts')}))
    return 2 if report.get('failure')else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))

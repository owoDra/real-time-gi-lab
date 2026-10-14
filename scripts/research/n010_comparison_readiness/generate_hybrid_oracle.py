#!/usr/bin/env python3
"""Build a separate streamed hybrid oracle candidate; never admit references."""
import argparse
import json
from pathlib import Path
from diagnose_gpu_deep_sampling import BASE, LANE, ROOT, invoke, replace_once, sha
from compile_gpu_reference import decorate

ACCUMULATE = r'''
        auto pathValues=static_cast<const GPath*>(c.buffers[11].mapped);
        auto pathFlags=static_cast<const uint32_t*>(c.buffers[12].mapped);
        std::vector<std::thread> workers;
        for(uint32_t worker=0;worker<threads;++worker)workers.emplace_back([&,worker]{
            for(size_t pixel=worker;pixel<pixels;pixel+=threads){
                auto& dst=corrected[pixel];auto& cache=cpuCaches[pixel];
                for(uint32_t sample=begin;sample<params.interval[1];++sample){
                    auto index=pixel*batch+sample-begin;GPath value=pathValues[index];
                    if(pathFlags[index]){
                        ++fallbackCounts[worker];N::N010NetRng rng(seed,pixel,sample);N::Rgb comp[N::kComponents]{};N::RenderCounters cnt{};
                        oracle.sample(uint32_t(pixel%scene.width),uint32_t(pixel/scene.width),rng,comp,cnt,nullptr,&cache);
                        for(int k=0;k<3;++k)value.components[k]=d4(comp[k]);
                        for(int ch=0;ch<3;++ch)value.components[3].v[ch]=(comp[0][ch]+comp[1][ch])+comp[2][ch];
                        value.counters[0]=cnt.primary_hits;value.counters[1]=cnt.shadow_tests;value.counters[2]=cnt.shadow_blocked;value.counters[3]=cnt.backface_absorbed;
                    }
                    for(int k=0;k<4;++k)for(int ch=0;ch<3;++ch){double x=value.components[k].v[ch];dst.sum[k].v[ch]+=x;dst.sum2[k].v[ch]+=x*x;}
                    for(int k=0;k<4;++k)dst.counters[k]+=value.counters[k];
                }
            }
        });
        for(auto& worker:workers)worker.join();
'''


def run(args):
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing hybrid build')
    args.work.mkdir(parents=True)
    prior=BASE/'ambiguity-fallback-diagnostic-v1'
    proof=LANE/'results/093-ambiguity-fallback-diagnostic.json'
    d=json.loads(proof.read_text())
    if not d.get('all_selected_pass'):raise ValueError('requires selected whole-path feasibility')
    files=[proof,LANE/'experiments/025-prospective-full-hybrid-conformance.md',prior/'fallback.cpp',prior/'fallback.comp.glsl',Path(__file__)]
    report=dict(schema='n010-hybrid-reference-build/1',complete=False,all_pass=False,gpu_run=False,eligible_for_references=False,
                input_sha256={str(p.relative_to(ROOT)):sha(p)for p in files},steps=[])
    try:
        host=files[2].read_text()
        start=host.index('    const std::vector<uint32_t> selected =')
        end=host.index('    Context c;c.init();',start)
        host=host[:start]+'''    std::vector<uint32_t> selected(pixels);for(uint32_t p=0;p<pixels;++p)selected[p]=p;
    std::array<std::array<double,2>,1> trig{}; // unused: polynomial mode only
'''+host[end:]
        host=replace_once(host,'uint32_t spp,uint32_t batch,const fs::path& out)', 'uint32_t spp,uint32_t batch,uint32_t threads,const fs::path& out)')
        host=replace_once(host,'params.interval[2]=spp;', 'params.interval[2]=batch;')
        host=replace_once(host,'selected.size()*spp', 'selected.size()*batch') if host.count('selected.size()*spp')==1 else host
        # Remove the prior post-hoc full-selected-frame fallback block. This
        # candidate processes every frame pixel in bounded streaming batches.
        start=host.index('    auto paths=static_cast<const GPath*>')
        end=host.index('    std::ofstream gpuRaw',start)
        host=host[:start]+host[end:]
        host=replace_once(host,'std::vector<GPath> emptyPath(selected.size()*spp);', 'std::vector<GPath> emptyPath(selected.size()*batch);') if 'std::vector<GPath> emptyPath(selected.size()*spp);' in host else host
        host=replace_once(host,'    for(uint32_t begin=0;begin<spp;begin+=batch){', '''
    std::vector<GStats> corrected(pixels);
    std::vector<N::Oracle::PrimaryCache> cpuCaches(pixels);
    std::vector<uint64_t> fallbackCounts(threads);
    for(uint32_t begin=0;begin<spp;begin+=batch){''')
        host=replace_once(host,'check(vkQueueWaitIdle(c.queue));\n    }', 'check(vkQueueWaitIdle(c.queue));\n'+ACCUMULATE+'\n    }')
        host=replace_once(host,'auto values=static_cast<const GStats*>(c.buffers[6].mapped);', 'auto values=corrected.data();')
        host=replace_once(host,'    sidecar(out/"o.f64",scene,seed,spp,values);', '''
    uint64_t fallbackTotal=0;for(auto count:fallbackCounts)fallbackTotal+=count;
    std::ofstream hybrid(out/"hybrid.json");hybrid<<"{\\\"schema\\\":\\\"n010-streamed-hybrid-diagnostic/1\\\",\\\"cpu_fallback_paths\\\":"<<fallbackTotal<<",\\\"total_paths\\\":"<<uint64_t(pixels)*spp<<",\\\"cpu_threads\\\":"<<threads<<",\\\"batch\\\":"<<batch<<",\\\"eligible_for_references\\\":false}\\n";hybrid.close();
    sidecar(out/"o.f64",scene,seed,spp,values);''')
        host=replace_once(host,'if(argc!=8)', 'if(argc!=9)')
        host=replace_once(host,'SPP BATCH NEW_OUTPUT', 'SPP BATCH CPU_THREADS NEW_OUTPUT')
        host=replace_once(host,'fs::path out=argv[7];', 'fs::path out=argv[8];')
        host=replace_once(host,'if(!spp || spp>262144 || !batch || batch>1024)', 'uint32_t threads=uint32_t(std::stoul(argv[7]));if(!spp || spp>262144 || !batch || batch>16 || !threads || threads>16)')
        host=replace_once(host,'seed,spp,batch,out);', 'seed,spp,batch,threads,out);')
        source=args.work/'hybrid.cpp';source.write_text(host)
        shader=files[3].read_text()
        shader=replace_once(shader,'uint pathIndex=diagnosticSlot*interval.z+sampleIndex;', 'uint pathIndex=diagnosticSlot*interval.z+sampleIndex-interval.x;')
        shader_source=args.work/'hybrid.comp.glsl';shader_source.write_text(shader)
        spv=args.work/'hybrid.spv';raw=args.work/'raw.spv'
        command=[str(ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'),'-V','--target-env','vulkan1.2','-S','comp',str(shader_source),'-o',str(raw)]
        report['steps'].append(invoke(command,args.work,'shader-build'))
        compiled,count=decorate(raw.read_bytes());spv.write_bytes(compiled);report['no_contraction_results']=count
        binary=args.work/'phos-n010-hybrid-reference'
        build=json.loads((prior/'host-build.json').read_text())['command']
        old_source=prior/'fallback.cpp';old_binary=prior/'phos-n010-fallback-diagnostic'
        build=[str(source)if x in (str(old_source),str(old_source.relative_to(ROOT)))else str(binary)if x in (str(old_binary),str(old_binary.relative_to(ROOT)))else x for x in build]
        if str(source)not in build or build[-1]!=str(binary)or binary.exists():raise ValueError('requires new source/output')
        report['steps'].append(invoke(build,args.work,'host-build'))
        report['generated_sha256']={p.name:sha(p)for p in (source,shader_source,spv,binary)}
        report['all_pass']=True
        report['scope']='Standalone streamed hybrid candidate build only. CPU whole-path recomputation for ambiguous intersections, deterministic per-pixel accumulation. No GPU execution, reference admission, default build/Renderer change or CUDA.'
    except Exception as error:report['failure']=str(error)
    report['complete']=True;args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k)for k in ('complete','failure','all_pass')}))
    return 0 if report['all_pass']else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(p.parse_args()))

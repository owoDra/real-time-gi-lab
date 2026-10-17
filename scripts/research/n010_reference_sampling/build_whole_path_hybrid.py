#!/usr/bin/env python3
"""Plan110: isolated eight-pixel GPU/CPU all-split backend build, no GPU run."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'whole-path-hybrid-prototype-v1'
OUTPUT = D.RESULTS / '352-whole-path-hybrid-prototype-build.json'
PLAN = D.RESULTS.parent / 'experiments/110-whole-path-hybrid-prototype-build.md'


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing hybrid prototype build; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,)*2)
    for path in (Path(__file__).resolve(), PLAN, Path(C.__file__), Path(D.__file__),
                 D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(path)
    for stem in ('095', '254', '257'):
        proof = C.pinned_result(stem)
        if not proof['all_pass']:
            raise ValueError('retained hybrid/selected backend proof required')
        if stem == '095':
            for name, digest in proof['generated_sha256'].items():
                D.checked(D.OUT / 'hybrid-oracle-build-v1' / name, digest)
    cpu_source = D.OUT / 'wide8-cpu-bvh-v1/n010_rqmc_oracle.hpp'
    old_header = D.checked(cpu_source).decode()
    header = old_header
    class_start = header.index('class Bvh {')
    class_end = header.index('\n};', class_start)+3
    old_class = header[class_start:class_end]
    new_class = D.once(old_class, '    std::vector<Node> nodes_;',
        '    std::vector<Node> nodes_;\npublic:\n'
        '    const auto& n010_nodes() const {return nodes_;}\n'
        '    const auto& n010_order() const {return order_;}\nprivate:')
    header = D.once(header, old_class, new_class)
    old_access = '    const Bvh& bvh() const { return bvh_; }'
    new_access = old_access+'\n    double n010_edge_inset() const {return edge_inset_;}'
    header = D.once(header, old_access, new_access)
    inverse = D.once(D.once(header, new_access, old_access), new_class, old_class)
    if inverse != old_header:
        raise ValueError('CPU accessor inverse differs')
    snapshot = D.OUT / 'gpu-reference-snapshot-v1'
    manifest = json.loads(D.checked(snapshot / 'snapshot.json'))
    for name, digest in manifest['generated_sha256'].items():
        D.checked(snapshot / name, digest)
    context = D.checked(snapshot / 'n010_reference_context.hpp')
    base = D.OUT / 'hybrid-oracle-build-v1'
    old_host = D.checked(base / 'hybrid.cpp').decode()
    host_edits = []

    def host_once(old, new):
        nonlocal host
        host = D.once(host, old, new)
        host_edits.append((old, new))

    host = old_host
    selected = [y*320+x for x,y in ((40,30),(120,30),(200,30),(280,30),
                                    (40,150),(120,150),(200,150),(280,150))]
    host_once('    std::vector<uint32_t> selected(pixels);for(uint32_t p=0;p<pixels;++p)selected[p]=p;\n',
              '    // Plan110: selection declared before CPU primary initialization.\n')
    host_once('    for(uint32_t y=0;y<scene.height;++y)for(uint32_t x=0;x<scene.width;++x){',
        '    if(scene.width!=320 || scene.height!=180 || scene.max_bounces!=8 || scene.points.size()!=1)\n'
        '        throw std::runtime_error("prototype requires original C1 shape/depth/point count");\n'
        '    const std::vector<uint32_t> selected={'+','.join(map(str,selected))+'};\n'
        '    for(uint32_t selectedPixel:selected){uint32_t x=selectedPixel%scene.width,y=selectedPixel/scene.width;')
    host_once('for(size_t pixel=worker;pixel<pixels;pixel+=threads){',
              'for(size_t slot=worker;slot<selected.size();slot+=threads){size_t pixel=selected[slot];')
    host_once('auto index=pixel*batch+sample-begin;', 'auto index=slot*batch+sample-begin;')
    host_once('oracle.sample(uint32_t(pixel%scene.width),uint32_t(pixel/scene.width),rng,comp,cnt,nullptr,&cache);',
              'oracle.sample_all_split(uint32_t(pixel%scene.width),uint32_t(pixel/scene.width),rng,comp,cnt,nullptr,&cache);')
    host_once('!threads || threads>16', 'threads!=1')
    host_once('if(!spp || spp>262144', 'if(!spp || spp>8192')
    host_once('vkCmdDispatch(c.command,uint32_t((selected.size()+63)/64),1,1);',
              'vkCmdDispatch(c.command,uint32_t((selected.size()*batch+63)/64),1,1);')
    host_once('        params.interval[0]=begin;',
        '        const auto batchStarted=std::chrono::steady_clock::now();\n        params.interval[0]=begin;')
    host_once('check(vkQueueWaitIdle(c.queue));',
        'check(vkQueueWaitIdle(c.queue));\n'
        '        const double batchWaitSeconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-batchStarted).count();\n'
        '        const bool batchLatencyExceeded=batchWaitSeconds>0.250;')
    host_once('n010-gpu-reference-diagnostic/1', 'n010-whole-path-eight-pixel-hybrid/1')
    host_once('<<uint64_t(pixels)*spp<<', '<<uint64_t(selected.size())*spp<<')
    host_once('#include <chrono>', '#include <chrono>\n#include <exception>')
    host_once('    Context c;c.init();',
        '    std::ofstream primaryEvidence(out/"primary-records.bin",std::ios::binary);\n'
        '    for(auto pixel:selected)primaryEvidence.write(reinterpret_cast<const char*>(&primary[pixel]),sizeof(GPrimary));\n'
        '    primaryEvidence.close();if(!primaryEvidence)throw std::runtime_error("CPU primary evidence write failed");\n'
        '    Context c;c.init();')
    host_once('        std::vector<std::thread> workers;',
              '        std::exception_ptr workerError;\n        std::vector<std::thread> workers;')
    host_once('workers.emplace_back([&,worker]{', 'workers.emplace_back([&,worker]{try{')
    host_once('            }\n        });\n        for(auto& worker:workers)worker.join();',
              '            }\n        }catch(...){workerError=std::current_exception();}});\n'
              '        for(auto& worker:workers)worker.join();')
    # Runtime metadata must make the sparse diagnostic buffers unambiguous.
    marker='    std::vector<uint64_t> fallbackCounts(threads);'
    host_once(marker,marker+'\n'
        '    std::ofstream rawSamples(out/"gpu-paths.bin",std::ios::binary),\n'
        '        correctedSamples(out/"corrected-paths.bin",std::ios::binary),\n'
        '        routingFlags(out/"routing-flags.bin",std::ios::binary),batchIndex(out/"batches.jsonl");\n'
        '    std::ofstream scope(out/"prototype-scope.json");\n'
        '    scope<<"{\\"selection_scope\\":\\"eight_fixed_pixels_only\\",\\"selected_pixels\\":['+
        ','.join(map(str,selected))+'],\\"seed\\":"<<seed<<",\\"spp\\":"<<spp\n'
        '         <<",\\"path_record_bytes\\":"<<sizeof(GPath)<<",\\"primary_record_bytes\\":"<<sizeof(GPrimary)\n'
        '         <<",\\"flag_record_bytes\\":4,\\"reference_admission\\":false}\\n";scope.close();\n'
        '    if(!scope || !rawSamples || !correctedSamples || !routingFlags || !batchIndex)throw std::runtime_error("sample evidence file creation failed");')
    host_once('GPath value=pathValues[index];',
        'GPath value=pathValues[index];\n'
        '                    rawSamples.write(reinterpret_cast<const char*>(&value),sizeof value);\n'
        '                    routingFlags.write(reinterpret_cast<const char*>(&pathFlags[index]),sizeof(uint32_t));')
    marker='                    for(int k=0;k<4;++k)for(int ch=0;ch<3;++ch){double x=value.components[k].v[ch];'
    host_once(marker,
        '                    correctedSamples.write(reinterpret_cast<const char*>(&value),sizeof value);\n'+marker)
    marker='        for(auto& worker:workers)worker.join();'
    host_once(marker,marker+'\n'
        '        batchIndex<<std::setprecision(17)<<"{\\"begin\\":"<<begin<<",\\"end\\":"<<params.interval[1]\n'
        '            <<",\\"selected_count\\":"<<selected.size()<<",\\"complete\\":"<<(workerError?"false":"true")\n'
        '            <<",\\"submit_wait_wall_seconds_diagnostic\\":"<<batchWaitSeconds<<"}\\n";\n'
        '        rawSamples.flush();correctedSamples.flush();routingFlags.flush();batchIndex.flush();\n'
        '        if(!rawSamples || !correctedSamples || !routingFlags || !batchIndex)throw std::runtime_error("sample evidence write failed");\n'
        '        if(workerError)std::rethrow_exception(workerError);\n'
        '        if(batchLatencyExceeded)throw std::runtime_error("prototype submit/wait latency guard; retain completed batch samples");')
    inverse = host
    for old,new in reversed(host_edits):
        inverse = D.once(inverse, new, old)
    if inverse != old_host:
        raise ValueError('host prototype inverse differs')
    shader_base = D.checked(base / 'hybrid.comp.glsl').decode()
    shader_main = D.checked(D.HERE / 'whole_path_scaled_gpu.inc.glsl').decode()
    cpu_probe = D.checked(D.HERE / 'whole_path_cpu_probe.cpp')
    cut = shader_base.index('void main() {')
    shader = shader_base[:cut] + shader_main
    helper = D.HERE.parent / 'n010_comparison_readiness/compile_gpu_reference.py'
    D.checked(helper)
    sys.path.insert(0, str(helper.parent))
    from compile_gpu_reference import decorate
    build_command = json.loads(D.checked(D.OUT / 'ambiguity-fallback-diagnostic-v1/host-build.json'))['command']
    WORK.mkdir()
    (WORK/'n010_reference_snapshot.hpp').write_text(header)
    (WORK/'n010_reference_context.hpp').write_bytes(context)
    (WORK/'prototype.cpp').write_text(host)
    (WORK/'prototype.comp.glsl').write_text(shader)
    (WORK/'cpu-probe.cpp').write_bytes(cpu_probe)
    (WORK/'host-edits.json').write_text(json.dumps(host_edits,indent=2)+'\n')
    result = dict(schema='n010-whole-path-hybrid-prototype-build/1',complete=False,all_pass=False,
                  gpu_run=False,reference_admission=False,runtime_validated=False,
                  classification='ISOLATED_HYBRID_PROTOTYPE_BUILD_ACQUIRING',
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  input_sha256=D.INPUTS,attempts=[],cpu_accessor_inverse_exact=True,host_inverse_exact=True,
                  shader_physical_helpers_byte_identical=True,selected_pixels=selected,
                  tests='NOT_RUN; isolated compiler invocations only; no GPU execution')

    def save():
        OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

    def compile_one(command,label):
        receipt=WORK/(label+'.resources.json')

        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(120,)*2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')

        attempt=dict(command=command,label=label,resource_receipt=str(receipt))
        result['attempts'].append(attempt);save();started=time.monotonic()
        try:
            proc=subprocess.run(command,capture_output=True,text=True,timeout=180,preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            (WORK/(label+'.stdout')).write_bytes(error.stdout or b'')
            (WORK/(label+'.stderr')).write_bytes(error.stderr or b'')
            attempt.update(terminal=True,failure='COMPILER_ELAPSED_GUARD_NO_RETRY')
            raise ValueError('prototype compiler elapsed guard') from error
        (WORK/(label+'.stdout')).write_text(proc.stdout);(WORK/(label+'.stderr')).write_text(proc.stderr)
        attempt.update(terminal=True,returncode=proc.returncode,elapsed_seconds=time.monotonic()-started)
        actual=json.loads(D.checked(receipt))
        if (actual['cpu']!=[120]*2 or actual['address_space']!=[4*1024**3]*2
                or actual['affinity']!=[31] or actual['nice']!=15 or proc.returncode):
            raise ValueError('prototype compiler/resources failed; no retry')

    save()
    try:
        glslang=D.ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'
        D.checked(glslang)
        compile_one([str(glslang),'-V','--target-env','vulkan1.2','-S','comp',
                     str(WORK/'prototype.comp.glsl'),'-o',str(WORK/'raw.spv')],'shader')
        decorated,count=decorate((WORK/'raw.spv').read_bytes())
        (WORK/'prototype.spv').write_bytes(decorated);result['no_contraction_results']=count
        source_path=WORK/'prototype.cpp';binary=WORK/'phos-n010-whole-hybrid-prototype'
        command=[str(source_path) if x.endswith('/fallback.cpp') else str(binary)
                 if x.endswith('/phos-n010-fallback-diagnostic') else x for x in build_command]
        if str(source_path) not in command or command[-1]!=str(binary):
            raise ValueError('retained host compiler command differs')
        command.insert(1,'-mavx512f')
        compile_one(command,'host')
        compile_one(['g++','-std=c++20','-O2','-mavx512f','-fno-fast-math',
                     '-ffp-contract=off','-pthread',str(WORK/'cpu-probe.cpp'),
                     '-o',str(WORK/'n010_whole_cpu_probe')],'cpu-probe')
        for path,digest in list(D.INPUTS.items()):
            D.checked(Path(path),digest)
        result.update(complete=True,all_pass=True,
                      classification='ISOLATED_HYBRID_PROTOTYPE_BUILD_COMPLETE_NO_RUNTIME_ADMISSION')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(classification='HYBRID_PROTOTYPE_BUILD_FAILURE_RETAINED',failure=str(error))
    result['payload_sha256']={str(p):C.sha(p) for p in WORK.iterdir() if p.is_file()}
    save();print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Plan112: bounded full-frame/depth-split standalone build; never a GPU run."""
import hashlib
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

BASE=D.OUT/'whole-path-hybrid-prototype-v1'
WORK=D.OUT/'whole-path-full-frame-build-v1'
OUTPUT=D.RESULTS/'360-whole-path-full-frame-build.json'
PLAN=D.RESULTS.parent/'experiments/112-full-frame-depth-split-hybrid-build.md'


def generate_shader(old):
    edits=[]
    def change(value,before,after):
        out=D.once(value,before,after);edits.append((before,after));return out
    source=old
    source=change(source,'uvec4 interval; uvec4 seedWords; };','uvec4 interval; uvec4 seedWords; uvec4 controlWords; };')
    source=change(source,
        'struct PathValue { dvec4 components[4]; u64vec4 counters; };\nlayout(std430,binding=11) buffer Paths { PathValue paths[]; };',
        'struct PartValue { dvec4 contribution; u64vec4 counts; u64vec4 proposal; dvec4 maxima; };\n'
        'layout(std430,binding=11) buffer Parts { PartValue parts[]; };')
    source=change(source,'bool pathAmbiguous;',
        'bool pathAmbiguous;\nuint routeReasons;\n'
        'void mark_route(uint bit){pathAmbiguous=true;routeReasons|=bit;}\n'
        'uint64_t diagnosticQueries,diagnosticAttempts,diagnosticNulls,diagnosticOwn;\n'
        'dvec4 diagnosticMaxima;')
    trace_begin=source.index('Hit trace(');trace_end=source.index('\ndvec3 nudge(',trace_begin)
    trace=source[trace_begin:trace_end]
    if trace.count('pathAmbiguous=true;')!=2:raise ValueError('retained trace routing differs')
    source=change(source,trace,trace.replace('pathAmbiguous=true;','mark_route(1u);'))
    # Every original route remains; instrumentation does not relax a guard.
    body_begin=source.index('struct WholeRawGpu')
    prefix,body=source[:body_begin],source[body_begin:]
    old_body=body
    body_edits=[]
    def body_once(before,after):
        nonlocal body
        body=D.once(body,before,after);body_edits.append((before,after))
    # Specific reasons precede the general nonfinite/invalid route.
    body_once('if(possible_cpu_coincidence(target.tri,hit.tri))pathAmbiguous=true;',
              'if(possible_cpu_coincidence(target.tri,hit.tri))mark_route(16u);')
    before='if(cosine<1e-12LF || pdf<1e-12LF)pathAmbiguous=true;'
    if body.count(before)!=2:raise ValueError('expected two inherited small-density routes')
    after='if(cosine<1e-12LF || pdf<1e-12LF)mark_route(8u);'
    changed=body.replace(before,after);body_edits.append((body,changed));body=changed
    body_once('if(abs(ownRatio-1.0LF)>1e-8LF)pathAmbiguous=true;',
              'diagnosticMaxima.x=max(diagnosticMaxima.x,abs(ownRatio-1.0LF));\n'
              '                if(abs(ownRatio-1.0LF)>1e-8LF)mark_route(4u);')
    body_once('targetPlane>bound || actualPlane>bound || error*cosine>bound)pathAmbiguous=true;',
              'targetPlane>bound || actualPlane>bound || error*cosine>bound)mark_route(2u);')
    body_once('        if(!finite_positive(d2) || isnan(error)',
              '        diagnosticMaxima.y=max(diagnosticMaxima.y,max(max(targetPlane,actualPlane),error*cosine)/bound);\n'
              '        diagnosticMaxima.z=max(diagnosticMaxima.z,error/bound);\n'
              '        if(!finite_positive(d2) || isnan(error)')
    # Both generation and reconstruction have the same exact query expression.
    query='        Hit hit=trace(current.origin,direction,sphere?physical.x:0.0LF,\n                      sphere?infinity():physical.w,current.tri,false);'
    if body.count(query)!=2:raise ValueError('original proposal query sites differ')
    changed=body.replace(query,'        ++diagnosticQueries;\n'+query);body_edits.append((body,changed));body=changed
    body_once('        pathAmbiguous=false;diagnosticSample=sampleIndex;diagnosticBounce=1u;',
              '        pathAmbiguous=false;routeReasons=0u;diagnosticSample=sampleIndex;diagnosticBounce=controlWords.x;\n'
              '        diagnosticQueries=uint64_t(0);diagnosticAttempts=uint64_t(0);diagnosticNulls=uint64_t(0);diagnosticOwn=uint64_t(0);diagnosticMaxima=dvec4(0.0LF);')
    body_once('u64vec4 counters=initial.counters;','u64vec4 counters=u64vec4(uint64_t(0));')
    body_once('if(initial.origin.w>0.0LF && sizes.w>1u)',
              'if(initial.origin.w>0.0LF && controlWords.x>0u && controlWords.x<sizes.w)')
    body_once('for(uint k=1u;k<sizes.w;++k)',
              'for(uint k=controlWords.x;k<=controlWords.x;++k)')
    body_once('                diagnosticBounce=k;',
              '                diagnosticBounce=k;++diagnosticAttempts;')
    body_once('!generate_whole_gpu(photonState,split,true,uniforms,remap,dimension,light,sampled))continue;',
              '!generate_whole_gpu(photonState,split,true,uniforms,remap,dimension,light,sampled)){++diagnosticNulls;continue;}')
    body_once('                double ownRatio=density_ratio(sampled,q[split]);',
              '                ++diagnosticOwn;double ownRatio=density_ratio(sampled,q[split]);')
    body_once('                if(all(equal(throughput,dvec3(0.0LF))))continue;',
              '                diagnosticMaxima.w=max(diagnosticMaxima.w,weight);\n'
              '                if(all(equal(throughput,dvec3(0.0LF))))continue;')
    old_tail=body[body.index('        dvec3 components[4]'):]
    body_once(old_tail,'''        uint pathIndex=slot*interval.z+sampleIndex-interval.x;
        if(any(isnan(indirect)) || any(isinf(indirect)) || any(lessThan(indirect,dvec3(0.0LF))))mark_route(32u);
        parts[pathIndex].contribution=dvec4(indirect,0.0LF);
        parts[pathIndex].counts=u64vec4(counters.y,counters.z,diagnosticAttempts,diagnosticNulls);
        parts[pathIndex].proposal=u64vec4(diagnosticQueries,diagnosticOwn,uint64_t(0),uint64_t(0));
        parts[pathIndex].maxima=diagnosticMaxima;
        pathFlags[pathIndex]=routeReasons;
    }
}
''')
    before=body;changed=body.replace('pathAmbiguous=true;','mark_route(32u);')
    body_edits.append((before,changed));body=changed
    inverse=body
    for before,after in reversed(body_edits):inverse=D.once(inverse,after,before)
    if inverse!=old_body:raise ValueError('shader body inverse differs')
    source=change(source,old_body,body)
    inverse=source
    for before,after in reversed(edits):inverse=D.once(inverse,after,before)
    if inverse!=old:raise ValueError('full shader inverse differs')
    if 'pathAmbiguous=true;' in body:raise ValueError('uncategorized route remains')
    return source,edits


def main():
    if OUTPUT.exists() or WORK.exists():raise ValueError('refuse existing full-frame build; no retry')
    require_no_other_research_worker();os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    for p in (Path(__file__).resolve(),PLAN,Path(C.__file__),Path(D.__file__),D.HERE/'run_primary_direction_sequence.py'):
        D.checked(p)
    prior=C.pinned_result('352');proof=C.pinned_result('358')
    if not prior['all_pass'] or not proof['all_pass'] or len(proof['rows'])!=32:raise ValueError('successful352/358 required')
    for p,h in prior['input_sha256'].items():D.checked(Path(p),h)
    for p,h in proof['input_sha256'].items():D.checked(Path(p),h)
    old_host=D.checked(BASE/'prototype.cpp').decode();old_shader=D.checked(BASE/'prototype.comp.glsl').decode()
    header=D.checked(BASE/'n010_reference_snapshot.hpp');context=D.checked(BASE/'n010_reference_context.hpp')
    common=old_host[:old_host.index('static void execute(')]
    common=D.once(common,'uint32_t sizes[4]{},interval[4]{},seed[4]{};',
                  'uint32_t sizes[4]{},interval[4]{},seed[4]{},control[4]{};')
    physical=old_host[old_host.index('    if(scene.sampling'):old_host.index('    // Plan110: selection')]
    old_shape='    if(scene.width!=320 || scene.height!=180 || scene.max_bounces!=8 || scene.points.size()!=1)\n        throw std::runtime_error("prototype requires original C1 shape/depth/point count");'
    physical=D.once(physical,old_shape,'    if(!scene.width || !scene.height || scene.width>320 || scene.height>180 || scene.points.size()!=1)\n'
                    '        throw std::runtime_error("full backend requires bounded shape and one point");')
    physical=D.once(physical,'    const std::vector<uint32_t> selected={9640,9720,9800,9880,48040,48120,48200,48280};',
                    '    const auto selected=select_pixels(scene,mode);')
    pipeline=old_host[old_host.index('    std::array<VkDescriptorSetLayoutBinding,13>'):old_host.index('    auto kernel=c.kernel')]
    template=D.checked(D.HERE/'full_frame_whole_hybrid.cpp').decode()
    shader,shader_edits=generate_shader(old_shader)
    host=D.once(D.once(D.once(template,'// @N010_COMMON@',common),'// @N010_PHYSICAL@',physical),
                '// @N010_PIPELINE@',pipeline)
    identity=hashlib.sha256(header+context+host.encode()+shader.encode()).hexdigest()
    host=D.once(host,'@N010_BACKEND_ID@',identity)
    for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
    WORK.mkdir();(WORK/'n010_reference_snapshot.hpp').write_bytes(header);(WORK/'n010_reference_context.hpp').write_bytes(context)
    (WORK/'full.cpp').write_text(host);(WORK/'full.comp.glsl').write_text(shader)
    (WORK/'shader-edits.json').write_text(json.dumps(shader_edits,indent=2)+'\n')
    result=dict(schema='n010-full-frame-whole-hybrid-build/1',complete=False,all_pass=False,gpu_run=False,
        runtime_validated=False,reference_admission=False,accepted_timing=False,backend_id=identity,
        classification='FULL_FRAME_HYBRID_BUILD_ACQUIRING',input_sha256=D.INPUTS,attempts=[],
        cpu_header_and_context_byte_identical=True,shader_source_inverse_exact=True,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        tests='NOT_RUN; isolated compiler invocations only; no GPU/native acquisition')
    def save():OUTPUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    def compile_one(command,label):
        receipt=WORK/(label+'.resources.json')
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(120,)*2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),command=command))+'\n')
        row=dict(label=label,command=command,resource_receipt=str(receipt),terminal=False);result['attempts'].append(row);save()
        started=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            p=subprocess.run(command,capture_output=True,timeout=180,preexec_fn=limits)
            stdout,stderr=p.stdout,p.stderr;row.update(terminal=True,returncode=p.returncode)
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b'';row.update(terminal=True,returncode='NOT_EXPOSED_BY_TIMEOUTEXPIRED',failure='ELAPSED_GUARD_NO_RETRY')
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        (WORK/(label+'.stdout')).write_bytes(stdout);(WORK/(label+'.stderr')).write_bytes(stderr)
        row.update(elapsed_seconds=time.monotonic()-started,child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        a=json.loads(D.checked(receipt))
        if row['returncode']!=0 or a['cpu']!=[120]*2 or a['address_space']!=[4*1024**3]*2 or a['affinity']!=[31] or a['nice']!=15:
            raise ValueError('isolated compiler/resource failure; no retry')
    save()
    try:
        glslang=D.ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang';D.checked(glslang)
        helper=D.HERE.parent/'n010_comparison_readiness/compile_gpu_reference.py';D.checked(helper)
        sys.path.insert(0,str(helper.parent));from compile_gpu_reference import decorate
        compile_one([str(glslang),'-V','--target-env','vulkan1.2','-S','comp',str(WORK/'full.comp.glsl'),'-o',str(WORK/'raw.spv')],'shader')
        decorated,count=decorate((WORK/'raw.spv').read_bytes());(WORK/'full.spv').write_bytes(decorated);result['no_contraction_results']=count
        old_command=next(row['command'] for row in prior['attempts'] if row['label']=='host')
        command=[str(WORK/'full.cpp') if x==str(BASE/'prototype.cpp') else str(WORK/'phos-n010-whole-full')
                 if x==str(BASE/'phos-n010-whole-hybrid-prototype') else x for x in old_command]
        if str(WORK/'full.cpp') not in command or command[-1]!=str(WORK/'phos-n010-whole-full'):raise ValueError('host compiler source/output anchor differs')
        compile_one(command,'host')
        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)
        result.update(complete=True,all_pass=True,classification='FULL_FRAME_HYBRID_BUILD_COMPLETE_NO_RUNTIME_ADMISSION')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='FULL_FRAME_HYBRID_BUILD_FAILURE_RETAINED')
    result['payload_sha256']={str(p):C.sha(p) for p in WORK.iterdir() if p.is_file()};save()
    print(json.dumps({k:result.get(k) for k in ('complete','all_pass','classification','failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':main()

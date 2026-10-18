#!/usr/bin/env python3
"""Plan126: prepare private exact sample-state PT sources; no native work."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from prepare_tiled_pixel_pt import overlay

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
BASE = ROOT/'out/research/n010-comparison-readiness'
PLAN = RESULTS.parent/'experiments/126-exact-sample-continuation-pixel-pt.md'
WORK = BASE/'continuation-pixel-pt-source-v1'
OUTPUT = RESULTS/'400-continuation-pixel-pt-source-prepare.json'
INPUTS = {}


def checked(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed: '+str(path))
    INPUTS[str(path)] = digest
    return raw


PROGRESS = '''    uvec4 previous=pc.sample_begin==0u ? uvec4(0) : sample_states[id];
    if(pc.sample_begin!=0u && (previous.z!=pc.sample_begin || previous.w!=0u)) {
        sample_states[id].w=1u; return;
    }
'''

RESTORE = '''    if(pc.sample_begin==0u)rng=mix32(pc.seed^mix32(id));
    else {rng=previous.x;sum_indirect=uintBitsToFloat(previous.y);}
    for(uint sample_index=pc.sample_begin;sample_index<pc.sample_end;++sample_index) {'''

SAVE = '''    sample_states[id]=uvec4(rng,floatBitsToUint(sum_indirect),pc.sample_end,0u);
    if(pc.sample_end!=pc.spp)return;
    float indirect=sum_indirect/float(pc.spp);'''

STATE_READBACK = '''            std::vector<uint32_t> state_words(size_t(width)*height*4);
            context.download_device_buffer(sample_state,state_words.data(),state_words.size()*sizeof(uint32_t));
            for(size_t p=0;p<size_t(width)*height;++p) {
                float sum;std::memcpy(&sum,&state_words[4*p+1],sizeof(sum));
                if(state_words[4*p+2]!=spp || state_words[4*p+3]!=0 || !std::isfinite(sum) || sum<0)
                    throw std::runtime_error("incomplete or invalid sample continuation state");
            }
            const auto save_state=[&](const fs::path& path) {
                std::ofstream f(path,std::ios::binary);
                f.write(reinterpret_cast<const char*>(state_words.data()),state_words.size()*sizeof(uint32_t));
                if(!f)throw std::runtime_error("sample state readback write failed");
            };
            save_state(frame_out/"sample-state.bin");
            if(f+1==frames)save_state(out/"sample-state.bin");
'''


def main():
    if OUTPUT.exists() or WORK.exists():
        raise ValueError('refuse existing400/source; no retry')
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(__file__).with_name('prepare_tiled_pixel_pt.py')):
        raw = checked(path)
        if raw != subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))]):
            raise ValueError('commit exact generator/plan before preparation')
    prep = json.loads(checked(RESULTS/'389-tiled-pixel-pt-source-prepare.json',
        '46e5e05c0ad23fe37df62b3a097284c0be0612e947a8ec76cba024cc25a0a805'))
    for group in ('input_sha256','payload_sha256'):
        for name,digest in prep[group].items():
            checked(name,digest)
    diagnostic = json.loads(checked(RESULTS/'398-tiled-pt-first-call-probe.json'))
    if (not diagnostic['complete'] or not diagnostic['step_valid']
            or diagnostic['validation']['outcome']!='COMPLETED_TILE_OPERATIONAL_STOP_NO_VULKAN_CALL_FAILURE'):
        raise ValueError('retain observed first-tile diagnostic before continuation source')
    host = checked(BASE/'tiled-pixel-pt-source-v1/tiled_pixel_pt.cpp').decode()
    shader = checked(BASE/'tiled-pixel-pt-source-v1/tiled_pixel_pt.comp.glsl').decode()
    shader_edits = [
        ('uint pixel_begin; uint pixel_count; } pc;',
         'uint pixel_begin; uint pixel_count; uint sample_begin; uint sample_end; } pc;',1),
        ('const float PI=', 'layout(std430,binding=4) buffer SampleStates { uvec4 sample_states[]; };\nconst float PI=',1),
        ('    float nx=',PROGRESS+'    float nx=',1),
        ('        pixels[id]=vec4(0,0,0,1); return;',
         '        sample_states[id]=uvec4(0,0,pc.sample_end,0);\n'
         '        if(pc.sample_end==pc.spp)pixels[id]=vec4(0,0,0,1); return;',1),
        ('    rng=mix32(pc.seed^mix32(id));\n    for(uint sample_index=0u;sample_index<pc.spp;++sample_index) {',RESTORE,1),
        ('    float indirect=sum_indirect/float(pc.spp);',SAVE,1)]
    revised_shader = overlay(shader,shader_edits)
    sample_body = shader[shader.index('        vec3 origin=pos, n=normal; uint self=prim;'):shader.index('    float indirect=sum_indirect/float(pc.spp);')]
    if sample_body not in revised_shader:
        raise ValueError('complete per-sample transport/sum body changed')
    helpers = shader[shader.index('const float PI='):shader.index('void main()')]
    if helpers not in revised_shader:
        raise ValueError('transport/RNG helpers changed')
    host_edits = [
        ('uint32_t tile_pixels=64,pause_us=2000;', 'uint32_t tile_pixels=4096,pause_us=2000,sample_chunk=16;',1),
        ('            else if(arg=="--pause-us") pause_us=std::stoul(value);',
         '            else if(arg=="--sample-chunk") sample_chunk=std::stoul(value);\n'
         '            else if(arg=="--pause-us") pause_us=std::stoul(value);',1),
        ('tile_pixels>512 ||','tile_pixels>4096 || sample_chunk==0 || sample_chunk>16 ||',1),
        ('tile1..512, pause>=2ms','tile1..4096, chunk1..16, pause>=2ms',1),
        ('        std::array<i::I001Binding,4> bindings{{',
         '        auto sample_state=context.create_device_buffer(VkDeviceSize(width)*height*16,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);\n'
         '        std::array<i::I001Binding,5> bindings{{',1),
        ('            {3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&uniform}}};',
         '            {3,VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,&uniform},\n'
         '            {4,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,&sample_state}}};',1),
        ('bindings,20);','bindings,28);',2),
        ('            for(uint32_t pixel_begin=0;pixel_begin<pixels;) {',
         '            for(uint32_t sample_begin=0;sample_begin<spp;) {\n'
         '              const uint32_t sample_end=sample_begin+std::min(sample_chunk,spp-sample_begin);\n'
         '              for(uint32_t pixel_begin=0;pixel_begin<pixels;) {',1),
        ('const std::array<uint32_t,5> push{spp,vertices,image_seed,pixel_begin,count};',
         'const std::array<uint32_t,7> push{spp,vertices,image_seed,pixel_begin,count,sample_begin,sample_end};',1),
        ('if(pixel_begin==0)first_tick=begin_tick;','if(sample_begin==0 && pixel_begin==0)first_tick=begin_tick;',1),
        ('<<",\\\"pixel_begin\\\":"<<pixel_begin',
         '<<",\\\"sample_begin\\\":"<<sample_begin<<",\\\"sample_end\\\":"<<sample_end\n'
         '                    <<",\\\"pixel_begin\\\":"<<pixel_begin',1),
        ('                if(pixel_begin<pixels)std::this_thread::sleep_for(std::chrono::microseconds(pause_us));\n            }\n            last_envelope_gpu_us=',
         '                if(pixel_begin<pixels || sample_end<spp)std::this_thread::sleep_for(std::chrono::microseconds(pause_us));\n'
         '              }\n              sample_begin=sample_end;\n            }\n            last_envelope_gpu_us=',1),
        ('<<",\\\"pause_us\\\":"<<pause_us',
         '<<",\\\"pause_us\\\":"<<pause_us<<",\\\"sample_chunk\\\":"<<sample_chunk\n'
         '                 <<",\\\"sample_state_bytes\\\":"<<uint64_t(width)*height*16',1),
        ('            for(size_t c=0;c<3;++c) {',STATE_READBACK+'            for(size_t c=0;c<3;++c) {',1),
        ('        context.destroy_buffer(image);context.destroy_buffer(uniform);',
         '        context.destroy_buffer(sample_state);context.destroy_buffer(image);context.destroy_buffer(uniform);',1),
        ('n010-tiled-pixel-pt/1','n010-continuation-pixel-pt/1',1)]
    revised_host = overlay(host,host_edits)
    WORK.mkdir(parents=True)
    (WORK/'continuation_pixel_pt.cpp').write_text(revised_host)
    (WORK/'continuation_pixel_pt.comp.glsl').write_text(revised_shader)
    (WORK/'source-edits.json').write_text(json.dumps(dict(host=host_edits,shader=shader_edits),indent=2)+'\n')
    result = dict(schema='n010-continuation-pixel-pt-source-preparation/1',complete=True,
        source_preparation_valid=True,all_pass=False,compiled=False,gpu_run=False,
        accepted_timing=False,reference_admission=False,source_commit=commit,input_sha256=INPUTS,
        payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in WORK.iterdir()},
        whole_host_inverse_exact=True,whole_shader_inverse_exact=True,
        per_sample_transport_scalar_sum_body_byte_identical=True,transport_rng_helpers_byte_identical=True,
        sample_state_stride_bytes=16,additional_persistent_state_bytes_at_320x180=921600,
        classification='CONTINUATION_SOURCES_PREPARED_UNCOMPILED_UNEXECUTED_NO_ADMISSION',
        limitation='Source inverses/body identity do not prove floating runtime equivalence; full046 byte replay required.',
        tests='NOT_RUN; source preparation only, no native/compiler/GPU work')
    for name,digest in list(INPUTS.items()):
        checked(name,digest)
    with OUTPUT.open('x') as out:
        out.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__ == '__main__':
    main()

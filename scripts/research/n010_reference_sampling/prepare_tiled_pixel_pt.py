#!/usr/bin/env python3
"""Plan122: prepare an isolated spatially tiled pixel PT; never build/dispatch."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / 'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent / 'experiments/122-spatially-tiled-pixel-pt.md'
WORK = ROOT / 'out/research/n010-comparison-readiness/tiled-pixel-pt-source-v1'
OUTPUT = RESULTS / '389-tiled-pixel-pt-source-prepare.json'
HOST = ROOT / 'src/research/n010_comparison_readiness/pixel_pt_main.cpp'
SHADER = ROOT / 'shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl'
INPUTS = {}


def checked(path, expected=None):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('pinned source changed: ' + str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('source changed during preparation: ' + str(path))
    INPUTS[str(path)] = digest
    return raw


def overlay(original, edits):
    source = original
    for before, after, count in edits:
        if source.count(before) != count or after in source:
            raise ValueError('source overlay count differs: ' + before[:80])
        source = source.replace(before, after)
    restored = source
    for before, after, count in reversed(edits):
        if restored.count(after) != count:
            raise ValueError('source inverse count differs')
        restored = restored.replace(after, before)
    if restored != original:
        raise ValueError('whole source inverse differs')
    return source


TIMESTAMP_HELPER = r'''
// Read the selected queue's actual valid-bit count through the Vulkan loader.
// No display, device, driver, power or clock setting is changed.
uint32_t timestamp_bits(b::B002VulkanContext& context) {
    void* library=dlopen("libvulkan.so.1",RTLD_NOW|RTLD_LOCAL);
    if(!library)throw std::runtime_error("Vulkan loader unavailable for timestamp properties");
    const auto get_properties=reinterpret_cast<PFN_vkGetPhysicalDeviceQueueFamilyProperties>(
        dlsym(library,"vkGetPhysicalDeviceQueueFamilyProperties"));
    if(!get_properties) {dlclose(library);throw std::runtime_error("queue timestamp properties unavailable");}
    uint32_t count=0;get_properties(context.physical_device(),&count,nullptr);
    if(count==0 || count>256) {dlclose(library);throw std::runtime_error("queue family count");}
    std::vector<VkQueueFamilyProperties> properties(count);
    get_properties(context.physical_device(),&count,properties.data());
    dlclose(library);
    if(context.queue_family()>=count)throw std::runtime_error("selected queue missing");
    const auto bits=properties[context.queue_family()].timestampValidBits;
    if(bits==0 || bits>64)throw std::runtime_error("unsupported timestamp valid bits");
    return bits;
}
'''


TILED_RUN = r'''        const uint32_t valid_bits=timestamp_bits(context);
        const uint64_t timestamp_mask=valid_bits==64?UINT64_MAX:((uint64_t(1)<<valid_bits)-1);
        const double timestamp_period=double(context.timestamp_period_ns());
        if(!std::isfinite(timestamp_period) || timestamp_period<=0 ||
           std::ldexp(timestamp_period,int(valid_bits))/1e9<=180.0)
            throw std::runtime_error("timestamp wrap period does not cover bounded image");
        std::ofstream tile_times(out/"tile-timings.jsonl");tile_times<<std::setprecision(17);
        uint32_t image_call=0;
        double last_active_gpu_us=0,last_envelope_gpu_us=0,last_max_tile_gpu_us=0;
        const auto run_image=[&](uint32_t image_seed) {
            const auto image_started=Clock::now();
            const uint32_t image_index=image_call++;
            uint64_t first_tick=0,last_tick=0;
            last_active_gpu_us=last_envelope_gpu_us=last_max_tile_gpu_us=0;
            const uint32_t pixels=uint32_t(uint64_t(width)*height);
            for(uint32_t pixel_begin=0;pixel_begin<pixels;) {
                if(std::chrono::duration<double>(Clock::now()-image_started).count()>=180.0)
                    throw std::runtime_error("bounded image elapsed guard; partials retained");
                const uint32_t count=std::min(tile_pixels,pixels-pixel_begin);
                check(context.vk().resetFences(1,&fence));check(context.vk().resetCommandPool(pool,0));
                auto begin=phos::gi::detail::make_vk_info<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
                begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;check(context.vk().beginCommandBuffer(command,&begin));
                context.vk().cmdResetQueryPool(command,query,0,4);
                context.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
                const std::array<uint32_t,5> push{spp,vertices,image_seed,pixel_begin,count};
                stage->record(command,(count+63)/64,1,1,push.data(),sizeof(push));
                i::i001_compute_barrier(context,command);
                context.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);
                check(context.vk().endCommandBuffer(command));
                auto submit=phos::gi::detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
                submit.commandBufferCount=1;submit.pCommandBuffers=&command;
                check(context.vk().queueSubmit(context.queue(),1,&submit,fence));
                check(context.vk().waitForFences(1,&fence,VK_TRUE,500000000ULL));
                std::array<uint64_t,2> ticks{};
                check(context.vk().getQueryPoolResults(query,0,2,sizeof(ticks),ticks.data(),8,VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT));
                const uint64_t begin_tick=ticks[0]&timestamp_mask,end_tick=ticks[1]&timestamp_mask;
                const uint64_t duration_ticks=(end_tick-begin_tick)&timestamp_mask;
                const double gpu_us=double(duration_ticks)*timestamp_period/1000.0;
                if(pixel_begin==0)first_tick=begin_tick;
                last_tick=end_tick;last_active_gpu_us+=gpu_us;
                last_max_tile_gpu_us=std::max(last_max_tile_gpu_us,gpu_us);
                tile_times<<"{\"image_index\":"<<image_index<<",\"seed\":"<<image_seed
                    <<",\"pixel_begin\":"<<pixel_begin<<",\"pixel_count\":"<<count
                    <<",\"begin_tick\":"<<ticks[0]<<",\"end_tick\":"<<ticks[1]
                    <<",\"timestamp_valid_bits\":"<<valid_bits<<",\"timestamp_period_ns\":"<<timestamp_period
                    <<",\"gpu_us\":"<<gpu_us<<"}"<<std::endl;
                if(!tile_times || !std::isfinite(gpu_us) || gpu_us<=0 || gpu_us>250000.0)
                    throw std::runtime_error("tile time/receipt guard; partials retained");
                pixel_begin+=count;
                if(pixel_begin<pixels)std::this_thread::sleep_for(std::chrono::microseconds(pause_us));
            }
            last_envelope_gpu_us=double((last_tick-first_tick)&timestamp_mask)*timestamp_period/1000.0;
            if(!std::isfinite(last_envelope_gpu_us) || last_envelope_gpu_us<last_active_gpu_us ||
               std::chrono::duration<double>(Clock::now()-image_started).count()>=180.0)
                throw std::runtime_error("image envelope/elapsed guard");
            n::NeutralWork::last_gpu_us=0;
            return last_envelope_gpu_us;
        };
'''


def main():
    if OUTPUT.exists() or WORK.exists():
        raise ValueError('refuse existing source preparation; no overwrite/retry')
    os.sched_setaffinity(0, {31})
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 15:
        os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    for path in (Path(__file__).resolve(), PLAN):
        checked(path)
    host = checked(HOST, 'c2f0bc8d517e29fd3ec33641900aed47b1310b3161e2f8b61e288c8b7b2c429c').decode()
    shader = checked(SHADER, 'ddb81baa0b701f96d78ffe297db589290d3fe4c2d6965a4df655c47a4a23d1c2').decode()
    baseline = json.loads(checked(RESULTS/'046-calibration-quiet-sizing.json',
        '2ab654662ffdef9b873179d95a9142eea7e18ad0635cec37601c51f0f828d36d'))
    shader_edits = [
        ('uint spp; uint vertices; uint seed; uint reserved;',
         'uint spp; uint vertices; uint seed; uint pixel_begin; uint pixel_count;', 1),
        ('    uvec2 px=gl_GlobalInvocationID.xy;\n',
         '    uint local_pixel=gl_WorkGroupID.x*64u+gl_LocalInvocationIndex;\n'
         '    if(local_pixel>=pc.pixel_count)return;\n'
         '    uint linear_pixel=pc.pixel_begin+local_pixel;\n'
         '    uvec2 px=uvec2(linear_pixel%p.counts.y,linear_pixel/p.counts.y);\n', 1)]
    revised_shader = overlay(shader, shader_edits)
    if shader.split('    float nx=',1)[1] != revised_shader.split('    float nx=',1)[1]:
        raise ValueError('per-pixel camera/RNG/sample/transport body changed')
    if shader.split('const float PI=',1)[1].split('void main()',1)[0] != revised_shader.split('const float PI=',1)[1].split('void main()',1)[0]:
        raise ValueError('transport/RNG helper body changed')
    run_begin = host.index('        const auto run_image=')
    run_end = host.index('        for(uint32_t f=0;f<frames;++f)', run_begin)
    host_edits = [
        ('#include <vector>', '#include <vector>\n#include <algorithm>\n#include <cmath>\n#include <thread>\n#include <dlfcn.h>', 1),
        ('int main(int argc,char** argv) {', TIMESTAMP_HELPER+'\nint main(int argc,char** argv) {', 1),
        ('        std::string family="pixel-pt";',
         '        uint32_t tile_pixels=64,pause_us=2000;\n        std::string family="pixel-pt";', 1),
        ('            else if(arg=="--family") family=value;',
         '            else if(arg=="--tile-pixels") tile_pixels=std::stoul(value);\n'
         '            else if(arg=="--pause-us") pause_us=std::stoul(value);\n'
         '            else if(arg=="--family") family=value;', 1),
        ('frames>256)', 'frames>5)', 1),
        ('        std::vector<uint32_t> doses;',
         '        if(family!="pixel-pt" || !calibration_doses.empty() || tile_pixels==0 || tile_pixels>512 ||\n'
         '           pause_us<2000 || pause_us>1000000)\n'
         '            throw std::runtime_error("tiled pixel-PT only; no calibration, tile1..512, pause>=2ms");\n'
         '        std::vector<uint32_t> doses;', 1),
        ('        auto width=source.width,height=source.height;',
         '        auto width=source.width,height=source.height;\n'
         '        if(uint64_t(width)*height==0 || uint64_t(width)*height>UINT32_MAX)\n'
         '            throw std::runtime_error("pixel indexing bound");', 1),
        ('bindings,16);', 'bindings,20);', 2),
        (host[run_begin:run_end], TILED_RUN, 1),
        ('n010-pixel-pt/1', 'n010-tiled-pixel-pt/1', 1),
        ('complete pixel Renderer: uniform/geometry uploads + BLAS/TLAS UPDATE + primary/NEE/all bounces/composite; initial setup/readback separate',
         'tiled pixel Renderer: upload/update GPU segments plus full image timestamp envelope including cooperative host gaps; active GPU sum and CPU wall separate; uncalibrated', 1)]
    # Append the metrics at the exact original source anchor, outside shaders.
    host_edits.append(('<<",\\\"known_work_gpu_us\\\":"<<n::NeutralWork::last_gpu_us',
        '<<",\\\"image_active_gpu_us\\\":"<<last_active_gpu_us'
        '<<",\\\"image_envelope_gpu_us\\\":"<<last_envelope_gpu_us'
        '<<",\\\"active_gpu_us\\\":"<<last_active_gpu_us+maintenance_gpu'
        '<<",\\\"max_tile_gpu_us\\\":"<<last_max_tile_gpu_us'
        '<<",\\\"tile_pixels\\\":"<<tile_pixels<<",\\\"pause_us\\\":"<<pause_us'
        '<<",\\\"known_work_gpu_us\\\":"<<n::NeutralWork::last_gpu_us', 1))
    revised_host = overlay(host, host_edits)
    WORK.mkdir(parents=True)
    (WORK/'tiled_pixel_pt.cpp').write_text(revised_host)
    (WORK/'tiled_pixel_pt.comp.glsl').write_text(revised_shader)
    (WORK/'source-edits.json').write_text(json.dumps(dict(host=host_edits,shader=shader_edits),indent=2)+'\n')
    result = dict(schema='n010-tiled-pixel-pt-source-preparation/1', complete=True,
        source_preparation_valid=True, all_pass=False, gpu_run=False, compiled=False,
        accepted_timing=False, reference_admission=False,
        classification='SOURCE_PREPARED_UNCOMPILED_UNEXECUTED_NO_ADMISSION',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=INPUTS, payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in WORK.iterdir()},
        whole_host_inverse_exact=True, whole_shader_inverse_exact=True,
        per_pixel_camera_rng_transport_sum_body_byte_identical=True,
        validation_baselines=[dict(boundary=r['boundary'],command=r['evidence']['command'],
                                   images=r['evidence']['payloads'][0]['images'])
            for r in baseline['rows'] if r['boundary']['id'] in ('C1-pt-B8','C7-pt-B8')],
        limitation='Source proof only; floating GPU equivalence, tile duration, full source/dynamic '
                   'coverage, memory/runtime and any timing conclusion are unverified.',
        tests='NOT_RUN; source preparation only, no compiler/GPU/numerical execution')
    for path, digest in list(INPUTS.items()):
        checked(Path(path), digest)
    with OUTPUT.open('x') as out:
        out.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__=='__main__':
    main()

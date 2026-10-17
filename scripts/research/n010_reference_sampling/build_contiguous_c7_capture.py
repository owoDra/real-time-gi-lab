#!/usr/bin/env python3
"""Plan 063: compile an isolated static C7 command-batch fixture; no GPU run."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / 'n010_comparison_readiness'))
from run_primary_direction_sequence import require_no_other_research_worker
from build_packed_readback_capture import overlay

RESULTS = ROOT / 'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent / 'experiments/063-contiguous-c7-command-batch-diagnosis.md'
PARENT = ROOT / 'out/research/n010-comparison-readiness/packed-readback-build-v1'
WORK = PARENT.parent / 'contiguous-c7-build-v1'
OUTPUT = RESULTS / '204-contiguous-c7-fixture-build.json'
INPUTS = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    if expected is not None and h != expected:
        raise ValueError('input identity differs: ' + str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != h:
        raise ValueError('input changed: ' + str(path))
    INPUTS[str(path)] = h
    return raw


AUDIT = r'''
struct N010BatchAudit {
    inline static size_t recorded{}, consumed{}, submits{}, waits{}, stride{}, alignment{}, range{};
    inline static double submit_wait_wall_us{};
    static void save(const std::filesystem::path& out,size_t expected) {
        if(recorded!=expected||consumed!=expected||submits!=1||waits!=1)
            throw std::runtime_error("incomplete contiguous batch");
        std::ofstream f(out/"contiguous-batch.json");
        f<<"{\"complete\":true,\"recorded_frames\":"<<recorded<<",\"consumed_frames\":"<<consumed
         <<",\"queue_submit_calls\":"<<submits<<",\"fence_wait_calls\":"<<waits
         <<",\"uniform_stride\":"<<stride<<",\"uniform_alignment\":"<<alignment
         <<",\"uniform_range\":"<<range<<",\"submit_wait_wall_us\":"<<submit_wait_wall_us
         <<",\"scope\":\"static C7 batch only; CPU cached calls are not independent frame wall times\",\"frames\":[";
        for(size_t i=0;i<recorded;++i) {
            if(i)f<<",";
            f<<"{\"index\":"<<i<<",\"frame_id\":"<<i+1<<",\"uniform_offset\":"<<4096*i
             <<",\"query_first\":"<<24*i<<",\"query_written_count\":18}";
        }
        f<<"]}\n";
        if(!f)throw std::runtime_error("batch receipt write failed");
    }
};
'''

UNIFORM_INIT = r'''
        if(std::getenv("PHOS_N010_CONTIGUOUS_C7")) {
            if(!std::getenv("PHOS_N010_PACKED_CALIBRATION_READBACK")||
               !std::getenv("PHOS_N010_MINIMAL_CALIBRATION_READBACK")||
               !std::getenv("PHOS_N010_CALIBRATION")||
               options.scenario!=I001Scenario::Static||options.variant!=I001Variant::LaneEFinalHwrt)
                fail("contiguous fixture requires static C7 calibration");
            void* library=dlopen("libvulkan.so.1",RTLD_NOW|RTLD_LOCAL);
            if(!library)fail("batch device property loader");
            auto properties=reinterpret_cast<PFN_vkGetPhysicalDeviceProperties>(dlsym(library,"vkGetPhysicalDeviceProperties"));
            if(!properties)fail("batch device property function");
            VkPhysicalDeviceProperties actual{};properties(context.physical_device(),&actual);dlclose(library);
            if(!actual.limits.minUniformBufferOffsetAlignment||4096%actual.limits.minUniformBufferOffsetAlignment||
               sizeof(params)>4096||sizeof(params)>actual.limits.maxUniformBufferRange)
                fail("batch actual uniform limits incompatible");
            n010_batch_uniform_bytes=sizeof(params);
            phos::gi::research::n010::N010BatchAudit::stride=4096;
            phos::gi::research::n010::N010BatchAudit::alignment=actual.limits.minUniformBufferOffsetAlignment;
            phos::gi::research::n010::N010BatchAudit::range=sizeof(params);
        }
'''

BATCH_ENTRY = r'''
        if(std::getenv("PHOS_N010_CONTIGUOUS_C7")&&!n010_batch_recording) {
            if(target_state)fail("batch target state unsupported");
            if(n010_batch_commands.empty()) {
                const char* path=std::getenv("PHOS_N010_BATCH_DOSES");
                if(!path)fail("batch dose path missing");
                std::ifstream f(path);uint32_t dose{};
                while(f>>dose)n010_batch_doses.push_back(dose);
                if(!f.eof()||n010_batch_doses.empty()||n010_batch_doses.size()>256)
                    fail("batch dose file invalid");
                n010_batch_recording=true;
                for(size_t i=0;i<n010_batch_doses.size();++i) {
                    n010_batch_index=i;
                    n010_batch_dynamic_offset=uint32_t(4096*i);
                    const auto dose_text=std::to_string(n010_batch_doses[i]);
                    setenv("PHOS_N010_CALIBRATION_DOSE",dose_text.c_str(),1);
                    (void)run_frame(false);
                    const auto* written=static_cast<const unsigned char*>(uniform.mapped)+4096*i;
                    if(params.limits[3]!=i+1||std::memcmp(written,&params,sizeof(params)))
                        fail("batch original frame parameters not retained");
                    ++phos::gi::research::n010::N010BatchAudit::recorded;
                }
                if(n010_batch_commands.size()!=n010_batch_doses.size())fail("batch command count differs");
                auto submit=detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
                submit.commandBufferCount=uint32_t(n010_batch_commands.size());
                submit.pCommandBuffers=n010_batch_commands.data();
                const auto start=std::chrono::steady_clock::now();
                if(context.vk().queueSubmit(context.queue(),1,&submit,fence)!=VK_SUCCESS)fail("batch submit");
                ++phos::gi::research::n010::N010BatchAudit::submits;
                if(context.vk().waitForFences(1,&fence,VK_TRUE,UINT64_MAX)!=VK_SUCCESS)fail("batch fence wait");
                ++phos::gi::research::n010::N010BatchAudit::waits;
                phos::gi::research::n010::N010BatchAudit::submit_wait_wall_us=
                    std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count();
                n010_batch_recording=false;
            }
            if(n010_batch_consumed>=n010_batch_doses.size())fail("batch result consumed twice");
            n010_batch_index=n010_batch_consumed++;
            frame_id=uint32_t(n010_batch_index+1);
            std::memcpy(&params,static_cast<const unsigned char*>(uniform.mapped)+4096*n010_batch_index,sizeof(params));
            if(params.limits[3]!=frame_id)fail("batch decoded frame ID differs");
            ++phos::gi::research::n010::N010BatchAudit::consumed;
            return n010_decode_frame({});
        }
'''

BETWEEN = r'''
        if(n010_batch_recording) {
            auto dependency=detail::make_vk_info<VkMemoryBarrier>(VK_STRUCTURE_TYPE_MEMORY_BARRIER);
            dependency.srcAccessMask=VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT;
            dependency.dstAccessMask=VK_ACCESS_MEMORY_READ_BIT|VK_ACCESS_MEMORY_WRITE_BIT;
            context.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,0,1,&dependency,0,nullptr,0,nullptr);
        }
'''


def generated_sources(originals):
    include = ('#include "n010_packed_neutral_work.hpp"', '#include "n010_contiguous_neutral_work.hpp"')
    runtime = originals['runtime']
    # Extract the original CPU result decoder intact. Its timestamp reads alone
    # acquire per-frame ranges; no original timing expression is reimplemented.
    decoder_start = '        std::array<std::uint64_t, 18> timestamps{};'
    decoder_stop = '\n    [[nodiscard]] I001Quality validate_last_frame() {'
    if runtime.count(decoder_start) != 1 or runtime.count(decoder_stop) != 1:
        raise ValueError('original decoder anchor differs')
    old_decoder = runtime.split(decoder_start, 1)[1].split(decoder_stop, 1)[0]
    pairs = {
        'runtime': [include,
            ('#include <algorithm>\n#include <array>\n#include <bit>', '#include <algorithm>\n#include <dlfcn.h>\n#include <array>\n#include <bit>'),
            ('namespace phos::gi::research::integration {\nnamespace {\n\nnamespace lane_a',
             'namespace phos::gi::research::integration {\nextern thread_local uint32_t n010_batch_dynamic_offset;\nextern size_t n010_batch_uniform_bytes;\nnamespace {\n\nnamespace lane_a'),
            ('    B002Buffer n010_packed_readback{};', '''    B002Buffer n010_packed_readback{};
    bool n010_batch_recording{};
    size_t n010_batch_index{},n010_batch_consumed{};
    std::vector<uint32_t> n010_batch_doses;
    std::vector<VkCommandBuffer> n010_batch_commands;
    VkDeviceSize n010_frame_stride() const {return 64+image.size+65536;}
    VkDeviceSize n010_readback_offset() const {return std::getenv("PHOS_N010_CONTIGUOUS_C7")?n010_frame_stride()*n010_batch_index:0;}
    uint32_t n010_query_base() const {return std::getenv("PHOS_N010_CONTIGUOUS_C7")?uint32_t(24*n010_batch_index):0;}
'''),
            ('        uniform = context.create_host_buffer(\n            sizeof(params),', UNIFORM_INIT + '''
        uniform = context.create_host_buffer(
            std::getenv("PHOS_N010_CONTIGUOUS_C7")?VkDeviceSize(4096*256):sizeof(params),'''),
            ('        query_info.queryCount = kQueryCount;',
             '        query_info.queryCount = kQueryCount*(std::getenv("PHOS_N010_CONTIGUOUS_C7")?256:1);'),
            ('        params = next;\n        std::memcpy(uniform.mapped, &params, sizeof(params));',
             '        params = next;\n        std::memcpy(static_cast<unsigned char*>(uniform.mapped)+(n010_batch_recording?4096*n010_batch_index:0), &params, sizeof(params));'),
            ('    [[nodiscard]] I001FrameResult run_frame(bool target_state) {',
             '    [[nodiscard]] I001FrameResult run_frame(bool target_state) {' + BATCH_ENTRY),
            ('            const VkDeviceSize bytes=64+image.size+65536;',
             '''            const VkDeviceSize bytes=n010_frame_stride()*(n010_batch_recording?n010_batch_doses.size():1);
            if(bytes>256U*1024U*1024U)fail("batch packed storage exceeds bound");'''),
            ('            if(bytes>16U*1024U*1024U||image.size!=',
             '            if(n010_frame_stride()>16U*1024U*1024U||image.size!='),
            ('        context.vk().resetFences(1, &fence);\n        context.vk().resetCommandPool(command_pool, 0);\n\n',
             '        if(!n010_batch_recording||n010_batch_index==0) {\n        context.vk().resetFences(1, &fence);\n        context.vk().resetCommandPool(command_pool, 0);\n        }\n\n'),
            ('        context.vk().cmdResetQueryPool(command, query_pool, 0, kQueryCount);',
             BETWEEN + '\n        context.vk().cmdResetQueryPool(command, query_pool, n010_query_base(), kQueryCount);'),
            ('command, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, query_pool, index);',
             'command, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, query_pool, n010_query_base()+index);'),
            ('                if(offset+bytes>n010_packed_readback.size)fail("packed copy overflow");\n                const VkBufferCopy region{0,offset,bytes};',
             '                offset+=n010_readback_offset();\n                if(offset+bytes>n010_packed_readback.size)fail("packed copy overflow");\n                const VkBufferCopy region{0,offset,bytes};'),
            ('        auto submit = detail::make_vk_info<VkSubmitInfo>(\n            VK_STRUCTURE_TYPE_SUBMIT_INFO);\n        submit.commandBufferCount = 1;\n        submit.pCommandBuffers = &command;\n        if (context.vk().queueSubmit(context.queue(), 1, &submit, fence) != VK_SUCCESS) {',
             '''        if(n010_batch_recording) {n010_batch_commands.push_back(command);return {};}
        auto submit = detail::make_vk_info<VkSubmitInfo>(
            VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &command;
        if (context.vk().queueSubmit(context.queue(), 1, &submit, fence) != VK_SUCCESS) {'''),
            (decoder_start + old_decoder + decoder_stop,
             '        return n010_decode_frame(dynamic_update);\n    }\n\n    I001FrameResult n010_decode_frame(const DynamicUpdateStats& dynamic_update) {\n' + decoder_start + old_decoder + decoder_stop),
            ('query_pool, 0, static_cast<std::uint32_t>(timestamps.size()),',
             'query_pool, n010_query_base(), static_cast<std::uint32_t>(timestamps.size()),'),
            ('std::memcpy(counter_values.data(),n010_packed_readback.mapped,sizeof(counter_values));',
             'std::memcpy(counter_values.data(),static_cast<const unsigned char*>(n010_packed_readback.mapped)+n010_readback_offset(),sizeof(counter_values));'),
            ('static_cast<const unsigned char*>(n010_packed_readback.mapped)+32,',
             'static_cast<const unsigned char*>(n010_packed_readback.mapped)+n010_readback_offset()+32,'),
            ('static_cast<const unsigned char*>(impl_->n010_packed_readback.mapped)+64,',
             'static_cast<const unsigned char*>(impl_->n010_packed_readback.mapped)+impl_->n010_readback_offset()+64,'),
            ('static_cast<const unsigned char*>(impl_->n010_packed_readback.mapped)+64+impl_->image.size);',
             'static_cast<const unsigned char*>(impl_->n010_packed_readback.mapped)+impl_->n010_readback_offset()+64+impl_->image.size);')],
        'capture': [include,
            ('            N010DeferredImages deferred(doses.size());', '''            if(std::getenv("PHOS_N010_CONTIGUOUS_C7")) {
                if(target||topology||backend!="hwrt"||scenario!="static")throw std::runtime_error("batch only supports static C7");
            }
            N010DeferredImages deferred(doses.size());'''),
            ('            if(!target) {\n                stable=', '''            if(std::getenv("PHOS_N010_CONTIGUOUS_C7")) {
                if(target||topology||backend!="hwrt"||scenario!="static")throw std::runtime_error("batch only supports static C7");
                setenv("PHOS_N010_BATCH_DOSES",fs::absolute(calibration_doses).c_str(),1);
            }
            if(!target) {
                stable='''),
            ('            if(std::getenv("PHOS_N010_PACKED_CALIBRATION_READBACK")) phos::gi::research::n010::N010PackedScratchSpool::flush(out);',
             '            if(std::getenv("PHOS_N010_CONTIGUOUS_C7")) phos::gi::research::n010::N010BatchAudit::save(out,doses.size());\n            if(std::getenv("PHOS_N010_PACKED_CALIBRATION_READBACK")) phos::gi::research::n010::N010PackedScratchSpool::flush(out);')],
        'neutral': [('class NeutralWork {', AUDIT + '\nclass NeutralWork {')],
        'compute': [
            ('#include <array>', '#include <array>\n#include <map>\n#include <cstdlib>'),
            ('namespace phos::gi::research::integration {', '''namespace phos::gi::research::integration {
thread_local uint32_t n010_batch_dynamic_offset{};
size_t n010_batch_uniform_bytes{};
static std::map<const I001ComputeStage*,bool> n010_batch_uniforms;
'''),
            ('    std::vector<VkDescriptorSetLayoutBinding> layout;', '''    std::vector<I001Binding> adjusted;
    if(std::getenv("PHOS_N010_CONTIGUOUS_C7")) {
        adjusted.assign(bindings.begin(),bindings.end());
        size_t count{};
        for(auto& b:adjusted)if(b.type==VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER) {b.type=VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER_DYNAMIC;++count;}
        if(count>1)fail("batch stage has multiple uniform bindings");
        n010_batch_uniforms[this]=count==1;bindings=adjusted;
    }
    std::vector<VkDescriptorSetLayoutBinding> layout;'''),
            ('} else if (binding.type == VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER) {',
             '} else if (binding.type == VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER || binding.type == VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER_DYNAMIC) {'),
            ('{VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, pool_counts[1]});',
             '{std::getenv("PHOS_N010_CONTIGUOUS_C7")?VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER_DYNAMIC:VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, pool_counts[1]});'),
            ('                binding.buffer->size,',
             '                binding.type==VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER_DYNAMIC?n010_batch_uniform_bytes:binding.buffer->size,'),
            ('I001ComputeStage::~I001ComputeStage() {',
             'I001ComputeStage::~I001ComputeStage() {\n    n010_batch_uniforms.erase(this);'),
            ('        &descriptor_set_,\n        0,\n        nullptr);',
             '''        &descriptor_set_,
        n010_batch_uniforms.contains(this)&&n010_batch_uniforms.at(this)?1:0,
        n010_batch_uniforms.contains(this)&&n010_batch_uniforms.at(this)?&n010_batch_dynamic_offset:nullptr);''')]
    }
    generated = {k: overlay(originals[k], pairs[k]) for k in originals}
    start = '        stamp(12);'
    stop = '        stamp(15);'
    if originals['runtime'].split(start, 1)[1].split(stop, 1)[0] != generated['runtime'].split(start, 1)[1].split(stop, 1)[0]:
        raise ValueError('original timed recording changed')
    start = '        const auto period = context.timestamp_period_ns();'
    stop = '        result.stats.work_items = counter_values[0];'
    if originals['runtime'].split(start, 1)[1].split(stop, 1)[0] != generated['runtime'].split(start, 1)[1].split(stop, 1)[0]:
        raise ValueError('original timing expressions changed')
    return generated, pairs


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing batch fixture')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    read(__file__)
    read(PLAN)
    read(HERE / 'build_packed_readback_capture.py')
    parent = json.loads(read(RESULTS / '199-packed-readback-fixture-build.json',
                            '7780bec0e9e2ec7f6da930a9b81fad01384e3620c5e39091f9a838e2c68dc108'))
    if not parent['complete'] or not parent['all_pass']:
        raise ValueError('complete parent build required')
    for p, h in parent['input_sha256'].items():
        read(p, h)
    names = dict(runtime='minimal_runtime.cpp', capture='minimal_capture.cpp',
                 neutral='n010_packed_neutral_work.hpp', compute='batch_compute.cpp')
    originals = {k: read(PARENT / name, parent['generated_sha256'][name]).decode()
                 for k, name in names.items() if k != 'compute'}
    originals['compute'] = read(ROOT / 'src/research/lane_n_end_to_end_renderer/imported/integration/i001_compute.cpp').decode()
    generated, pairs = generated_sources(originals)
    WORK.mkdir()
    names['neutral'] = 'n010_contiguous_neutral_work.hpp'
    for k, source in generated.items():
        (WORK / names[k]).write_text(source)
    first = [[a.replace(str(PARENT), str(WORK)) for a in s['command']] for s in parent['steps'][:2]]
    compute = [a.replace('runtime.o', 'compute.o').replace('minimal_runtime.cpp', 'batch_compute.cpp') for a in first[0]]
    link = [a.replace(str(PARENT), str(WORK)) for a in parent['steps'][2]['command']]
    old_compute = next(a for a in link if a.endswith('/imported/integration/i001_compute.cpp.o'))
    link[link.index(old_compute)] = str(WORK / 'compute.o')
    steps = first + [compute, link]
    for args in steps:
        for a in args:
            if a.endswith(('.o', '.a')) and not a.startswith(str(WORK)):
                read(Path(a) if Path(a).is_absolute() else ROOT / 'build/n009' / a)
    result = dict(schema='n010-contiguous-c7-fixture-build/1', complete=False, all_pass=False,
                  gpu_run=False, source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  input_sha256=INPUTS, whole_parent_source_inverses_exact=True,
                  timed_gpu_recording_through_stamp15_byte_identical=True,
                  timing_expressions_byte_identical=True, compute_class_headers_unchanged=True,
                  overlay_pairs={k: [dict(old=a,new=b) for a,b in v] for k,v in pairs.items()},
                  scope='static C7 calibration only; no all-boundary or reference or timing admission',
                  tests='NOT_RUN; isolated scientific build only', steps=[])
    def save():
        OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for i, args in enumerate(steps):
            receipt = WORK / f'step-{i}.resources.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(120,120))
                resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=300,command=args))+'\n')
            attempt = dict(command=args,cwd=str(ROOT/'build/n009'))
            result['steps'].append(attempt)
            save()
            started = time.monotonic()
            proc = subprocess.run(args,cwd=ROOT/'build/n009',capture_output=True,text=True,timeout=300,preexec_fn=limits)
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-started,stdout=proc.stdout,stderr=proc.stderr,receipt_sha256=sha(receipt))
            save()
            actual = json.loads(read(receipt))
            if actual['cpu'] != [120,120] or actual['address_space'] != [8*1024**3]*2 or len(actual['affinity']) != 1 or actual['nice'] != 15:
                raise ValueError('actual compiler resource limits differ')
            if proc.returncode:
                raise ValueError('compile/link failed; no retry')
        for p,h in list(INPUTS.items()):
            read(p,h)
        result['generated_sha256'] = {p.name: sha(p) for p in WORK.iterdir() if p.is_file()}
        result.update(all_pass=True,active_inputs_byte_unchanged=True)
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        result['failure'] = str(e)
    result['complete'] = True
    save()
    print(json.dumps(dict(complete=True,all_pass=result['all_pass'],failure=result.get('failure'))))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

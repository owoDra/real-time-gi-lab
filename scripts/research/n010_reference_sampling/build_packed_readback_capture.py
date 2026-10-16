#!/usr/bin/env python3
"""Plan 060: isolated packed diagnostic readback; no GPU dispatch."""
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
sys.path.insert(0,str(HERE.parent/'n010_comparison_readiness'))
from run_primary_direction_sequence import require_no_other_research_worker

RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/060-packed-readback-cadence-diagnosis.md'
PARENT = ROOT/'out/research/n010-comparison-readiness/deferred-image-calibration-build-v1'
WORK = ROOT/'out/research/n010-comparison-readiness/packed-readback-build-v1'
OUTPUT = RESULTS/'199-packed-readback-fixture-build.json'
INPUTS = {}


def read(path,expected=None):
    path=Path(path);raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest()
    if expected is not None and h!=expected:raise ValueError('input identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)]!=h:raise ValueError('input changed: '+str(path))
    INPUTS[str(path)]=h
    return raw


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def overlay(original,pairs):
    source=original
    for old,new in pairs:
        if source.count(old)!=1:raise ValueError('packed source anchor differs: '+old[:80])
        source=source.replace(old,new)
    restored=source
    for old,new in reversed(pairs):
        if restored.count(new)!=1:raise ValueError('packed inverse anchor differs')
        restored=restored.replace(new,old)
    if restored!=original:raise ValueError('whole parent inverse differs')
    return source


SPOOL=r'''
struct N010PackedScratchSpool {
    struct Entry {std::filesystem::path path;std::vector<unsigned char> bytes;};
    inline static std::vector<Entry> entries;
    inline static size_t peak{},live{},retained{};
    static constexpr size_t limit=16U*1024U*1024U;
    static void retain(const std::filesystem::path& path,const unsigned char* bytes) {
        if(entries.size()>=256)throw std::runtime_error("scratch record bound");
        Entry e{path,std::vector<unsigned char>(bytes,bytes+65536)};
        const size_t capacity=e.bytes.capacity();
        if(capacity>limit-live)throw std::runtime_error("scratch capacity bound");
        entries.push_back(std::move(e));live+=capacity;peak=std::max(peak,live);++retained;
    }
    static void flush(const std::filesystem::path& out) {
        size_t written=0;
        for(auto& e:entries) {
            std::ofstream f(e.path,std::ios::binary);
            f.write(reinterpret_cast<const char*>(e.bytes.data()),e.bytes.size());
            if(!f)throw std::runtime_error("packed scratch write failure");
            live-=e.bytes.capacity();std::vector<unsigned char>().swap(e.bytes);++written;
        }
        entries.clear();
        if(live||written!=retained)throw std::runtime_error("scratch flush incomplete");
        std::ofstream f(out/"packed-scratch-spool.json");
        f<<"{\"complete\":true,\"retained_frames\":"<<retained<<",\"written_frames\":"<<written
         <<",\"capacity_peak_bytes\":"<<peak<<",\"capacity_limit_bytes\":"<<limit
         <<",\"capacity_bytes_after_flush\":"<<live<<"}\n";
        if(!f)throw std::runtime_error("scratch receipt failure");
    }
};
'''

PACK_INIT=r'''
        if(std::getenv("PHOS_N010_PACKED_CALIBRATION_READBACK")) {
            if(!n010_neutral||!std::getenv("PHOS_N010_MINIMAL_CALIBRATION_READBACK"))
                fail("packed readback requires explicit minimal calibration");
            const VkDeviceSize bytes=64+image.size+65536;
            if(bytes>16U*1024U*1024U||image.size!=VkDeviceSize(params.counts[1])*params.counts[2]*16U)
                fail("packed readback bound/shape");
            if(!n010_packed_readback.buffer)
                n010_packed_readback=context.create_host_buffer(bytes,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
            if(n010_packed_readback.size!=bytes)fail("packed image size changed");
        }
'''

PACK_RECORD=r'''
        if(n010_packed_readback.buffer) {
            auto before=detail::make_vk_info<VkMemoryBarrier>(VK_STRUCTURE_TYPE_MEMORY_BARRIER);
            before.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;before.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
            context.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                VK_PIPELINE_STAGE_TRANSFER_BIT,0,1,&before,0,nullptr,0,nullptr);
            auto copy=[&](VkBuffer source,VkDeviceSize bytes,VkDeviceSize offset) {
                if(offset+bytes>n010_packed_readback.size)fail("packed copy overflow");
                const VkBufferCopy region{0,offset,bytes};
                context.vk().cmdCopyBuffer(command,source,n010_packed_readback.buffer,1,&region);
            };
            copy(counters.buffer,24,0);copy(storage_stats.buffer,16,32);
            copy(image.buffer,image.size,64);copy(n010_neutral->packed_source_buffer(),65536,64+image.size);
            auto after=detail::make_vk_info<VkMemoryBarrier>(VK_STRUCTURE_TYPE_MEMORY_BARRIER);
            after.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;after.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
            context.vk().cmdPipelineBarrier(command,VK_PIPELINE_STAGE_TRANSFER_BIT,
                VK_PIPELINE_STAGE_HOST_BIT,0,1,&after,0,nullptr,0,nullptr);
        }
'''


def generated_sources(originals):
    include=('#include "neutral_work.hpp"','#include "n010_packed_neutral_work.hpp"')
    counter='        context.download_device_buffer(counters, counter_values.data(), sizeof(counter_values));'
    storage='        context.download_device_buffer(storage_stats, storage_values.data(), sizeof(storage_values));'
    download='''    impl_->context.download_device_buffer(
        impl_->image,
        out.image_rgba.data(),
        out.image_rgba.size() * sizeof(float));'''
    scratch='        impl_->n010_neutral->save(std::filesystem::path(directory)/"neutral-work.bin");'
    pairs={
        'runtime':[include,
            ('    B002Buffer storage_slots{}, storage_stats{};',
             '    B002Buffer storage_slots{}, storage_stats{};\n    B002Buffer n010_packed_readback{};'),
            ('        n010_neutral.reset();','        n010_neutral.reset();\n        context.destroy_buffer(n010_packed_readback);'),
            ('    [[nodiscard]] I001FrameResult run_frame(bool target_state) {',
             '    [[nodiscard]] I001FrameResult run_frame(bool target_state) {'+PACK_INIT),
            ('        stamp(15);','        stamp(15);'+PACK_RECORD),
            (counter,'        if(n010_packed_readback.mapped) std::memcpy(counter_values.data(),n010_packed_readback.mapped,sizeof(counter_values));\n        else '+counter.strip()),
            (storage,'        if(n010_packed_readback.mapped) std::memcpy(storage_values.data(),static_cast<const unsigned char*>(n010_packed_readback.mapped)+32,sizeof(storage_values));\n        else '+storage.strip()),
            (download,'''    if(impl_->n010_packed_readback.mapped)
        std::memcpy(out.image_rgba.data(),static_cast<const unsigned char*>(impl_->n010_packed_readback.mapped)+64,out.image_rgba.size()*sizeof(float));
    else {
'''+download+'\n    }'),
            (scratch,'''        if(impl_->n010_packed_readback.mapped)
            phos::gi::research::n010::N010PackedScratchSpool::retain(std::filesystem::path(directory)/"neutral-work.bin",
                static_cast<const unsigned char*>(impl_->n010_packed_readback.mapped)+64+impl_->image.size);
        else '''+scratch.strip())],
        'capture':[include,
            ('            deferred.flush(out,[&](const auto& image) {',
             '            if(std::getenv("PHOS_N010_PACKED_CALIBRATION_READBACK")) phos::gi::research::n010::N010PackedScratchSpool::flush(out);\n            deferred.flush(out,[&](const auto& image) {')],
        'neutral':[
            ('#include <memory>','#include <memory>\n#include <vector>\n#include <algorithm>'),
            ('class NeutralWork {',SPOOL+'\nclass NeutralWork {'),
            ('    void save(const std::filesystem::path& path) const {',
             '    VkBuffer packed_source_buffer() const {return scratch_.buffer;}\n    void save(const std::filesystem::path& path) const {')]
    }
    # This old scratch save appears twice with different indent; replace only
    # the minimal branch (the exact eight-space anchor includes a newline).
    old,new=pairs['runtime'][-1]
    pairs['runtime'][-1]=('\n'+old+'\n','\n'+new+'\n')
    generated={k:overlay(originals[k],pairs[k]) for k in originals}
    start='        stamp(12);';stop='        stamp(15);'
    before=originals['runtime'].split(start,1)[1].split(stop,1)[0]
    after=generated['runtime'].split(start,1)[1].split(stop,1)[0]
    if before!=after:raise ValueError('original timed GPU recording changed')
    start='        const auto period = context.timestamp_period_ns();'
    stop='        result.stats.work_items = counter_values[0];'
    if originals['runtime'].split(start,1)[1].split(stop,1)[0]!=generated['runtime'].split(start,1)[1].split(stop,1)[0]:
        raise ValueError('original timing expressions changed')
    return generated,pairs


def main():
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing packed fixture')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    read(__file__);read(PLAN)
    parent=json.loads(read(RESULTS/'184-deferred-image-calibration-fixture-build.json',
        '6eca016a61ca7ba3b072f05ef7f22221a2d402a9ff778d10b56feb0261f96ebf'))
    if not parent['complete'] or not parent['all_pass']:raise ValueError('complete parent build required')
    for p,h in parent['input_sha256'].items():read(p,h)
    originals={k:read(PARENT/name,parent['generated_sha256'][name]).decode() for k,name in
               [('runtime','minimal_runtime.cpp'),('capture','minimal_capture.cpp')]}
    originals['neutral']=read(ROOT/'src/research/n010_comparison_readiness/neutral_work.hpp').decode()
    generated,pairs=generated_sources(originals)
    WORK.mkdir()
    names=dict(runtime='minimal_runtime.cpp',capture='minimal_capture.cpp',neutral='n010_packed_neutral_work.hpp')
    for k,s in generated.items():(WORK/names[k]).write_text(s)
    steps=parent['steps'][:3]
    result=dict(schema='n010-packed-readback-fixture-build/1',complete=False,all_pass=False,gpu_run=False,
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=INPUTS,whole_parent_source_inverses_exact=True,
        timed_gpu_recording_through_stamp15_byte_identical=True,timing_expressions_byte_identical=True,
        overlay_pairs={k:[dict(old=a,new=b) for a,b in v] for k,v in pairs.items()},
        scope='C7 capture diagnostic only; no PT/dense-RC packed fixture or scientific/timing/READY admission',
        tests='NOT_RUN; isolated scientific build only',steps=[])
    def save():OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for i,parent_step in enumerate(steps):
            args=[a.replace(str(PARENT),str(WORK)) for a in parent_step['command']]
            for a in args:
                if a.endswith(('.a','.o')) and not a.startswith(str(WORK)):
                    read(Path(a) if Path(a).is_absolute() else ROOT/'build/n009'/a)
            receipt=WORK/f'step-{i}.resources.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=300,command=args))+'\n')
            attempt=dict(command=args,cwd=str(ROOT/'build/n009'));result['steps'].append(attempt);save()
            started=time.monotonic()
            try:proc=subprocess.run(args,cwd=ROOT/'build/n009',capture_output=True,text=True,timeout=300,preexec_fn=limits)
            except subprocess.TimeoutExpired as e:
                (WORK/f'step-{i}.stdout').write_bytes(e.stdout or b'');(WORK/f'step-{i}.stderr').write_bytes(e.stderr or b'')
                raise ValueError('compile elapsed guard; partials retained') from e
            attempt.update(returncode=proc.returncode,elapsed=time.monotonic()-started,stdout=proc.stdout,stderr=proc.stderr,receipt_sha256=sha(receipt));save()
            actual=json.loads(read(receipt))
            if actual['cpu']!=[120,120] or actual['address_space']!=[8*1024**3]*2 or len(actual['affinity'])!=1 or actual['nice']!=15:
                raise ValueError('actual compiler resource limits differ')
            if proc.returncode:raise ValueError('compile/link failed; no retry')
        for p,h in list(INPUTS.items()):read(p,h)
        result['generated_sha256']={p.name:sha(p) for p in WORK.iterdir() if p.is_file()}
        result.update(all_pass=True,active_inputs_byte_unchanged=True)
    except (ValueError,OSError,subprocess.SubprocessError) as e:result['failure']=str(e)
    result['complete']=True;save()
    print(json.dumps(dict(complete=True,all_pass=result['all_pass'],failure=result.get('failure'))))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__=='__main__':main()

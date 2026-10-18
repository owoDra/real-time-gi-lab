#!/usr/bin/env python3
"""Plan135: source-only bounded integer work preserving actual PT histories."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

from prepare_tiled_pixel_pt import overlay
from build_continuation_pixel_pt import checked,unchanged,INPUTS,ROOT,RESULTS

PLAN=RESULTS.parent/'experiments/135-bounded-history-known-work.md'
BASE=ROOT/'out/research/n010-comparison-readiness'
WORK=BASE/'history-known-work-source-v1'
OUTPUT=RESULTS/'428-history-known-work-source-prepare.json'
HEADER=ROOT/'src/research/n010_comparison_readiness/bounded_neutral_work.hpp'
SHADER=ROOT/'shaders/research/n010_comparison_readiness/n010_history_neutral_work.comp.glsl'

KNOWN_LOOP=r'''            uint32_t known_begin=0,known_index=0;
            do {
                if(std::chrono::duration<double>(Clock::now()-image_started).count()>=180.0)
                    throw std::runtime_error("bounded known-work image guard; partials retained");
                const uint32_t known_end=known_begin+std::min(n::BoundedNeutralWork::chunk,known_work_dose-known_begin);
                check(context.vk().resetFences(1,&fence));check(context.vk().resetCommandPool(pool,0));
                auto begin=phos::gi::detail::make_vk_info<VkCommandBufferBeginInfo>(VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
                begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;check(context.vk().beginCommandBuffer(command,&begin));
                context.vk().cmdResetQueryPool(command,query,0,4);
                context.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,query,0);
                known_work->record(command,known_begin,known_end);
                context.vk().cmdWriteTimestamp(command,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,query,1);
                check(context.vk().endCommandBuffer(command));
                auto submit=phos::gi::detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
                submit.commandBufferCount=1;submit.pCommandBuffers=&command;
                check(context.vk().queueSubmit(context.queue(),1,&submit,fence));
                check(context.vk().waitForFences(1,&fence,VK_TRUE,500000000ULL));
                std::array<uint64_t,2> ticks{};
                check(context.vk().getQueryPoolResults(query,0,2,sizeof(ticks),ticks.data(),8,VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WAIT_BIT));
                const uint64_t first=ticks[0]&timestamp_mask,last=ticks[1]&timestamp_mask;
                const double duration=double((last-first)&timestamp_mask)*timestamp_period/1000.0;
                if(known_index==0)first_tick=first;
                last_tick=last;last_known_work_gpu_us+=duration;
                last_known_work_max_gpu_us=std::max(last_known_work_max_gpu_us,duration);
                known_times<<"{\"image_index\":"<<image_index<<",\"chunk_index\":"<<known_index
                    <<",\"work_begin\":"<<known_begin<<",\"work_end\":"<<known_end
                    <<",\"dose\":"<<known_work_dose<<",\"count\":"<<n::BoundedNeutralWork::count
                    <<",\"begin_tick\":"<<ticks[0]<<",\"end_tick\":"<<ticks[1]
                    <<",\"timestamp_valid_bits\":"<<valid_bits<<",\"timestamp_period_ns\":"<<timestamp_period
                    <<",\"gpu_us\":"<<duration<<"}"<<std::endl;
                if(!known_times || !std::isfinite(duration) || duration<=0 || duration>250000.0)
                    throw std::runtime_error("known-work dispatch time/receipt guard; partials retained");
                known_begin=known_end;++known_index;
                std::this_thread::sleep_for(std::chrono::microseconds(pause_us));
            } while(known_begin<known_work_dose);
            last_known_work_envelope_gpu_us=double((last_tick-first_tick)&timestamp_mask)*timestamp_period/1000.0;
            uint64_t first_pt_tick=0;
'''


def main():
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180);start,cpu=time.monotonic(),time.process_time()
    if WORK.exists() or OUTPUT.exists():raise ValueError('refuse existing428/source; no overwrite/retry')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,HEADER,SHADER):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])!=checked(path):
            raise ValueError('commit exact source/recipe before preparation')
    for filename in ('405-continuation-readback-source-prepare.json','401-continuation-pixel-pt-build.json'):
        proof=json.loads(checked(RESULTS/filename))
        if not proof['complete']:raise ValueError('terminal405/401 required')
        for group in ('input_sha256','payload_sha256'):
            for name,digest in proof[group].items():checked(name,digest)
    old=BASE/'continuation-pixel-pt-accounted-source-v1'
    host=checked(old/'continuation_pixel_pt.cpp').decode()
    pt=checked(old/'continuation_pixel_pt.comp.glsl')
    work_shader=checked(SHADER).decode()
    original_shader=checked(ROOT/'shaders/research/n010_comparison_readiness/n010_neutral_work.comp.glsl').decode()
    recurrence='{x=x*1664525u+1013904223u;x^=x>>13u;}'
    if original_shader.count(recurrence)!=1 or work_shader.count(recurrence)!=1:
        raise ValueError('original complete integer recurrence body differs')
    edits=[
        ('#include "neutral_work.hpp"','#include "neutral_work.hpp"\n#include "bounded_neutral_work.hpp"',1),
        ('        std::string family="pixel-pt";',
         '        uint32_t known_work_dose=0;bool known_work_requested=false;\n        std::string family="pixel-pt";',1),
        ('            else if(arg=="--calibration-doses") calibration_doses=value;',
         '''            else if(arg=="--known-work-dose") {
                if(known_work_requested)throw std::runtime_error("duplicate known-work dose");
                size_t used=0;const auto parsed=std::stoull(value,&used);
                if(used!=value.size() || parsed>n::BoundedNeutralWork::max_dose || value.empty() || value[0]=='-')
                    throw std::runtime_error("invalid known-work dose");
                known_work_dose=uint32_t(parsed);known_work_requested=true;
            }
            else if(arg=="--calibration-doses") calibration_doses=value;''',1),
        ('        if(family!="pixel-pt" || !calibration_doses.empty()',
         '        if(!known_work_requested || family!="pixel-pt" || !calibration_doses.empty()',1),
        ('tiled pixel-PT only; no calibration, tile1..4096, chunk1..16, pause>=2ms',
         'history known-work PT requires explicit dose; no calibration reset, tile1..4096, chunk1..16, pause>=2ms',1),
        ('        std::unique_ptr<n::NeutralWork> neutral;',
         '        auto known_work=std::make_unique<n::BoundedNeutralWork>(context);\n        std::unique_ptr<n::NeutralWork> neutral;',1),
        ('n010-continuation-pixel-pt/1','n010-history-known-work-pixel-pt/1',1),
        ('tiled pixel Renderer: upload/update GPU segments plus full image timestamp envelope including cooperative host gaps; active GPU sum and CPU wall separate; uncalibrated',
         'history pixel Renderer: maintenance plus first known-work to last PT timestamp including all cooperative gaps; active components and CPU/readback wall separate; uncalibrated',1),
        ('        uint32_t image_call=0;',
         '        std::ofstream known_times(out/"known-work-timings.jsonl");known_times<<std::setprecision(17);\n        uint32_t image_call=0;',1),
        ('        const auto run_image=[&](uint32_t image_seed) {',
         '        double last_known_work_gpu_us=0,last_known_work_max_gpu_us=0,last_known_work_envelope_gpu_us=0,last_pt_envelope_gpu_us=0;\n'
         '        const auto run_image=[&](uint32_t image_seed) {',1),
        ('            const uint32_t pixels=uint32_t(uint64_t(width)*height);',
         '            last_known_work_gpu_us=last_known_work_max_gpu_us=last_known_work_envelope_gpu_us=last_pt_envelope_gpu_us=0;\n'
         +KNOWN_LOOP+'            const uint32_t pixels=uint32_t(uint64_t(width)*height);',1),
        ('                if(sample_begin==0 && pixel_begin==0)first_tick=begin_tick;',
         '                if(sample_begin==0 && pixel_begin==0)first_pt_tick=begin_tick;',1),
        ('            if(!std::isfinite(last_envelope_gpu_us) || last_envelope_gpu_us<last_active_gpu_us ||',
         '            last_pt_envelope_gpu_us=double((last_tick-first_pt_tick)&timestamp_mask)*timestamp_period/1000.0;\n'
         '            if(!std::isfinite(last_envelope_gpu_us) || last_envelope_gpu_us<last_active_gpu_us+last_known_work_gpu_us ||\n'
         '               !std::isfinite(last_pt_envelope_gpu_us) || last_pt_envelope_gpu_us<last_active_gpu_us ||',1),
        ('            n::NeutralWork::last_gpu_us=0;',
         '            // Full envelope includes all known-work and PT chunks and gaps.',1),
        ('<<",\\\"dose\\\":"<<(doses.empty()?0:doses[f])',
         '<<",\\\"dose\\\":"<<(doses.empty()?known_work_dose:doses[f])',1),
        ('<<last_active_gpu_us+maintenance_gpu',
         '<<last_active_gpu_us+last_known_work_gpu_us+maintenance_gpu',1),
        ('<<n::NeutralWork::last_gpu_us',
         '<<last_known_work_gpu_us<<",\\\"known_work_envelope_gpu_us\\\":"<<last_known_work_envelope_gpu_us\n'
         '                 <<",\\\"known_work_max_dispatch_gpu_us\\\":"<<last_known_work_max_gpu_us\n'
         '                 <<",\\\"pt_image_envelope_gpu_us\\\":"<<last_pt_envelope_gpu_us\n'
         '                 <<",\\\"known_work_count\\\":"<<n::BoundedNeutralWork::count\n'
         '                 <<",\\\"known_work_chunk_iterations\\\":"<<n::BoundedNeutralWork::chunk\n'
         '                 <<",\\\"known_work_persistent_bytes\\\":"<<uint64_t(n::BoundedNeutralWork::count)*8',1),
        ('            if(neutral)neutral->save(frame_out/"neutral-work.bin");',
         '            if(neutral)neutral->save(frame_out/"neutral-work.bin");\n            known_work->save(frame_out,known_work_dose);',1),
        ('        neutral.reset();stage.reset();hwrt.reset();',
         '        known_work.reset();neutral.reset();stage.reset();hwrt.reset();',1)]
    revised=overlay(host,edits)
    history=host[host.index('        for(uint32_t f=0;f<frames;++f) {'):host.index('            const double gpu=run_image(')]
    if history not in revised:raise ValueError('complete original history/update/seed control flow differs')
    WORK.mkdir(parents=True)
    (WORK/'history_known_work_pixel_pt.cpp').write_text(revised)
    (WORK/'n010_pixel_pt.comp.glsl').write_bytes(pt)
    (WORK/'n010_history_neutral_work.comp.glsl').write_text(work_shader)
    (WORK/'bounded_neutral_work.hpp').write_bytes(checked(HEADER))
    (WORK/'source-edits.json').write_text(json.dumps(edits,indent=2)+'\n')
    (WORK/'known-work-loop.inc.txt').write_text(KNOWN_LOOP)
    unchanged();elapsed,used=time.monotonic()-start,time.process_time()-cpu
    if elapsed>=180 or used>=120:raise ValueError('registered preparation resource bound exceeded')
    result=dict(schema='n010-history-known-work-source/1',complete=True,source_preparation_valid=True,
        all_pass=False,compiled=False,gpu_run=False,accepted_timing=False,reference_admission=False,
        source_commit=commit,input_sha256=INPUTS,
        payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in WORK.iterdir()},
        whole_host_inverse_exact=True,pt_shader_byte_identical_to405=True,
        original_history_update_seed_flow_byte_identical=True,known_work_recurrence_body_byte_identical=True,
        known_work_lanes=16384,known_work_chunk_iterations=65536,additional_persistent_owned_bytes=131072,
        classification='HISTORY_KNOWN_WORK_SOURCES_PREPARED_UNCOMPILED_UNEXECUTED',
        execution=dict(elapsed_seconds=elapsed,cpu_seconds=used,affinity=sorted(os.sched_getaffinity(0)),
            nice=os.getpriority(os.PRIO_PROCESS,0),cpu_limit_seconds=120,elapsed_limit_seconds=180,address_space_limit_bytes=2*1024**3),
        tests='NOT_RUN; source preparation/inverse checks only, no runtime or timing admission')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__=='__main__':main()

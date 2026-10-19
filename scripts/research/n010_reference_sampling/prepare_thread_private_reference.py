#!/usr/bin/env python3
"""Plan162: exact-inverse thread-private audit sources, or isolated builds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

PLAN = D.RESULTS.parent/'experiments/162-thread-private-reference-audit-source.md'
PREP = D.RESULTS/'621-thread-private-reference-source.json'
BUILD = D.RESULTS/'622-thread-private-reference-build.json'
ROOT = D.OUT/'thread-private-reference-source-v1'
BUILD_ROOT = D.OUT/'thread-private-reference-build-v1'
INTEGER = ('eye_samples','light_samples','prefixes','forward_null','opposite_zero',
    'density_reconstructions','bvh_queries','own_checks','coincident_matches','alternative_ray_checks',
    'alternative_direct_checks','unmatched_visibility','component_attempts','component_nulls')
MAXIMA = ('max_coincident_normal_difference','max_own_log_error','max_target_error_fraction',
    'max_weight','max_unconditioned_target_error_fraction')
COUNTERS = ('primary_hits','shadow_tests','shadow_blocked','backface_absorbed','proposal_null_samples')
LAYOUT = '''    struct WholeAudit {
        uint64_t eye_samples{},light_samples{},prefixes{},forward_null{},opposite_zero{},
                 density_reconstructions{},bvh_queries{},own_checks{},coincident_matches{},alternative_ray_checks{},alternative_direct_checks{},unmatched_visibility{};
        std::map<std::pair<uint32_t,uint32_t>,uint64_t> coincident_pairs;
        double max_coincident_normal_difference{};
        double max_own_log_error{},max_target_error_fraction{},max_weight{},max_unconditioned_target_error_fraction{};
        uint64_t strategy_counts[8][8]{},component_attempts{},component_nulls{};
        double max_depth_weight[8]{};
        RenderCounters direct_counters;
    };'''


def write(path,value,fresh=False):
    with path.open('x' if fresh else 'w') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def transform(original):
    if original.count(LAYOUT) != 1 or original.count(
        '    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{}, proposal_null_samples{};') != 1:
        raise ValueError('exact complete audit/counter layouts required')
    source,edits = original,[]
    def change(before,after):
        nonlocal source
        source = D.once(source,before,after);edits.append((before,after))
    change('inline uint32_t n010_density_witness_k=0, n010_density_witness_split=0;',
        'inline thread_local uint32_t n010_density_witness_k=0, n010_density_witness_split=0;')
    signature = '                          PrimaryRecord* primary,PrimaryCache* cache) const {'
    change(signature,'                          PrimaryRecord* primary,PrimaryCache* cache,\n'
        '                          WholeAudit& renderer_audit_,uint64_t& primary_prime_samples_) const {')
    anchor = '    // One camera sample; writes per-component radiance.\n'
    wrapper = '''    // Private audit wrapper preserves serial diagnostic callers.
    template<class Rng>
    void sample_all_split(uint32_t x,uint32_t y,Rng& rng,Rgb out[kComponents],RenderCounters& cnt,
                          PrimaryRecord* primary,PrimaryCache* cache) const {
        sample_all_split(x,y,rng,out,cnt,primary,cache,renderer_audit_,primary_prime_samples_);
    }

'''
    change(anchor,wrapper+anchor)
    change('        if(threads!=1)throw std::runtime_error("all-split export requires one render thread");',
        '        if(threads<1||threads>4)throw std::runtime_error("private audit requires one to four render threads");\n'
        '#ifdef N010_VERIFY_BVH\n'
        '        if(threads!=1)throw std::runtime_error("paired debug BVH remains serial");\n'
        '#endif')
    change('        std::vector<RenderCounters> per_thread(threads);',
        '        std::vector<RenderCounters> per_thread(threads);\n'
        '        std::vector<WholeAudit> per_thread_audit(threads);\n'
        '        std::vector<uint64_t> per_thread_primes(threads);')
    change(': nullptr, &cache);',': nullptr, &cache, per_thread_audit[t], per_thread_primes[t]);')
    merge = '        for (unsigned t=0;t<threads;++t) {\n            const auto& a=per_thread_audit[t];\n'
    merge += '            primary_prime_samples_+=per_thread_primes[t];\n'
    merge += ''.join(f'            renderer_audit_.{key}+=a.{key};\n' for key in INTEGER)
    merge += ''.join(f'            renderer_audit_.{key}=std::max(renderer_audit_.{key},a.{key});\n' for key in MAXIMA)
    merge += '''            for(const auto& entry:a.coincident_pairs)renderer_audit_.coincident_pairs[entry.first]+=entry.second;
            for(unsigned i=0;i<8;++i) {
                renderer_audit_.max_depth_weight[i]=std::max(renderer_audit_.max_depth_weight[i],a.max_depth_weight[i]);
                for(unsigned j=0;j<8;++j)renderer_audit_.strategy_counts[i][j]+=a.strategy_counts[i][j];
            }
'''
    merge += ''.join(f'            renderer_audit_.direct_counters.{key}+=a.direct_counters.{key};\n' for key in COUNTERS)
    merge += '        }\n'
    anchor = '        for (auto& th : pool) th.join();\n'
    change(anchor,anchor+merge)
    restored = source
    for before,after in reversed(edits):restored = D.once(restored,after,before)
    if restored != original:raise ValueError('whole thread-private header inverse differs')
    def sample_body(text):
        start = text.index('        if(!cache)throw std::runtime_error("all-split renderer requires primary cache");')
        end = text.index('    // One camera sample; writes per-component radiance.',start)
        block = text[start:end]
        return block.replace(wrapper,'')
    if sample_body(source) != sample_body(original):raise ValueError('actual full all-split sample body changed')
    def physical(text):return text[text.index('    Ray primary_ray('):text.index('    // Plan080: single-thread renderer audit')]
    if physical(source) != physical(original):raise ValueError('physical/density/geometry/sampling code changed')
    return source,edits,dict(whole_header_inverse_exact=True,sample_all_split_body_byte_identical=True,
        physical_density_geometry_sampling_block_byte_identical=True,all_audit_layout_fields_accounted=True,
        integer_fields=list(INTEGER),maxima_fields=list(MAXIMA),all_direct_counter_fields=list(COUNTERS),
        per_pixel_statistics_arithmetic_unchanged=True,debug_paired_bvh_serial_guard=True)


def prepare(commit):
    if PREP.exists() or ROOT.exists():raise ValueError('fresh thread-private source required')
    parent = json.loads(D.checked(D.RESULTS/'452-compensated-full-exporter-build.json'))
    prefix = json.loads(D.checked(D.RESULTS/'525-compensated-prefix-source-prepare.json'))
    if not parent['build_valid'] or not prefix['source_preparation_valid']:raise ValueError('actual452/525 source required')
    full = D.OUT/'compensated-full-deterministic-v1/build'
    inc = D.OUT/'compensated-prefix-source-v1'
    rows,payloads = [],{}
    # Prepare in memory first: a failed inverse must not create partial sources.
    prepared = []
    for mode,base,main,proof,binary in (
        ('full',full,'exporter.cpp',parent,'n010_thread_private_exporter'),
        ('prefix',inc,'n010_rqmc_main.cpp',prefix,'n010_thread_private_prefix')):
        header_path = base/'n010_rqmc_oracle.hpp'
        original = D.checked(header_path,proof['payload_sha256'][str(header_path)]).decode()
        main_bytes = D.checked(base/main,proof['payload_sha256'][str(base/main)])
        generated,edits,identity_proof = transform(original)
        command = list(proof['command']);command[-3] = str(ROOT/mode/main);command[-1] = str(BUILD_ROOT/binary)
        prepared.append((mode,main,main_bytes,generated,edits))
        rows.append(dict(mode=mode,proof=identity_proof,original_header_sha256=hashlib.sha256(original.encode()).hexdigest(),
            generated_header_sha256=hashlib.sha256(generated.encode()).hexdigest(),main_sha256=hashlib.sha256(main_bytes).hexdigest(),
            command=command,compiler_realpath=proof['compiler_realpath'],binary=str(BUILD_ROOT/binary)))
    baseline = json.loads(D.checked(next(D.RESULTS.glob('371-*.json'))))
    attempt = baseline['attempts'][0]
    if not baseline['complete'] or not baseline['all_pass'] or attempt['returncode'] != 0:
        raise ValueError('actual terminal371 baseline required for cost planning')
    if (baseline['spp'],baseline['width'],baseline['height']) != (16,320,180):raise ValueError('exact371 sizing identity required')
    command = attempt['command']
    if command[command.index('--seeds')+1] != str(D.SEEDS[0]):raise ValueError('371 is exactly one original seed')
    planning = dict(posthoc=True,source='371 one-seed16spp older backend; not candidate throughput/ETA',
        four_seed8192_cpu_seconds=attempt['child_cpu_seconds']*2048,
        four_seed8192_elapsed_seconds=attempt['elapsed_seconds']*2048,
        optimistic_two_way_elapsed_seconds=attempt['elapsed_seconds']*1024,
        optimistic_four_way_elapsed_seconds=attempt['elapsed_seconds']*512,
        unchanged_native_elapsed_guard_seconds=43200,actual_feasibility_proved=False)
    ROOT.mkdir()
    for mode,main,main_bytes,generated,edits in prepared:
        folder = ROOT/mode;folder.mkdir()
        (folder/main).write_bytes(main_bytes)
        (folder/'n010_rqmc_oracle.hpp').write_text(generated)
        write(folder/'source-edits.json',edits,True)
        for path in folder.iterdir():payloads[str(path)] = D.sha(path)
    result = dict(schema='n010-thread-private-reference-source/1',complete=True,source_preparation_valid=True,
        classification='THREAD_PRIVATE_AUDIT_SOURCE_ONLY_NOT_QUALIFIED',source_commit=commit,
        input_sha256=D.INPUTS,payload_sha256=payloads,rows=rows,posthoc_resource_planning=planning,
        maximum_render_threads_in_source=4,actual_cpu_load_changed=False,compiled=False,native_rendering_executed=False,
        reference_admission=False,gpu_run=False,tests='NOT_RUN; source inverses/body/layout/input identity only')
    write(PREP,result,True);print(result['classification'])


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def build(commit):
    require_no_other_research_worker()
    if BUILD.exists() or BUILD_ROOT.exists():raise ValueError('fresh private build required')
    source = json.loads(D.checked(PREP))
    if not source['complete'] or not source['source_preparation_valid']:raise ValueError('actual621 source required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in source[group].items():D.checked(Path(name),digest)
    BUILD_ROOT.mkdir()
    result = dict(schema='n010-thread-private-reference-build/1',complete=False,build_valid=False,source_commit=commit,
        input_sha256=D.INPUTS,attempts=[],gpu_run=False,reference_admission=False,native_rendering_executed=False,
        tests='NOT_RUN; two serial isolated compilers only')
    def save():write(BUILD,result)
    save()
    try:
        for row in source['rows']:
            require_no_other_research_worker()
            command = row['command']
            import shutil
            if str(Path(shutil.which(command[0])).resolve()) != row['compiler_realpath']:
                raise ValueError('exact parent compiler changed')
            receipt = BUILD_ROOT/(row['mode']+'.resources.json')
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(220,220))
                resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                write(receipt,dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
                    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=300),True)
            attempt = dict(mode=row['mode'],command=command,terminal=False,resource_receipt=str(receipt))
            result['attempts'].append(attempt);save()
            before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
            with (BUILD_ROOT/(row['mode']+'.stdout')).open('wb') as stdout,(BUILD_ROOT/(row['mode']+'.stderr')).open('wb') as stderr:
                child = subprocess.Popen(command,cwd=D.ROOT,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
                attempt['pid'] = child.pid;save()
                try:code = child.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    own = json.loads(receipt.read_text())
                    if ((own['pid'],own['pgid'],own['start_ticks']) != (child.pid,child.pid,start_ticks(child.pid))
                            or own['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
                        raise ValueError('owned compiler changed; refuse signalling')
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    child.wait(timeout=5);code='ELAPSED_GUARD_PARTIALS_RETAINED'
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            attempt.update(terminal=True,returncode=code,elapsed_seconds=time.monotonic()-started,
                child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
            save()
            own = json.loads(receipt.read_text())
            if (code != 0 or own['pid'] != child.pid or own['pgid'] != child.pid
                    or type(own['start_ticks']) is not int or own['start_ticks'] <= 0
                    or own['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                    or own['elapsed_limit_seconds'] != 300
                    or own['command'] != command or own['cpu'] != [220,220] or own['address_space'] != [4*1024**3]*2
                    or own['affinity'] != [31] or own['nice'] != 15 or attempt['elapsed_seconds'] >= 300
                    or attempt['child_cpu_seconds'] > 220 or not Path(row['binary']).read_bytes().startswith(b'\x7fELF')):
                raise ValueError('private compiler/resource failure; stop before next stage')
            for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
        result.update(build_valid=True,classification='THREAD_PRIVATE_REFERENCE_BUILD_COMPLETE_RUNTIME_NOT_QUALIFIED')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='THREAD_PRIVATE_REFERENCE_BUILD_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True,payload_sha256={str(path):D.sha(path) for path in BUILD_ROOT.iterdir() if path.is_file()})
    save();print(result['classification'])
    return 0 if result['build_valid'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--build',action='store_true')
    args = parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):raise ValueError('one numerical thread required')
    if args.prepare:
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact162 source/recipe before use')
    return prepare(commit) if args.prepare else build(commit)


if __name__ == '__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Plan119: source preparation, then separately invoked bounded diagnostics.

Only --step prepare is allowed while original260 calculates. No step queues
another one. Failed372 stays failed; no reference or timing admission here.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT / 'research/lanes/n010-comparison-readiness/results'
OUT = ROOT / 'out/research/n010-comparison-readiness'
BASE = OUT / 'whole-path-full-frame-build-v1'
WORK = OUT / 'early-density-route-diagnostic-v1'
PLAN = RESULTS.parent / 'experiments/119-early-density-route-diagnostic.md'
STEPS = ('prepare', 'build', 'old', 'guarded')
INPUTS = {}


def checked(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input identity differs: ' + str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed: ' + str(path))
    INPUTS[str(path)] = digest
    return raw


def result_path(step):
    return RESULTS / f'{380 + STEPS.index(step)}-early-density-route-{step}.json'


def retained(step):
    data = json.loads(checked(result_path(step)))
    if not data['complete'] or not data['step_valid'] or data['step'] != step:
        raise ValueError('valid terminal prior diagnostic step required')
    for group in ('input_sha256', 'payload_sha256'):
        for path, digest in data[group].items():
            checked(path, digest)
    return data


def transform(original, edits):
    source = original
    for before, after, count in edits:
        if source.count(before) != count or after in source:
            raise ValueError('nonunique source edit: ' + before[:80])
        source = source.replace(before, after)
    restored = source
    for before, after, count in reversed(edits):
        if restored.count(after) != count:
            raise ValueError('source inverse edit count differs')
        restored = restored.replace(after, before)
    if restored != original:
        raise ValueError('whole source inverse differs')
    return source


def prepare(build, directory):
    def original(name):
        path = BASE / name
        return checked(path, build['payload_sha256'][str(path)])
    shader = original('full.comp.glsl').decode()
    shader_edits = [
        ('uint64_t diagnosticQueries,diagnosticAttempts,diagnosticNulls,diagnosticOwn;',
         'uint64_t diagnosticQueries,diagnosticAttempts,diagnosticNulls,diagnosticOwn;\n'
         'uint64_t earlyRouteMask,earlyNonpositiveBranches;', 1),
        ('diagnosticMaxima=dvec4(0.0LF);',
         'diagnosticMaxima=dvec4(0.0LF);earlyRouteMask=uint64_t(0);earlyNonpositiveBranches=uint64_t(0);', 1),
        ('        if(!(pdf>0.0LF))return;',
         '        if(!sphere && abs(dotd(current.normal,direction))/PI<1e-12LF) {\n'
         '            mark_route(8u);earlyRouteMask|=uint64_t(1);\n'
         '            if(!(pdf>0.0LF))++earlyNonpositiveBranches;\n'
         '        }\n        if(!(pdf>0.0LF))return;', 1),
        ('        if(!(cosine>0.0LF))return;',
         '        if(cosine<1e-12LF) {mark_route(8u);earlyRouteMask|=uint64_t(2);\n'
         '            if(!(cosine>0.0LF))++earlyNonpositiveBranches;}\n'
         '        if(!(cosine>0.0LF))return;', 1),
        ('double cosx=dotd(n,wi);if(cosx<=0.0LF)continue;',
         'double cosx=dotd(n,wi);\n'
         '        if(abs(cosx)<1e-12LF) {mark_route(8u);earlyRouteMask|=uint64_t(4);\n'
         '            if(cosx<=0.0LF)++earlyNonpositiveBranches;}\n'
         '        if(cosx<=0.0LF)continue;', 1),
        ('parts[pathIndex].proposal=u64vec4(diagnosticQueries,diagnosticOwn,uint64_t(0),uint64_t(0));',
         'parts[pathIndex].proposal=u64vec4(diagnosticQueries,diagnosticOwn,earlyRouteMask,earlyNonpositiveBranches);', 1)]
    revised_shader = transform(shader, shader_edits)
    host = original('full.cpp').decode()
    selection = 'static std::vector<uint32_t> select_pixels(const N::Scene& scene,const std::string& mode) {\n'
    host_edits = [(selection, selection +
        '    if(mode=="counter-pixel") {\n'
        '        if(scene.width!=320 || scene.height!=180 || scene.max_bounces!=8)\n'
        '            throw std::runtime_error("counter-pixel requires original C1");\n'
        '        return {43665};\n    }\n', 1),
        ('if(mode=="diagnostic8")', 'if(mode=="diagnostic8" || mode=="counter-pixel")', 5)]
    revised_host = transform(host, host_edits)
    header, context = original('n010_reference_snapshot.hpp'), original('n010_reference_context.hpp')
    identity = hashlib.sha256(header + context + revised_host.encode() + revised_shader.encode()).hexdigest()
    identity_edit = (build['backend_id'], identity, 1)
    revised_host = transform(revised_host, [identity_edit])
    (directory / 'full.cpp').write_text(revised_host)
    (directory / 'full.comp.glsl').write_text(revised_shader)
    (directory / 'n010_reference_snapshot.hpp').write_bytes(header)
    (directory / 'n010_reference_context.hpp').write_bytes(context)
    (directory / 'source-edits.json').write_text(json.dumps(dict(
        shader=shader_edits, host=host_edits + [identity_edit]), indent=2) + '\n')
    # Independently restore the final host all the way back, including its ID.
    restored = revised_host.replace(identity, build['backend_id'])
    for before, after, count in reversed(host_edits):
        if restored.count(after) != count:
            raise ValueError('final host inverse count differs')
        restored = restored.replace(after, before)
    if restored != host:
        raise ValueError('final host inverse differs')
    return dict(backend_id=identity, shader_inverse_exact=True, host_inverse_exact=True,
                cpu_header_context_byte_identical=True, selection=[43665],
                cause='HYPOTHESIS_UNRESOLVED; unprotected early zero/near-zero branches found in source',
                early_route_mask_bits={'1': 'prefix PDF', '2': 'target cosine', '4': 'direct cosine'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--step', choices=STEPS, required=True)
    step = parser.parse_args().step
    output, work = result_path(step), WORK / step
    if output.exists() or work.exists():
        raise ValueError('refuse existing diagnostic part; no retry')
    if step != 'prepare':
        from run_primary_direction_sequence import require_no_other_research_worker
        checked(HERE / 'run_primary_direction_sequence.py')
        require_no_other_research_worker()
        control = json.loads(checked(RESULTS / '260-wide8-original-a6a-seed1.json'))
        if not control['complete'] or not control['seed_integrity_pass']:
            raise ValueError('finish original260 with integrity PASS first; no waiting worker')
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    if os.getpriority(os.PRIO_PROCESS, 0) != 15:
        raise ValueError('actual nice15 required')
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    for path in (Path(__file__).resolve(), PLAN):
        checked(path)
    build = json.loads(checked(RESULTS / '360-whole-path-full-frame-build.json',
                              '3191adae4d54297ccbe00d2179af6c5910d6e2d33814b02a220075eebeab0699'))
    failed = json.loads(checked(RESULTS / '372-batched-full-frame-gpu.json',
                               '088a828350fb163868691636707afc98eeb8d7fa7064d9e5ef7660422c7e07c1'))
    scan = json.loads(checked(OUT / 'posthoc-batched-counter-localization-v1/scan/scan.json',
                             '76518ff58a796431a3ab664e440aab00595ac7616d8149972a7a06414eecb73b'))
    if failed['all_pass'] or failed['failure'] != 'full-frame independent scored counts differ':
        raise ValueError('retain original372 failure')
    if not scan['complete'] or [r['pixel'] for r in scan['rows']] != [43665]:
        raise ValueError('original localization differs')
    prep = None if step == 'prepare' else retained('prepare')
    if step in ('old', 'guarded'):
        retained('build')
    if step == 'guarded':
        prior = retained('old')
        if not prior['validation']['reproduces_prior_corrected_pixel_counts']:
            raise ValueError('old focused probe did not reproduce; stop, no guarded probe')
    work.mkdir(parents=True)
    if shutil.disk_usage(work).free < 2 * 1024**3:
        raise ValueError('2GiB free-space guard; no native')
    result = dict(schema='n010-early-density-route-diagnostic/1', step=step,
        complete=False, step_valid=False, all_pass=False, accepted_timing=False,
        reference_admission=False, gpu_run=step in ('old', 'guarded'),
        classification='POSTHOC_EARLY_ROUTE_DIAGNOSTIC_IN_PROGRESS',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        input_sha256=INPUTS, attempts=[],
        tests='NOT_RUN; post-hoc source/isolated compiler/scientific diagnosis only')
    def save():
        output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    def native(command, label, cpu_limit, elapsed_limit):
        receipt = work / (label + '.resources.json')
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit,) * 2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                command=command)) + '\n')
        row = dict(command=command, terminal=False, resource_receipt=str(receipt))
        result['attempts'].append(row);save()
        started, before = time.monotonic(), resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            proc = subprocess.run(command, capture_output=True, timeout=elapsed_limit, preexec_fn=limits)
            stdout, stderr = proc.stdout, proc.stderr
            row.update(terminal=True, returncode=proc.returncode)
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b'', error.stderr or b''
            row.update(terminal=True, returncode='TIMEOUT_PARTIALS_RETAINED')
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        row.update(elapsed_seconds=time.monotonic() - started,
                   child_cpu_seconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime)
        (work / (label + '.stdout')).write_bytes(stdout)
        (work / (label + '.stderr')).write_bytes(stderr)
        save()
        actual = json.loads(checked(receipt))
        if (row['returncode'] != 0 or actual['cpu'] != [cpu_limit] * 2
                or actual['address_space'] != [4 * 1024**3] * 2
                or actual['affinity'] != [31] or actual['nice'] != 15
                or actual['command'] != command):
            raise ValueError('native/resource failure; no retry')
    save()
    try:
        if step == 'prepare':
            result['validation'] = prepare(build, work)
        elif step == 'build':
            prepared = WORK / 'prepare'
            for name in ('full.cpp', 'full.comp.glsl', 'n010_reference_snapshot.hpp', 'n010_reference_context.hpp'):
                (work / name).write_bytes(checked(prepared / name, prep['payload_sha256'][str(prepared / name)]))
            glslang = ROOT / 'build/n009/_deps/glslang-build/StandAlone/glslang'
            checked(glslang)
            native([str(glslang), '-V', '--target-env', 'vulkan1.2', '-S', 'comp',
                    str(work / 'full.comp.glsl'), '-o', str(work / 'raw.spv')], 'shader', 120, 180)
            helper = HERE.parent / 'n010_comparison_readiness/compile_gpu_reference.py'
            checked(helper);sys.path.insert(0, str(helper.parent))
            from compile_gpu_reference import decorate
            decorated, count = decorate((work / 'raw.spv').read_bytes())
            (work / 'full.spv').write_bytes(decorated)
            command = next(r['command'] for r in build['attempts'] if r['label'] == 'host')
            command = [str(work / 'full.cpp') if x == str(BASE / 'full.cpp') else
                       str(work / 'probe') if x == str(BASE / 'phos-n010-whole-full') else x for x in command]
            if str(work / 'full.cpp') not in command or command[-1] != str(work / 'probe'):
                raise ValueError('host command anchors differ')
            native(command, 'host', 120, 180)
            result['validation'] = dict(compiler_valid=True, no_contraction_results=count,
                                        runtime_validated=False, backend_id=prep['validation']['backend_id'])
        else:
            baseline = json.loads(checked(RESULTS / '371-batched-full-frame-cpu.json',
                '225b9e381492bc29c75938de3d4f3603da10e5747f1fb97b15d071467bf63635'))
            oldcmd = baseline['attempts'][0]['command']
            scene, net = [Path(oldcmd[oldcmd.index(flag) + 1]) for flag in ('--scene', '--net')]
            for path in (scene, net):
                checked(path, baseline['input_sha256'][str(path)])
            shader = BASE / 'full.spv' if step == 'old' else WORK / 'build/full.spv'
            if step == 'old':
                checked(shader, build['payload_sha256'][str(shader)])
            command = ['bash', str(ROOT / 'scripts/run_with_vulkan.sh'), str(WORK / 'build/probe'),
                str(scene), str(net), str(shader), '305419896', '16', '16', '1',
                'counter-pixel', '0', '-', str(work / 'gpu'), '1']
            checked(ROOT / 'scripts/run_with_vulkan.sh')
            native(command, 'gpu', 60, 120)
            result['validation'] = validate_probe(work / 'gpu', scan['rows'][0], prep, scene, net)
            if step == 'guarded':
                old_dir = WORK / 'old/gpu'
                result['validation']['old_new_raw_paths_bit_exact'] = (
                    checked(old_dir / 'gpu-paths.bin') == checked(work / 'gpu/gpu-paths.bin'))
                if not result['validation']['all16_corrected_scored_and_proposal_counts_exact']:
                    raise ValueError('guarded focused counts still differ; stop')
                if result['validation']['max_corrected_sample_component_error'] > 1e-10:
                    raise ValueError('guarded focused numerical tolerance failed; stop')
        for path, digest in list(INPUTS.items()):
            checked(path, digest)
        if sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file()) > 1024**3:
            raise ValueError('retained diagnostic work exceeds1GiB')
        result.update(step_valid=True, classification='POSTHOC_EARLY_ROUTE_STEP_COMPLETE_NO_ADMISSION')
    except (ValueError, OSError, KeyError, StopIteration, AssertionError, subprocess.SubprocessError) as error:
        result.update(failure=str(error), classification='POSTHOC_EARLY_ROUTE_FAILURE_RETAINED')
    result['complete'] = True
    result['payload_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in work.rglob('*') if p.is_file()}
    save();print(result['classification'], flush=True)
    return 0 if result['step_valid'] else 2


def validate_probe(directory, cpu, preparation, scene, net):
    meta = json.loads(checked(directory / 'gpu.json'))
    scope = json.loads(checked(directory / 'scope.json'))
    if (meta['mode'] != 'counter-pixel' or scope['selected_pixels'] != [43665]
            or scope['mode'] != 'counter-pixel'
            or (meta['width'],meta['height'],meta['vertices'],meta['begin_spp']) != (320,180,8,0)
            or meta['backend_id'] != preparation['validation']['backend_id']
            or meta['scene_sha256'] != hashlib.sha256(scene.read_bytes()).hexdigest()
            or meta['net_sha256'] != hashlib.sha256(net.read_bytes()).hexdigest()
            or (meta['spp'], meta['seed'], meta['batch'], meta['tile_capacity'], meta['selected_count']) != (16,305419896,16,1,1)
            or meta['fault_flags'] or not meta['all_finite'] or meta['reference_admission'] or meta['accepted_timing']):
        raise ValueError('focused diagnostic identity differs')
    path_format, part_format = struct.Struct('<16d4Q'), struct.Struct('<4d8Q4d')
    streams = {}
    path_bytes = {}
    for name in ('gpu-paths.bin', 'corrected-paths.bin'):
        raw = checked(directory / name)
        if len(raw) != 16 * path_format.size:
            raise ValueError('missing focused path stream')
        path_bytes[name] = raw
        streams[name] = list(path_format.iter_unpack(raw))
    flags_raw, parts_raw = checked(directory / 'routing-flags.bin'), checked(directory / 'gpu-parts.bin')
    if len(flags_raw) != 64 or len(parts_raw) != 16 * 7 * part_format.size:
        raise ValueError('missing flags or depth evidence')
    flags, parts = struct.unpack('<16I', flags_raw), list(part_format.iter_unpack(parts_raw))
    rows, max_error = [], 0.0
    for sample, expected in enumerate(cpu['cpu_samples']):
        raw, corrected = streams['gpu-paths.bin'][sample], streams['corrected-paths.bin'][sample]
        start, end = sample * path_format.size, (sample + 1) * path_format.size
        if flags[sample] & ~63 or (not flags[sample] and
                path_bytes['gpu-paths.bin'][start:end] != path_bytes['corrected-paths.bin'][start:end]):
            raise ValueError('unknown route or unflagged mutation')
        values = [corrected[k*4+c] for k in range(4) for c in range(3)]
        if any(not math.isfinite(x) or x < 0 for x in values):
            raise ValueError('invalid corrected values')
        max_error = max(max_error, max(abs(a-b) for a,b in zip(values, expected['components'])))
        sample_parts = parts[sample*7:(sample+1)*7]
        rows.append(dict(sample=sample, raw_counters=list(raw[16:]), corrected_counters=list(corrected[16:]),
            cpu_counters=expected['counters'], routing_flags=flags[sample],
            early_depths=[dict(depth=k+1, route_mask=p[10], nonpositive_branches=p[11])
                          for k,p in enumerate(sample_parts) if p[10] or p[11]]))
    keys = ('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
    exact = all(r['corrected_counters'] == r['cpu_counters'] for r in rows)
    expected_audit = dict(proposal_bvh_queries=sum(x['queries'] for x in cpu['cpu_samples']),
        component_attempts=16*7, component_nulls=sum(x['nulls'] for x in cpu['cpu_samples']),
        own_checks=sum(x['own'] for x in cpu['cpu_samples']))
    exact = exact and all(meta['all_split'][key] == value for key,value in expected_audit.items())
    audit = meta['all_split']
    maxima = ('max_own_log_error_bound','max_conditioned_error_fraction',
              'max_unconditioned_error_fraction','max_weight')
    if (any(not math.isfinite(audit[k]) or audit[k] < 0 for k in maxima)
            or audit[maxima[0]] > 1e-6 or audit[maxima[1]] > 1 or audit[maxima[3]] > 8):
        raise ValueError('original numerical audit guard failed')
    for key,i in zip(keys,range(4)):
        if meta[key] != sum(r['corrected_counters'][i] for r in rows):
            raise ValueError('aggregate path counter mismatch')
    sys.path.insert(0, str(HERE.parent / 'n010_comparison_readiness'))
    checked(HERE.parent / 'n010_comparison_readiness/readiness_preflight.py')
    from readiness_preflight import replay
    ledger = json.loads(checked(directory / 'allocation-ledger.json'))
    if not replay(ledger):
        raise ValueError('owned memory replay failure')
    dispatches = [json.loads(x) for x in checked(directory / 'dispatches.jsonl').splitlines()]
    if len(dispatches) != 7 or any(
            (x['begin'],x['end'],x['tile_begin'],x['tile_count'],x['depth']) != (0,16,0,1,i+1)
            or not 0 <= x['submit_wait_wall_seconds_diagnostic'] <= .250 for i,x in enumerate(dispatches)):
        raise ValueError('focused depth/resource boundary failure')
    return dict(reproduces_prior_corrected_pixel_counts=[meta[k] for k in keys] == cpu['gpu_counters'],
        all16_corrected_scored_and_proposal_counts_exact=exact,
        max_corrected_sample_component_error=max_error, sample_rows=rows,
        cpu_expected_audit=expected_audit, gpu_audit=meta['all_split'],
        owned_peak_bytes=ledger['true_peak_owned_bytes'], owned_teardown_zero=True,
        causal_scope='Early-branch route telemetry is diagnostic; no full-frame or ray-level cause is inferred automatically')


if __name__ == '__main__':
    raise SystemExit(main())

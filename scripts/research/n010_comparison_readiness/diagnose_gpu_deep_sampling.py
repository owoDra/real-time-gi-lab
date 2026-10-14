#!/usr/bin/env python3
"""Post-hoc ROI replay and CPU-trigonometry intervention; never admission."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import struct
import subprocess
import time

from compile_gpu_reference import decorate
from reference_provenance import ROOT, sha

LANE = ROOT / 'research/lanes/n010-comparison-readiness'
BASE = ROOT / 'out/research/n010-comparison-readiness'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('source anchor must occur exactly once: ' + old[:80])
    return text.replace(old, new)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))


def invoke(command, work, name):
    start = time.monotonic()
    try:
        r = subprocess.run(command, capture_output=True, text=True,
                           timeout=300, preexec_fn=limits)
        row = dict(command=command, returncode=r.returncode,
                   stdout=r.stdout, stderr=r.stderr)
    except subprocess.TimeoutExpired:
        row = dict(command=command, returncode=None, failure='elapsed guard')
    row['wall_seconds_diagnostic'] = time.monotonic() - start
    (work / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    if row['returncode'] != 0:
        raise RuntimeError('retained failed step: ' + name)
    return row


def payload(path):
    raw = path.read_bytes()
    if raw[:8] != b'N008F64\0':
        raise ValueError('invalid sidecar')
    width, height, spp, seed = struct.unpack_from('<IIIQ', raw, 8)
    if (width, height, spp, seed) != (320, 180, 8192, 305419896):
        raise ValueError('unexpected frame/sample identity')
    if len(raw) != 28 + width * height * 192:
        raise ValueError('unexpected sidecar length')
    return raw


def run(args):
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing diagnostic output')
    args.work.mkdir(parents=True)
    inputs = [LANE / 'results/082-gpu-reference-deep-conformance-resource-followup.json',
              LANE / 'results/084-gpu-deep-numerical-failure-map.json',
              LANE / 'experiments/022-posthoc-deep-sampling-diagnostic.md',
              ROOT / 'src/research/n010_comparison_readiness/gpu_reference_main.cpp',
              ROOT / 'shaders/research/n010_comparison_readiness/n010_gpu_oracle.comp.glsl',
              BASE / 'gpu-reference-snapshot-v1/n010_reference_snapshot.hpp',
              BASE / 'gpu-reference-snapshot-v1/n010_reference_context.hpp',
              BASE / 'references-v1/C1_T_B8/scene.n008',
              BASE / 'sobol16x262144.bin', Path(__file__)]
    failure = json.loads(inputs[1].read_text())
    pixels = [r['pixel'] for r in failure['largest_16_pixels'][:8]]
    if len(set(pixels)) != 8:
        raise ValueError('invalid fixed diagnostic selection')
    selection = '{' + ','.join(map(str, pixels)) + '}'
    report = dict(schema='n010-deep-sampling-intervention/1', complete=False,
                  gpu_run=False, eligible_for_references=False,
                  classification='POSTHOC_DIAGNOSTIC_NOT_ADMISSION',
                  selected_pixels=pixels,
                  input_sha256={str(p.relative_to(ROOT)): sha(p) for p in inputs},
                  steps=[])
    try:
        host = inputs[3].read_text()
        host = replace_once(host, '    Context c;c.init();', r'''
    const std::vector<uint32_t> selected = SELECTION;
    std::vector<GStats> cpu(pixels);
    for(auto pixel:selected) {
        N::Oracle::PrimaryCache cache;
        for(uint32_t sample=0;sample<spp;++sample) {
            N::N010NetRng rng(seed,pixel,sample);N::Rgb comp[N::kComponents+1]{};
            N::RenderCounters cnt{};
            oracle.sample(pixel%scene.width,pixel/scene.width,rng,comp,cnt,nullptr,&cache);
            for(int c=0;c<3;++c)comp[N::kComponents][c]=(comp[N::kEmission][c]+comp[N::kDirect][c])+comp[N::kIndirect][c];
            for(int k=0;k<4;++k)for(int c=0;c<3;++c){cpu[pixel].sum[k].v[c]+=comp[k][c];cpu[pixel].sum2[k].v[c]+=comp[k][c]*comp[k][c];}
            cpu[pixel].counters[0]+=cnt.primary_hits;cpu[pixel].counters[1]+=cnt.shadow_tests;
            cpu[pixel].counters[2]+=cnt.shadow_blocked;cpu[pixel].counters[3]+=cnt.backface_absorbed;
        }
    }
    sidecar(out/"cpu.f64",scene,seed,spp,cpu.data());
    std::ofstream cpuraw(out/"cpu.stats",std::ios::binary);
    for(auto pixel:selected)cpuraw.write(reinterpret_cast<const char*>(&cpu[pixel]),sizeof(GStats));
    cpuraw.close();
    std::vector<std::array<double,2>> trig(selected.size()*spp*7);
    for(size_t slot=0;slot<selected.size();++slot)for(uint32_t sample=0;sample<spp;++sample) {
        N::N010NetRng rng(seed,selected[slot],sample);
        for(uint32_t bounce=0;bounce<7;++bounce){rng.uniform();double phi=2.0*N::kPi*rng.uniform();trig[(slot*spp+sample)*7+bounce]={std::sin(phi),std::cos(phi)};}
    }
    Context c;c.init();
'''.replace('SELECTION', selection))
        host = replace_once(host, 'upload(&fault,sizeof fault);',
                            'upload(&fault,sizeof fault);upload(selected.data(),selected.size()*sizeof(uint32_t));upload(trig.data(),trig.size()*sizeof(trig[0]));')
        for old, new in [('LayoutBinding,9>', 'LayoutBinding,11>'),
                         ('j<9;', 'j<11;'),
                         ('STORAGE_BUFFER,9}', 'STORAGE_BUFFER,11}'),
                         ('BufferInfo,9>', 'BufferInfo,11>'),
                         ('DescriptorSet,9>', 'DescriptorSet,11>'),
                         ('c.device,9,writes', 'c.device,11,writes'),
                         ('uint32_t((pixels+63)/64)', 'uint32_t((selected.size()+63)/64)')]:
            if old not in host:
                raise ValueError('missing host binding/dispatch anchor ' + old)
            host = host.replace(old, new)
        host = replace_once(host, 'params.seed[2]=scene.falloff==N::Falloff::N001Soft?1:0;',
                            'params.seed[2]=scene.falloff==N::Falloff::N001Soft?1:0;params.seed[3]=DIAG_MODE;params.interval[2]=spp;params.interval[3]=uint32_t(selected.size());')
        host = replace_once(host, '    sidecar(out/"o.f64",scene,seed,spp,values);',
                            '    std::ofstream gpuRaw(out/"gpu.stats",std::ios::binary);for(auto pixel:selected)gpuRaw.write(reinterpret_cast<const char*>(&values[pixel]),sizeof(GStats));gpuRaw.close();\n    sidecar(out/"o.f64",scene,seed,spp,values);')
        shader = inputs[4].read_text()
        shader = replace_once(shader, 'const uint MISS=', '''layout(std430,binding=9) readonly buffer Selection { uint selected[]; };
layout(std430,binding=10) readonly buffer Trigonometry { dvec2 trig[]; };
uint diagnosticSlot,diagnosticSample,diagnosticBounce;
const uint MISS=''')
        shader = replace_once(shader, 'dvec2 sincosd(double phi) {',
                              'dvec2 sincosd(double phi) {\n    if(seedWords.w!=0u)return trig[(diagnosticSlot*interval.z+diagnosticSample)*7u+diagnosticBounce-1u];')
        shader = replace_once(shader, 'uint pixel=gl_GlobalInvocationID.x;if(pixel>=sizes.x)return;',
                              'uint slot=gl_GlobalInvocationID.x;if(slot>=interval.w)return;diagnosticSlot=slot;uint pixel=selected[slot];')
        shader = replace_once(shader, 'precise dvec3 indirect=dvec3(0.0LF);uint dim=0u;',
                              'diagnosticSample=sampleIndex;precise dvec3 indirect=dvec3(0.0LF);uint dim=0u;')
        shader = replace_once(shader, 'double u1=uniform01(pixel,sampleIndex,dim),u2=uniform01(pixel,sampleIndex,dim);',
                              'diagnosticBounce=bounce;double u1=uniform01(pixel,sampleIndex,dim),u2=uniform01(pixel,sampleIndex,dim);')
        shader_path = args.work / 'roi.comp.glsl'
        shader_path.write_text(shader.replace('precise ', ''))
        compiler = ROOT / 'build/n009/_deps/glslang-build/StandAlone/glslang'
        unannotated = args.work / 'raw.spv'
        report['steps'].append(invoke([str(compiler), '-V', '--target-env', 'vulkan1.2', '-S', 'comp', str(shader_path), '-o', str(unannotated)], args.work, 'shader-build'))
        data, count = decorate(unannotated.read_bytes())
        spv = args.work / 'roi.spv';spv.write_bytes(data)
        report['no_contraction_results'] = count
        sdk = BASE / 'external/RTXGI-DDGI/rtxgi-sdk/include'
        inc = BASE / 'gpu-reference-snapshot-v1'
        include_paths = [inc, sdk, ROOT / 'src/research/n010_comparison_readiness',
                         ROOT / 'build/n007/_deps/vulkan-headers-for-vk-bootstrap-src/include',
                         Path('/nix/store/1rhchilgcirwrwmq4h8xqldkn8lx209x-libx11-1.8.13-dev/include'),
                         Path('/nix/store/h11h9pq0d23c8n2k0pd162mgzg1z4jca-xorgproto-2025.1/include')]
        for mode, name in [(0, 'polynomial'), (1, 'cpu-trigonometry')]:
            source = args.work / (name + '.cpp');source.write_text(host.replace('DIAG_MODE', str(mode)))
            binary = args.work / ('phos-n010-roi-' + name)
            command = ['g++', '-std=c++20', '-O2', '-fno-fast-math', '-ffp-contract=off', '-pthread',
                       '-DRTXGI_COORDINATE_SYSTEM=2', '-DRTXGI_DDGI_RESOURCE_MANAGEMENT=0',
                       '-DRTXGI_DDGI_USE_SHADER_CONFIG_FILE=0', '-DRTXGI_GFX_NAME_OBJECTS=1']
            command += ['-I' + str(p) for p in include_paths]
            command += [str(source), str(ROOT / 'build/n010-ddgi-sdk/lib/librtxgi-vulkan.a'),
                        '/run/current-system/sw/share/nix-ld/lib/libvulkan.so', '-o', str(binary)]
            report['steps'].append(invoke(command, args.work, name + '-build'))
            output = args.work / name
            command = ['bash', str(ROOT / 'scripts/run_with_vulkan.sh'), str(binary),
                       str(inputs[7]), str(inputs[8]), str(spv), '305419896', '8192', '16', str(output)]
            report['gpu_run'] = True
            report['steps'].append(invoke(command, args.work, name + '-runtime'))
            report.setdefault('derived_sha256', {})[name] = {'source': sha(source), 'binary': sha(binary)}
        cpu_saved = payload(BASE / 'references-v1/C1_T_B8/o.n8192.s0.f64')
        gpu_saved = payload(BASE / 'gpu-reference-full-conformance-v3/C1-B8-seed0/gpu/o.f64')
        report['saved_payload_sha256'] = dict(cpu=hashlib.sha256(cpu_saved).hexdigest(), gpu=hashlib.sha256(gpu_saved).hexdigest())
        report['shader_sha256'] = sha(spv)
        rows = []
        for name in ('polynomial', 'cpu-trigonometry'):
            output = args.work / name
            cpu = payload(output / 'cpu.f64');gpu = payload(output / 'o.f64')
            cpustats = (output / 'cpu.stats').read_bytes();gpustats = (output / 'gpu.stats').read_bytes()
            meta = json.loads((output / 'gpu.json').read_text())
            for slot, pixel in enumerate(pixels):
                start = 28 + pixel * 192
                old_cpu = cpu_saved[start:start+192];old_gpu = gpu_saved[start:start+192]
                new_cpu = cpu[start:start+192];new_gpu = gpu[start:start+192]
                a = struct.unpack('<24d', new_cpu);b = struct.unpack('<24d', new_gpu)
                cc = struct.unpack_from('<4Q', cpustats, slot*288+256);gc = struct.unpack_from('<4Q', gpustats, slot*288+256)
                rows.append(dict(mode=name, pixel=pixel, x=pixel%320, y=pixel//320,
                                 cpu_reproduces_saved_byte_equal=new_cpu==old_cpu,
                                 gpu_reproduces_saved_byte_equal=new_gpu==old_gpu,
                                 max_abs_mean=max(abs(x-y) for x,y in zip(a[:12],b[:12])),
                                 max_abs_moment=max(abs(x-y) for x,y in zip(a[12:],b[12:])),
                                 cpu_counters=cc, gpu_counters=gc, counters_equal=cc==gc,
                                 faults=meta['fault_flags'], finite=meta['all_finite']))
        report['rows'] = rows
        report['replay_valid'] = all(r['cpu_reproduces_saved_byte_equal'] and r['gpu_reproduces_saved_byte_equal'] for r in rows if r['mode']=='polynomial')
        report['scope'] = 'Selected post-hoc pixels only; no exclusion, no reference admission, no full conformance or GPU performance verdict.'
    except Exception as error:
        report['failure'] = str(error)
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report.get(k) for k in ('complete', 'failure', 'replay_valid')}))
    return 2 if report.get('failure') else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))

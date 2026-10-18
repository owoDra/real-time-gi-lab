#!/usr/bin/env python3
"""Plan148: private full-query source/command metadata; no native compilation."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'out/research/n010-comparison-readiness'
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/148-private-full-query-receipts.md'
HEADER = ROOT/'src/research/n010_comparison_readiness/raw_query_capture.hpp'
BUILD = ROOT/'build/n009'
GENERATED = BUILD/'src/research/n010_comparison_readiness/generated'
PARENT = BASE/'deferred-image-calibration-build-v1'
WORK = BASE/'raw-query-pilot-source-v1'
FUTURE_BUILD = BASE/'raw-query-pilot-build-v1'
OUTPUT = RESULTS/'504-raw-query-pilot-source-prepare.json'
INPUTS = {}


def checked(path, digest=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if digest is not None and got != digest:raise ValueError('changed input '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != got:raise ValueError('input changed during preparation')
    INPUTS[str(path)] = got
    return raw


def overlay(raw, edits):
    original = raw.decode()
    source = original
    for before, after in edits:
        if source.count(before) != 1 or after in source:raise ValueError('nonunique query-source anchor '+before[:70])
        source = source.replace(before, after, 1)
    restored = source
    for before, after in reversed(edits):
        if restored.count(after) != 1:raise ValueError('nonunique query-source inverse')
        restored = restored.replace(after, before, 1)
    if restored != original:raise ValueError('whole query-source inverse differs')
    return source, dict(whole_inverse_exact=True, original_sha256=hashlib.sha256(raw).hexdigest(),
                       generated_sha256=hashlib.sha256(source.encode()).hexdigest(),
                       edits=[dict(before=a, after=b) for a,b in edits])


def sources():
    b002 = checked(GENERATED/'n010_b002_vulkan.cpp')
    vk = checked(GENERATED/'n010_vk_context.cpp')
    capture = checked(PARENT/'minimal_capture.cpp')
    dense = checked(PARENT/'minimal_pt.cpp')
    inc = '#include "raw_query_capture.hpp"\n'
    b002_edits = [
        ('#include "allocation_ledger.hpp"\n', '#include "allocation_ledger.hpp"\n'+inc),
        ('        fail("B002 selected compute queue does not support timestamps");\n    }\n}',
         '        fail("B002 selected compute queue does not support timestamps");\n    }\n'
         '    phos::gi::research::n010::RawQueryCapture::instance().install(\n'
         '        dispatch_, timestamp_period_ns_, queue.timestampValidBits, queue_family_);\n}')]
    vk_edits = [
        ('#include "allocation_ledger.hpp"\n', '#include "allocation_ledger.hpp"\n'+inc),
        ('        fail("Selected compute queue does not support timestamps");\n    }\n}',
         '        fail("Selected compute queue does not support timestamps");\n    }\n'
         '    phos::gi::research::n010::RawQueryCapture::instance().install(\n'
         '        dispatch_, timestamp_period_ns_, q.timestampValidBits, queue_family_);\n}')]
    prefix = 'phos::gi::research::n010::RawQueryCapture::instance()'
    capture_edits = [
        ('#include "neutral_work.hpp"\n', '#include "neutral_work.hpp"\n'+inc),
        ('        if(!calibration_doses.empty()) {',
         '        if(!calibration_doses.empty() || std::getenv("PHOS_N010_CALIBRATION"))\n'
         '            throw std::runtime_error("descriptive raw capture forbids calibration/reset mode");\n'
         '        if(!calibration_doses.empty()) {'),
        ('            if(!recovery) return;',
         '            '+prefix+'.phase(std::int32_t(index),"readback");'),
        ('        auto gpu_frame=runtime.run_frame(false);',
         '        '+prefix+'.phase(0,"source");\n        auto gpu_frame=runtime.run_frame(false);'),
        ('        if(target)gpu_frame=topology ?',
         '        if(target)'+prefix+'.phase(1,"first-target");\n        if(target)gpu_frame=topology ?'),
        ('            gpu_frame=runtime.run_frame(true);',
         '            '+prefix+'.phase(std::int32_t(step+2),"recovery");\n'
         '            gpu_frame=runtime.run_frame(true);'),
        ('        phos::gi::research::n010::AllocationLedger::instance().phase("diagnostic-readback");',
         '        '+prefix+'.phase(-2,"final-readback");\n'
         '        phos::gi::research::n010::AllocationLedger::instance().phase("diagnostic-readback");'),
        ('        std::cout << "N010 GPU diagnostics captured; legacy N007 CPU audit not run.\\n";',
         '        '+prefix+'.phase(-3,"teardown");\n'
         '        std::cout << "N010 GPU diagnostics captured; legacy N007 CPU audit not run.\\n";')]
    dense_edits = [
        ('#include "neutral_work.hpp"\n', '#include "neutral_work.hpp"\n'+inc),
        ('        N010DeferredImages deferred(doses.empty()?0:frames);',
         '        if(family!="dense-rc" || !doses.empty() || std::getenv("PHOS_N010_CALIBRATION"))\n'
         '            throw std::runtime_error("descriptive dense capture forbids PT/calibration mode");\n'
         '        N010DeferredImages deferred(doses.empty()?0:frames);'),
        ('            n::AllocationLedger::instance().phase("frame-"+label+"-"+std::to_string(f));',
         '            n::RawQueryCapture::instance().phase(std::int32_t(f),label.c_str());\n'
         '            n::AllocationLedger::instance().phase("frame-"+label+"-"+std::to_string(f));'),
        ('            n::AllocationLedger::instance().phase("diagnostic-readback-"+std::to_string(f));',
         '            n::RawQueryCapture::instance().phase(std::int32_t(f),"readback");\n'
         '            n::AllocationLedger::instance().phase("diagnostic-readback-"+std::to_string(f));'),
        ('        times<<"]}\\n"; if(!times) throw std::runtime_error("timing output failed");',
         '        n::RawQueryCapture::instance().phase(-3,"teardown");\n'
         '        times<<"]}\\n"; if(!times) throw std::runtime_error("timing output failed");')]
    prepared, inverses = {}, {}
    for name, raw, edits in (('b002_context.cpp',b002,b002_edits),('vk_context.cpp',vk,vk_edits),
                             ('capture.cpp',capture,capture_edits),('dense.cpp',dense,dense_edits)):
        prepared[name], inverses[name] = overlay(raw, edits)
    prepared['runtime.cpp'] = checked(PARENT/'minimal_runtime.cpp').decode()
    prepared['raw_query_capture.hpp'] = checked(HEADER).decode()
    # Only host phase/serialization/guard edits surround this unchanged GPU lambda.
    a,b = dense.decode(),prepared['dense.cpp']
    start,end = '        const auto run_image=', '        N010DeferredImages deferred'
    # The new explicit mode guard is outside the lambda and removed for this check.
    new_guard = dense_edits[1][1].removesuffix(dense_edits[1][0])
    b = b.replace(new_guard,'',1)
    if a[a.index(start):a.index(end)] != b[b.index(start):b.index(end)]:
        raise ValueError('dense GPU lambda changed')
    return prepared, inverses


def command_plan(parent_inputs):
    stages, identities = [], {}
    for target, replacements in (
        ('phos-n010-capture', {
            GENERATED/'n010_capture_main.cpp':'capture.cpp',
            GENERATED/'n010_runtime.cpp':'runtime.cpp',
            GENERATED/'n010_b002_vulkan.cpp':'b002_context.cpp',
            GENERATED/'n010_vk_context.cpp':'vk_context.cpp'}),
        ('phos-n010-pixel-pt', {
            ROOT/'src/research/n010_comparison_readiness/pixel_pt_main.cpp':'dense.cpp',
            GENERATED/'n010_b002_vulkan.cpp':'b002_context.cpp'})):
        text = subprocess.check_output(['ninja','-C',str(BUILD),'-t','commands',target],text=True)
        commands = []
        for line in text.splitlines():
            args,cwd = shlex.split(line),BUILD
            if args[:1] == ['cd'] and len(args)>3 and args[2]=='&&':cwd,args = Path(args[1]),args[3:]
            if args[:2] == [':','&&'] and args[-2:] == ['&&',':']:args = args[2:-2]
            if '-c' in args or ('-o' in args and args[args.index('-o')+1] == target):
                if any(a in ('&&',';','|',':') for a in args):raise ValueError('shell operation in native command')
                commands.append((args,cwd))
        mapping = {}
        role = 'rc' if target.endswith('capture') else 'dense'
        found = set()
        for args,cwd in commands:
            if '-c' not in args:continue
            source = Path(args[args.index('-c')+1])
            if source not in replacements:continue
            if source in found:raise ValueError('duplicate original compiler command')
            found.add(source)
            old_object = args[args.index('-o')+1]
            name = role+'-'+Path(replacements[source]).stem
            obj = FUTURE_BUILD/(name+'.o')
            mapping[old_object] = str(obj)
            args = list(args)
            for flag,value in (('-c',WORK/replacements[source]),('-o',obj),('-MF',FUTURE_BUILD/(name+'.d')),('-MT',obj)):
                if flag in args:args[args.index(flag)+1] = str(value)
            args.insert(1,'-I'+str(WORK))
            args = [a.replace(str(BUILD/'shaders'),str(WORK/'shaders')) for a in args]
            compiler = Path(args[0]).resolve();checked(compiler)
            deps = subprocess.check_output(['ninja','-C',str(BUILD),'-t','deps',old_object],text=True)
            for line in deps.splitlines():
                if line.startswith('    '):
                    dep = Path(line.strip());checked(dep if dep.is_absolute() else BUILD/dep)
            stages.append(dict(label=name,command=args,cwd=str(cwd),produced=str(obj),compiler_realpath=str(compiler)))
        if found != set(replacements):raise ValueError('missing original private source commands')
        links = [(a,c) for a,c in commands if '-c' not in a and '-o' in a and a[a.index('-o')+1] == target]
        if len(links) != 1:raise ValueError('unique original linker command required')
        args,cwd = links[0]
        for arg in args:
            if arg.endswith(('.o','.a')) and arg not in mapping:
                p = Path(arg);p = p if p.is_absolute() else cwd/p
                digest = parent_inputs.get(str(p.resolve()))
                if digest is None:raise ValueError('unbound reused object/library '+str(p))
                checked(p,digest)
        args = [mapping.get(a,a) for a in args]
        executable = FUTURE_BUILD/('phos-n010-raw-query-'+role)
        args[args.index('-o')+1] = str(executable)
        compiler = Path(args[0]).resolve();checked(compiler)
        stages.append(dict(label=role+'-link',command=args,cwd=str(cwd),produced=str(executable),compiler_realpath=str(compiler)))
        identities[role] = str(executable)
    if len(stages) != 8:raise ValueError('exact eight private compile/link stages required')
    return stages,identities


def main():
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180);started,cpu = time.monotonic(),time.process_time()
    if OUTPUT.exists() or WORK.exists():raise ValueError('fresh source/result required; no overwrite')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for p in (Path(__file__).resolve(),PLAN,HEADER):
        if subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))]) != checked(p):
            raise ValueError('commit exact source/recipe before preparation')
    parent = json.loads(checked(RESULTS/'184-deferred-image-calibration-fixture-build.json'))
    if not (parent['complete'] and parent['all_pass'] and parent['whole_inverse_to_167']
            and parent['runtime_file_and_pt_timed_bodies_unchanged']):
        raise ValueError('complete unchanged184 parent required')
    for path,digest in parent['input_sha256'].items():checked(path,digest)
    for name,digest in parent['generated_sha256'].items():checked(PARENT/name,digest)
    checked(BUILD/'build.ninja')
    prepared,inverses = sources()
    stages,binaries = command_plan(parent['input_sha256'])
    shaders = {p.name:checked(p) for p in sorted((BUILD/'shaders').glob('*.spv'))}
    if not shaders:raise ValueError('original compiled shaders missing')
    for path,digest in list(INPUTS.items()):checked(path,digest)
    WORK.mkdir()
    for name,source in prepared.items():(WORK/name).write_text(source)
    (WORK/'shaders').mkdir()
    for name,raw in shaders.items():(WORK/'shaders'/name).write_bytes(raw)
    result = dict(schema='n010-raw-query-pilot-source-prepare/1',complete=True,
        classification='PRIVATE_RAW_QUERY_SOURCE_ONLY_RUNTIME_NOT_RUN',source_preparation_valid=True,
        source_commit=commit,input_sha256=INPUTS,edits=inverses,stages=stages,binaries=binaries,
        whole_source_inverses_exact=True,runtime_entire_file_byte_identical_to184=True,
        dense_gpu_lambda_byte_identical_to184=True,all_shader_bytes_unchanged=True,
        compiled=False,gpu_run=False,native_executed=False,accepted_timing=False,reference_admission=False,
        remaining='Actual private compilation, same-scope full runtime equivalence, raw intake and full36 final auditor',
        elapsed_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
        payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in WORK.rglob('*') if p.is_file()},
        tests='NOT_RUN; source/inverse/compiler-command metadata only')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0);print(result['classification'])


if __name__ == '__main__':main()

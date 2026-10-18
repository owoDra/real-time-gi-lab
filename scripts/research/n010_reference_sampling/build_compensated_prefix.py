#!/usr/bin/env python3
"""Plan155: prepare an exact-inverse candidate prefix, or compile it alone."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

import diagnose_selected_bounce_paths as D
import cover_wide8_original_controls as C
from run_primary_direction_sequence import require_no_other_research_worker

PLAN = D.RESULTS.parent/'experiments/155-compensated-exact-prefix-build.md'
PREPARE = D.RESULTS/'525-compensated-prefix-source-prepare.json'
OUTPUT = D.RESULTS/'526-compensated-prefix-build.json'
SOURCE = D.OUT/'compensated-prefix-source-v1'
BUILD = D.OUT/'compensated-prefix-build-v1'
PARENT = D.OUT/'compensated-full-deterministic-v1/build'
OVERLAYS = {
    'generate_point_guided_prefix.py':'8519c37cf0c8b1df98ef532f40c3779f1387c3017578b8c0294c2528487a654b',
    'generate_incremental_oracle.py':'34267414f93e37eb0f60bcab63c231884540ea45cfef3c37e7e30898c7819348',
}


def write(path, value, fresh=False):
    with path.open('x' if fresh else 'w') as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def bind(path):
    proof = json.loads(D.checked(path))
    if not proof['complete']:raise ValueError('terminal pinned input required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in proof.get(group,{}).items():D.checked(Path(name),digest)
    return proof


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def unchanged():
    for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)


def prepare(parent, commit):
    if PREPARE.exists() or SOURCE.exists():raise ValueError('fresh candidate prefix source required; no retry')
    helper = D.HERE.parent/'n010_comparison_readiness'
    for name,digest in OVERLAYS.items():D.checked(helper/name,digest)
    sys.path.insert(0,str(helper))
    spec = importlib.util.spec_from_file_location('n010_plan155_prefix_overlay',helper/'generate_point_guided_prefix.py')
    overlay = importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)
    for module in tuple(sys.modules.values()):
        name = getattr(module,'__file__',None)
        if name and Path(name).resolve().is_relative_to(D.ROOT/'scripts/research'):
            D.checked(Path(name).resolve())
    original = {'n010_rqmc_oracle.hpp':D.checked(PARENT/'n010_rqmc_oracle.hpp',
                    parent['payload_sha256'][str(PARENT/'n010_rqmc_oracle.hpp')]).decode(),
                'n010_rqmc_main.cpp':D.checked(PARENT/'exporter.cpp',
                    parent['payload_sha256'][str(PARENT/'exporter.cpp')]).decode()}
    source_command = list(parent['command'])
    command = list(source_command)
    command[-3] = str(SOURCE/'n010_rqmc_main.cpp')
    command[-1] = str(BUILD/'n010_compensated_prefix')
    if source_command[-2] != '-o' or not source_command[-3].endswith('/exporter.cpp'):
        raise ValueError('unique original452 compiler source/output positions required')
    compiler = Path(shutil.which(command[0])).resolve();D.checked(compiler)
    if str(compiler) != parent['compiler_realpath']:raise ValueError('original452 compiler changed')
    SOURCE.mkdir()
    for name,text in original.items():(SOURCE/name).write_text(text)
    edits = {name:[] for name in ('header','main','loader')}
    latest = dict(header=original['n010_rqmc_oracle.hpp'],main=original['n010_rqmc_main.cpp'],loader=overlay.LOADER)
    def once(value, before, after):
        matches = [name for name,current in latest.items() if current == value]
        if len(matches) != 1:raise ValueError('prefix edit input not unique')
        name = matches[0];changed = D.once(value,before,after)
        edits[name].append((before,after));latest[name] = changed
        write(SOURCE/'source-edits.json',edits)
        return changed
    result = dict(schema='n010-compensated-prefix-source/1',complete=False,source_preparation_valid=False,
        source_commit=commit,input_sha256=D.INPUTS,numerical_variant='compensated-raw-target-v1',
        classification='COMPENSATED_PREFIX_SOURCE_PREPARING',gpu_run=False,compiled=False,
        native_executed=False,accepted_timing=False,reference_admission=False,
        tests='NOT_RUN; exact inverse source/command metadata only')
    write(PREPARE,result,True)
    try:
        overlay.once = once;overlay.overlay(SOURCE)
        main = (SOURCE/'n010_rqmc_main.cpp').read_text()
        main = once(main,'        const Oracle oracle(scene);',
            '        if(spp==0 || spp>262144 || (spp&(spp-1)) ||\n'
            '           (prefix_spp && spp!=2*prefix_spp))\n'
            '            throw std::runtime_error("prefix requires consecutive original dyadic levels");\n'
            '        const Oracle oracle(scene);')
        main = once(main,'        std::printf("]}\\n");',
            '        std::printf("],\\"prefix_begin\\":%u,\\"audit_scope\\":'
            '\\"new_sample_interval\\"}\\n",prefix_spp);')
        (SOURCE/'n010_rqmc_main.cpp').write_text(main)
        inverses = {}
        for filename,group in (('n010_rqmc_oracle.hpp','header'),('n010_rqmc_main.cpp','main')):
            text = (SOURCE/filename).read_text()
            for before,after in reversed(edits[group]):text = D.once(text,after,before)
            inverses[filename] = text == original[filename]
        loader = latest['loader']
        for before,after in reversed(edits['loader']):loader = D.once(loader,after,before)
        inverses['retained_loader'] = loader == overlay.LOADER
        header = (SOURCE/'n010_rqmc_oracle.hpp').read_text()
        start,end = '    std::vector<PixelStats> render(', '    const Bvh& bvh()'
        old = original['n010_rqmc_oracle.hpp']
        outside = header[:header.index(start)] == old[:old.index(start)] and header[header.index(end):] == old[old.index(end):]
        if not all(inverses.values()) or not outside:raise ValueError('candidate prefix source inverse/outside render differs')
        unchanged()
        result.update(complete=True,source_preparation_valid=True,
            classification='COMPENSATED_PREFIX_SOURCE_ONLY_BUILD_AND_RUNTIME_NOT_RUN',
            source_inverses_exact=inverses,physical_proposal_bvh_compensation_outside_render_unchanged=outside,
            command=command,original452_command=source_command,compiler_realpath=str(compiler),
            audit_scope='new_sample_interval; prior diagnostic totals not silently restored')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(complete=True,failure=str(error),classification='COMPENSATED_PREFIX_SOURCE_FAILURE_PARTIALS_RETAINED')
    result['payload_sha256'] = {str(p):C.sha(p) for p in SOURCE.iterdir() if p.is_file()}
    write(PREPARE,result)
    print(result['classification'])
    return 0 if result['source_preparation_valid'] else 2


def build(commit):
    if BUILD.exists() or OUTPUT.exists():raise ValueError('fresh compiler output required; no retry')
    prep = bind(PREPARE)
    if not prep['source_preparation_valid']:raise ValueError('successful exact525 source required')
    command = prep['command'];compiler = Path(shutil.which(command[0])).resolve()
    if str(compiler) != prep['compiler_realpath']:raise ValueError('pinned compiler changed')
    require_no_other_research_worker();unchanged();BUILD.mkdir()
    receipt = BUILD/'compile.resources.json'
    result = dict(schema='n010-compensated-prefix-build/1',complete=False,build_valid=False,
        source_commit=commit,input_sha256=D.INPUTS,numerical_variant='compensated-raw-target-v1',
        classification='COMPENSATED_PREFIX_COMPILER_RUNNING',command=command,compiler_realpath=str(compiler),
        gpu_run=False,native_rendering_executed=False,accepted_timing=False,reference_admission=False,
        tests='NOT_RUN; one isolated compiler invocation only')
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(220,220))
        write(receipt,dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=300),True)
    write(OUTPUT,result,True)
    try:
        before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
        with (BUILD/'compile.stdout').open('wb') as stdout,(BUILD/'compile.stderr').open('wb') as stderr:
            child = subprocess.Popen(command,cwd=D.ROOT,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
            result['compiler_pid'] = child.pid;write(OUTPUT,result)
            try:code = child.wait(timeout=300)
            except subprocess.TimeoutExpired:
                own = json.loads(receipt.read_text())
                if (own['pid'],own['pgid'],own['start_ticks']) != (child.pid,child.pid,start_ticks(child.pid)):
                    raise ValueError('owned compiler identity differs; refuse signalling')
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait(timeout=5);code = 'ELAPSED_GUARD_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(compiler_terminal=True,returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
        write(OUTPUT,result)
        own = json.loads(D.checked(receipt))
        if (code != 0 or own['pid'] != own['pgid'] or own['pid'] != child.pid
                or type(own['start_ticks']) is not int or own['start_ticks'] <= 0
                or own['cpu'] != [220,220] or own['address_space'] != [4*1024**3]*2
                or own['affinity'] != [31] or own['nice'] != 15 or own['command'] != command
                or own['elapsed_limit_seconds'] != 300 or result['elapsed_seconds'] >= 300
                or result['child_cpu_seconds'] > 220 or not Path(command[-1]).read_bytes().startswith(b'\x7fELF')):
            raise ValueError('compiler/resource/output failure; no retry')
        unchanged()
        if Path(shutil.which(command[0])).resolve() != compiler:raise ValueError('compiler changed during build')
        result.update(complete=True,build_valid=True,terminal_identity_verified=True,
            classification='COMPENSATED_PREFIX_BUILD_COMPLETE_RUNTIME_NOT_RUN')
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result.update(complete=True,failure=str(error),classification='COMPENSATED_PREFIX_BUILD_FAILURE_PARTIALS_RETAINED')
    result['payload_sha256'] = {str(p):C.sha(p) for p in BUILD.iterdir() if p.is_file()}
    write(OUTPUT,result);print(result['classification'])
    return 0 if result['build_valid'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',action='store_true');group.add_argument('--build',action='store_true')
    args = parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120) if args.prepare else (220,220))
    resource.setrlimit(resource.RLIMIT_AS,((2 if args.prepare else 4)*1024**3,)*2)
    if args.prepare:signal.alarm(180)
    else:require_no_other_research_worker()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact155 recipe/driver before use')
    parent = bind(D.RESULTS/'452-compensated-full-exporter-build.json')
    if not parent['build_valid'] or not parent['terminal_identity_verified']:
        raise ValueError('actual452 compensated exporter build required')
    return prepare(parent,commit) if args.prepare else build(commit)


if __name__ == '__main__':raise SystemExit(main())

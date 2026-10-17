#!/usr/bin/env python3
"""Plan108: separate exact-inverse prefix overlay, compiler only, no rendering."""
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK = D.OUT / 'wide8-prefix-build-v1'
OUTPUT = D.RESULTS / '272-wide8-prefix-build.json'
PLAN = D.RESULTS.parent / 'experiments/108-wide8-prefix-build.md'
SOURCE = D.OUT / 'wide8-cpu-bvh-v1'
OVERLAYS = {
    'generate_point_guided_prefix.py':
        '8519c37cf0c8b1df98ef532f40c3779f1387c3017578b8c0294c2528487a654b',
    'generate_incremental_oracle.py':
        '34267414f93e37eb0f60bcab63c231884540ea45cfef3c37e7e30898c7819348',
}


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing prefix build; no retry')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
    for path in (Path(__file__).resolve(), PLAN, Path(C.__file__), Path(D.__file__),
                 D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(path)
    for stem in ('254', '257'):
        if not C.pinned_result(stem)['all_pass']:
            raise ValueError('selected backend proof required: ' + stem)
    directory = D.HERE.parent / 'n010_comparison_readiness'
    for name, digest in OVERLAYS.items():
        D.checked(directory / name, digest)
    # Imported modules supply the retained overlay/loader, not their CLI entry points.
    for name in ('generate_rqmc_oracle.py', 'reference_provenance.py',
                 'qualify_hybrid_references.py', 'qualify_references.py', 'n010lib.py'):
        path = directory / name
        if path.exists():
            D.checked(path)
    sys.path.insert(0, str(directory))
    spec = importlib.util.spec_from_file_location('n010_plan108_overlay',
                                                 directory / 'generate_point_guided_prefix.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for imported in list(sys.modules.values()):
        path = getattr(imported, '__file__', None)
        if path and Path(path).suffix == '.py' and Path(path).resolve().is_relative_to(D.ROOT):
            D.checked(Path(path).resolve())
    original = {
        'n010_rqmc_oracle.hpp': D.checked(SOURCE / 'n010_rqmc_oracle.hpp').decode(),
        'n010_rqmc_main.cpp': D.checked(SOURCE / 'exporter.cpp').decode(),
    }
    WORK.mkdir()
    for name, value in original.items():
        (WORK / name).write_text(value)
    edits = {name: [] for name in ('header', 'main', 'loader')}
    latest = dict(header=original['n010_rqmc_oracle.hpp'],
                  main=original['n010_rqmc_main.cpp'], loader=module.LOADER)

    def traced_once(value, old, new):
        matches = [name for name, current in latest.items() if current == value]
        if len(matches) != 1:
            raise ValueError('prefix edit source is not uniquely identified')
        name = matches[0]
        changed = D.once(value, old, new)
        edits[name].append((old, new))
        latest[name] = changed
        (WORK / 'source-edits.json').write_text(json.dumps(edits, indent=2) + '\n')
        return changed

    result = dict(schema='n010-wide8-prefix-build/1', complete=False, all_pass=False,
                  gpu_run=False, reference_admission=False, runtime_validated=False,
                  classification='ISOLATED_PREFIX_BUILD_ACQUIRING', input_sha256=D.INPUTS,
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  tests='NOT_RUN; isolated compiler invocation only, no native rendering')

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')

    save()
    try:
        module.once = traced_once
        module.overlay(WORK)
        source = (WORK / 'n010_rqmc_main.cpp').read_text()
        source = traced_once(source, '        const Oracle oracle(scene);',
            '        if(spp==0 || spp>262144 || (spp&(spp-1)) ||\n'
            '           (prefix_spp && spp!=2*prefix_spp))\n'
            '            throw std::runtime_error("prefix requires consecutive original dyadic levels");\n'
            '        const Oracle oracle(scene);')
        source = traced_once(source, '        std::printf("]}\\n");',
            '        std::printf("],\\"prefix_begin\\":%u,\\"audit_scope\\":'
            '\\"new_sample_interval\\"}\\n",prefix_spp);')
        (WORK / 'n010_rqmc_main.cpp').write_text(source)
        inverse = {}
        for name, changes in (('n010_rqmc_oracle.hpp', edits['header']),
                              ('n010_rqmc_main.cpp', edits['main'])):
            value = (WORK / name).read_text()
            for old, new in reversed(changes):
                value = D.once(value, new, old)
            inverse[name] = value == original[name]
        if not all(inverse.values()):
            raise ValueError('prefix source inverse differs')
        header = (WORK / 'n010_rqmc_oracle.hpp').read_text()
        begin, end = '    std::vector<PixelStats> render(', '    const Bvh& bvh()'
        outside = (header.split(begin)[0] == original['n010_rqmc_oracle.hpp'].split(begin)[0]
                   and header[header.index(end):] == original['n010_rqmc_oracle.hpp'][
                       original['n010_rqmc_oracle.hpp'].index(end):])
        if not outside:
            raise ValueError('physical/proposal/BVH source changed outside render')
        (WORK / 'source-edits.json').write_text(json.dumps(
            edits, indent=2) + '\n')
        command = ['c++', '-mavx512f', '-std=c++20', '-O3', '-fno-fast-math',
                   '-ffp-contract=off', '-pthread', '-I', str(D.ROOT / 'src/research/n008_hdr_oracle'),
                   str(WORK / 'n010_rqmc_main.cpp'), '-o', str(WORK / 'n010_wide8_prefix')]
        receipt = WORK / 'compile.resources.json'

        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
            receipt.write_text(json.dumps(dict(pid=os.getpid(),
                start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                command=command)) + '\n')

        result.update(command=command, source_inverses_exact=inverse,
                      physical_proposal_bvh_source_unchanged=outside,
                      audit_scope='new_sample_interval; prior diagnostics not silently restored')
        save()
        for path, digest in list(D.INPUTS.items()):
            D.checked(Path(path), digest)
        start = time.monotonic()
        child_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            proc = subprocess.run(command, capture_output=True, text=True,
                                  timeout=300, preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            (WORK / 'compile.stdout').write_bytes(error.stdout or b'')
            (WORK / 'compile.stderr').write_bytes(error.stderr or b'')
            result.update(compiler_terminal=True, elapsed_seconds=time.monotonic()-start,
                          failure_kind='COMPILER_ELAPSED_GUARD_NO_RETRY')
            raise ValueError('compiler elapsed guard; partials retained') from error
        (WORK / 'compile.stdout').write_text(proc.stdout)
        (WORK / 'compile.stderr').write_text(proc.stderr)
        child_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        result.update(returncode=proc.returncode, elapsed_seconds=time.monotonic()-start,
                      compiler_terminal=True,
                      cpu_seconds=(child_after.ru_utime+child_after.ru_stime
                                   -child_before.ru_utime-child_before.ru_stime))
        actual = json.loads(D.checked(receipt))
        if (actual['cpu'] != [220]*2 or actual['address_space'] != [4*1024**3]*2
                or actual['affinity'] != [31] or actual['nice'] != 15):
            raise ValueError('actual compiler resources differ')
        if proc.returncode:
            raise ValueError('compiler failure; no retry')
        for path, digest in list(D.INPUTS.items()):
            D.checked(Path(path), digest)
        result.update(complete=True, all_pass=True,
                      classification='ISOLATED_PREFIX_BUILD_COMPLETE_NO_RUNTIME_ADMISSION')
    except (ValueError, OSError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result.update(classification='PREFIX_BUILD_OPERATIONAL_FAILURE_RETAINED', failure=str(error))
    result['payload_sha256'] = {str(p): C.sha(p) for p in WORK.iterdir() if p.is_file()}
    save()
    print(json.dumps({k: result.get(k) for k in ('complete', 'all_pass', 'classification', 'failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

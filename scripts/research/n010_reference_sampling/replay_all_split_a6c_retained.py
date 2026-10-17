#!/usr/bin/env python3
"""Plan088: exact original analysis, one missing metadata field, no native retry."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import diagnose_selected_bounce_paths as D
from run_primary_direction_sequence import require_no_other_research_worker

OUTPUT = D.RESULTS / '237-posthoc-original-a6c-retained-control.json'
PLAN = D.RESULTS.parent / 'experiments/088-retained-a6c-analysis-repair.md'


def main():
    if OUTPUT.exists():
        raise ValueError('refuse existing retained A6c analysis')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)
    for p in (Path(__file__).resolve(), PLAN, Path(D.__file__),
              D.HERE / 'run_primary_direction_sequence.py'):
        D.checked(p)
    failed = json.loads(D.checked(D.RESULTS / '234-all-split-original-a6c-full-physical-control.json'))
    if (failed['complete'] or failed['all_pass'] or failed['returncode'] != 0
            or failed['classification'] != 'ORIGINAL_FULL_A6C_FAILURE_PARTIALS_RETAINED'
            or failed['failure'] != "'run_counters'"):
        raise ValueError('exact terminal native-success metadata failure required')
    for p, digest in failed['input_sha256'].items():
        D.checked(Path(p), digest)
    for p, digest in failed['payload_sha256'].items():
        D.checked(Path(p), digest)
    work = D.OUT / 'all-split-original-a6c-full-v1'
    receipt = json.loads(D.checked(work / 'native.resources.json'))
    stat = Path('/proc') / str(receipt['pid']) / 'stat'
    if stat.exists():
        fields = stat.read_text().rsplit(')', 1)[1].split()
        if int(fields[19]) == receipt['start_ticks'] and fields[0] != 'Z':
            raise ValueError('same native remains live; do not relabel')
    if (receipt['cpu'] != [3600] * 2 or receipt['address_space'] != [4 * 1024**3] * 2
            or len(receipt['affinity']) != 1 or receipt['nice'] != 15):
        raise ValueError('retained native resources differ')
    stdout = D.checked(work / 'native.stdout').decode()
    if json.loads(stdout) != json.loads(D.checked(work / 'A6c.meta.json')):
        raise ValueError('metadata differs from native stdout')
    parent = D.HERE / 'validate_all_split_a6c_full.py'
    source = D.checked(parent).decode()
    start = source.index('        fresh=json.loads(proc.stdout);')
    end = source.index('        for p,h in list(D.INPUTS.items()):D.checked(Path(p),h)', start)
    analysis = source[start:end]
    old = "m.update(name='A6c',geometry_hash_match=True);"
    new = ("m.update(name='A6c',geometry_hash_match=True,run_counters="
           "[{k:r[k]for k in ('seed','primary_hits','shadow_tests','shadow_blocked',"
           "'backface_absorbed')}for r in fresh['runs']]);")
    if analysis.count(old) != 1:
        raise ValueError('metadata insertion anchor differs')
    repaired = analysis.replace(old, new)
    if repaired.replace(new, old) != analysis:
        raise ValueError('analysis inverse differs')
    # Original source wrote a derived metadata file. Its existing exact bytes
    # must remain fixed; intercept that one operation with an equality check.
    class RetainedWork:
        def __truediv__(self, name):
            if name != 'A6c.meta.json':
                raise ValueError('unexpected original analysis output')
            class ExistingMetadata:
                def write_text(self, text):
                    if text.encode() != (work / name).read_bytes():
                        raise ValueError('derived native metadata bytes differ')
                    return len(text)
            return ExistingMetadata()
    sys.path.insert(0, str(D.HERE.parent / 'n010_comparison_readiness'))
    import validate_sampler as V
    for p in (Path(V.__file__), Path(V.P.__file__), Path(V.L.__file__)):
        D.checked(p)
    original = D.OUT / 'sampler-validation-v1/rqmc'
    meta = json.loads(D.checked(original / 'A6c.meta.json'))
    env = dict(json=json, np=np, V=V, D=D, Path=Path, proc=SimpleNamespace(stdout=stdout),
               WORK=RetainedWork(), prefix=work / 'A6c', original=original,
               scene=original / 'A6c.n008', meta=meta)
    result = dict(schema='n010-posthoc-original-a6c-retained-control/1', complete=False,
                  all_pass=False, gpu_run=False, native_reexecuted=False, reference_admission=False,
                  classification='POSTHOC_SAME_A6C_ANALYSIS', input_sha256=D.INPUTS,
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  native_returncode=failed['returncode'], native_elapsed_seconds=failed['elapsed'],
                  native_cpu_seconds=failed['child_cpu_seconds'], native_pid_start_confirmed_terminal=True,
                  analysis_inverse_exact=True,
                  original_analysis_sha256=hashlib.sha256(analysis.encode()).hexdigest(),
                  repaired_analysis_sha256=hashlib.sha256(repaired.encode()).hexdigest(),
                  analysis_receipt=dict(pid=os.getpid(),
                      start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]),
                      affinity=sorted(os.sched_getaffinity(0)), nice=os.getpriority(os.PRIO_PROCESS, 0),
                      cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),
                      address_space=list(resource.getrlimit(resource.RLIMIT_AS))),
                  tests='NOT_RUN; post-hoc same full native acquisition analytic replay')
    try:
        # Keep original indentation intact: execute as the body of one block.
        exec(compile('if True:\n' + repaired, str(parent) + '#plan088-analysis-only', 'exec'), env)
        physical = env['physical']
        for p, digest in list(D.INPUTS.items()):
            D.checked(Path(p), digest)
        result.update(complete=True, all_pass=bool(physical['pass']),
                      classification='POSTHOC_SAME_A6C_FULL_ANALYTIC_COMPLETE_NO_ADMISSION',
                      physical_checks=physical, deterministic_component_bits_primary_exact=True,
                      native_metadata=env['fresh'],
                      scope='Same234 original full A6c only; 11of17 if PASS, other physical/bias/state/prefix/reference gates remain')
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result.update(classification='POSTHOC_A6C_ANALYSIS_FAILURE_RETAINED', failure=str(error))
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result.get(k) for k in ('complete', 'all_pass', 'classification', 'failure',
                                              'native_elapsed_seconds', 'native_cpu_seconds')}, indent=2))
    raise SystemExit(0 if result['all_pass'] else 2)


if __name__ == '__main__':
    main()

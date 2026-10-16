#!/usr/bin/env python3
"""Plan 050: fresh two-level acquisition after zero-export interruption 171."""
import sys
from pathlib import Path

from primary_direction_recovery_programs import (
    HERE, RESULTS, ROOT, identities, require_paths, feasibility_program, sha, once,
)

sys.path.insert(0, str(HERE.parent/'n010_comparison_readiness'))
from reference_provenance import read
from qualify_hybrid_references import check_files
from run_primary_direction_sequence import require_no_other_research_worker

CONTINUATION_PLAN = RESULTS.parent/'experiments/050-prospective-zero-export-feasibility-recovery.md'
STOP = RESULTS/'171-user-requested-recovered-feasibility-stop.json'
PARTIAL = RESULTS/'165-primary-direction-recovered-bounded-feasibility.json'
OLD_WORK = ROOT/'out/research/n010-comparison-readiness/primary-direction-feasibility-recovery-v1'


def validate_interruption(inputs):
    if (sha(STOP)!='88263401c0cc473b65b881821676bf4f70cd574ab61b991aaf31608d6b68e5e7'
        or sha(PARTIAL)!='7f68e982e64d4203040550ab73e73f504edaf08642a86529a5c6f2be0f8d2c2f'):
        raise ValueError('immutable user-stop or partial identity changed')
    stop, partial = read(STOP, inputs), read(PARTIAL, inputs)
    receipt = read(ROOT/stop['source_receipt']['path'], inputs)
    if (not stop['complete'] or stop['classification']!='USER_STOPPED_BEFORE_FIRST_COMPLETE_FEASIBILITY_LEVEL'
        or stop['completed_levels'] or stop['exported_seed_count']
        or stop['numerical_verdict']!='INCOMPLETE_NOT_ASSIGNED'
        or stop['scientific_cap_failure'] or stop['reference_admission']
        or partial['complete'] or partial['all_pass'] or partial['levels']
        or receipt!=stop['source_receipt']['record'] or not receipt['stopped']
        or receipt['remaining_live_research_workers']
        or sha(ROOT/stop['source_receipt']['path'])!=stop['source_receipt']['sha256']):
        raise ValueError('zero-export interruption scope differs')
    actual = {str(p.relative_to(ROOT)) for p in OLD_WORK.rglob('*') if p.is_file()}
    if len(actual)!=3 or actual!=set(stop['partial_files_sha256']):
        raise ValueError('stopped work file set changed')
    check_files({str(ROOT/p):h for p,h in stop['partial_files_sha256'].items()}, inputs)
    check_files(partial['input_sha256'], inputs)
    inputs[str(CONTINUATION_PLAN)] = sha(CONTINUATION_PLAN)


def program():
    original, source = feasibility_program()
    previous = source
    edits = []

    def change(before, after):
        nonlocal source
        source = once(source, before, after)
        edits.append((before, after))

    change('primary-direction-feasibility-recovery-v1', 'primary-direction-feasibility-recovery-v2')
    change('165-primary-direction-recovered-bounded-feasibility.json',
           '172-primary-direction-post-stop-bounded-feasibility.json')
    change('def prerequisites(inputs):\n',
           'def prerequisites(inputs):\n    _validate_interruption(inputs)\n')
    change('    def save():\n',
           "    result['operational_recovery'] = {'plan':'050', 'stopped_result_sha256':sha(_stopped_result),\n"
           "        'partial_samples_imported':False, 'source_inverse_proof':True}\n    def save():\n")
    restored = source
    for before, after in reversed(edits):
        restored = once(restored, after, before)
    if restored!=previous:
        raise ValueError('unexpected feasibility change outside plan-050 dispatch/provenance')
    return original, source


original, source = program()
_program_inputs = identities(__file__, original)
for path, digest in (
    (HERE/'acquire_recovered_primary_direction_feasibility.py',
     'ffb879ebb5aecfb0778b847f7ccdb0ded92953056d937ff4288844bdb0455ba9'),
    (HERE/'primary_direction_recovery_programs.py',
     'ef573b5d7b45746425ff11151b1464c5af2ea804f1e7b1b3587356aa79a2ea21'),
):
    if sha(path)!=digest:
        raise ValueError('retained plan-047 program changed')
    _program_inputs[str(path)] = digest
_program_inputs[str(CONTINUATION_PLAN)] = sha(CONTINUATION_PLAN)
_require_quiet = require_no_other_research_worker
_require_paths = require_paths
_validate_interruption = validate_interruption
_stopped_result = PARTIAL
exec(compile(source, str(original)+'#plan050-zero-export-recovery', 'exec'), globals())

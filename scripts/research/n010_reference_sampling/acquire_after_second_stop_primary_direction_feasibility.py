#!/usr/bin/env python3
"""Plan 053: unchanged bounded feasibility at a fresh path after stop 176."""
from pathlib import Path
import hashlib

from primary_direction_recovery_programs import (
    HERE, ROOT, RESULTS, identities, require_paths, sha, once,
)
import acquire_post_stop_primary_direction_feasibility as Previous
from reference_provenance import read
from qualify_hybrid_references import check_files
from run_primary_direction_sequence import require_no_other_research_worker

CONTINUATION_PLAN = RESULTS.parent/'experiments/053-prospective-feasibility-after-second-zero-export-stop.md'
STOP = RESULTS/'176-user-requested-post-stop-feasibility-stop.json'
PARTIAL = RESULTS/'172-primary-direction-post-stop-bounded-feasibility.json'
OLD_WORK = ROOT/'out/research/n010-comparison-readiness/primary-direction-feasibility-recovery-v2'
PREVIOUS_SHA = '71d4b88c4619334069fcf0a503252788ee7cde468ae0adb0a67d6bc1bd7d8385'


def validate_interruption(inputs):
    # Preserve/recheck the earlier interruption as well; no samples are imported.
    Previous.validate_interruption(inputs)
    if (sha(STOP)!='cd0287f7fb5c2c4947ad42ec833c68f9b3f892518085fee11bb54520744fbbd4'
        or sha(PARTIAL)!='f5d50696c8e85f36ea6a3c5ab13f967248c06a2b647cb31c84db127e757c42cb'):
        raise ValueError('immutable second user-stop/partial identity changed')
    stopped, partial = read(STOP,inputs), read(PARTIAL,inputs)
    source = stopped['source_receipt']
    receipt_path = ROOT/source['path']
    receipt = read(receipt_path,inputs)
    if (not stopped['complete'] or stopped['classification']!='USER_STOPPED_BEFORE_FIRST_COMPLETE_FEASIBILITY_LEVEL'
        or stopped['completed_levels'] or stopped['exported_seed_count']
        or stopped['numerical_verdict']!='INCOMPLETE_NOT_ASSIGNED'
        or stopped['scientific_cap_failure'] or stopped['reference_admission']
        or partial['complete'] or partial['all_pass'] or partial['levels']
        or receipt!=source['record'] or sha(receipt_path)!=source['sha256']
        or not receipt['all_targets_exited'] or not all(
            a['pidfd_exit_observed'] and a['proc'] is None for a in receipt['after'])
        or len(receipt['post_stop_research_process_scans'])!=2
        or any(s['remaining_research_processes'] for s in receipt['post_stop_research_process_scans'])):
        raise ValueError('second zero-export interruption scope differs')
    expected = {}
    for f in receipt['preserved_files']:
        path = ROOT/f['path']
        if path.stat().st_size!=f['size'] or sha(path)!=f['sha256']:
            raise ValueError('second stopped partial bytes changed')
        expected[str(path)] = f['sha256']
    actual = {str(p) for p in OLD_WORK.rglob('*') if p.is_file()}
    if len(actual)!=3 or actual!={p for p in expected if p.startswith(str(OLD_WORK)+'/')}:
        raise ValueError('stopped v2 work file set changed')
    check_files(expected,inputs)
    check_files(partial['input_sha256'],inputs)
    # A quiet-process check runs in the original main before this prerequisite.
    # Require the completed restoration record, irrespective of timing PASS/FAIL.
    gpu = read(RESULTS/'178-hidden-ide-bulk-pfm-calibration-full-renderer.json',inputs)
    policy_path = ROOT/'out/research/n010-comparison-readiness/hidden-ide-bulk-pfm-accepted-v1/visibility-policy.json'
    policy = read(policy_path,inputs)
    if (policy!=gpu.get('visibility_policy') or not policy.get('complete')
        or not policy.get('restoration_verified') or policy.get('restoration_failure')
        or sha(policy_path)!=gpu.get('visibility_policy_sha256')):
        raise ValueError('GPU acquisition/restoration is not terminal and verified')
    check_files(gpu['fixture_input_sha256'],inputs)
    inputs[str(CONTINUATION_PLAN)] = sha(CONTINUATION_PLAN)


def program():
    if sha(Path(Previous.__file__))!=PREVIOUS_SHA:
        raise ValueError('frozen previous feasibility entry changed')
    original, source = Previous.program()
    parent = source
    edits = []
    def change(old,new):
        nonlocal source
        source = once(source,old,new)
        edits.append((old,new))
    change('primary-direction-feasibility-recovery-v2','primary-direction-feasibility-recovery-v3')
    change('172-primary-direction-post-stop-bounded-feasibility.json',
           '180-primary-direction-second-stop-bounded-feasibility.json')
    change("    result['operational_recovery'] = {'plan':'050', 'stopped_result_sha256':sha(_stopped_result),\n"
           "        'partial_samples_imported':False, 'source_inverse_proof':True}\n",
           "    result['operational_recovery'] = {'plan':'053', 'stopped_result_sha256':sha(_stopped_result),\n"
           "        'partial_samples_imported':False, 'source_inverse_proof':True,\n"
           "        'whole_parent_program_inverse':_recovery_inverse}\n")
    restored = source
    for old,new in reversed(edits):
        restored = once(restored,new,old)
    if restored!=parent:
        raise ValueError('whole previous generated feasibility program inverse differs')
    inverse = {'exact':True,
        'parent_generated_source_sha256':hashlib.sha256(parent.encode()).hexdigest(),
        'restored_generated_source_sha256':hashlib.sha256(restored.encode()).hexdigest(),
        'generated_source_sha256':hashlib.sha256(source.encode()).hexdigest()}
    return original,source,inverse


original,source,_recovery_inverse = program()
_program_inputs = identities(__file__,original)
for path in (Path(Previous.__file__).resolve(),Previous.CONTINUATION_PLAN,
             HERE/'acquire_recovered_primary_direction_feasibility.py',CONTINUATION_PLAN):
    _program_inputs[str(path)] = sha(path)
_require_quiet = require_no_other_research_worker
_require_paths = require_paths
_validate_interruption = validate_interruption
_stopped_result = PARTIAL
exec(compile(source,str(original)+'#plan053-fresh-after-second-stop','exec'),globals())

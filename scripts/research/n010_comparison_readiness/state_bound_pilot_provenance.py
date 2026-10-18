"""Plan160: full36 intake with unchanged PT and state-bound non-PT proofs."""
import hashlib
from pathlib import Path

import selected_reportable_pilot_provenance as T
import non_pt_state_bound_case as W
from selected_reportable_pilot_provenance import C, P, R, SCOPE, LOCK

PIN = 'e1c6be0c7c5d84c881e8a5944b0fb8f4103e68dc5d36b5014584bc40227d0ebd'
WRAPPER_PIN = '3e638838b3dd66163cf1d48d75a319c359df4aaa027a008d98fc67f4888cfda6'
PLAN = R.RESULTS.parent/'experiments/160-state-bound-full-selected-intake.md'


def bind_inventory(rows):
    for row in rows:
        if row['kind'] != 'raw-non-pt':continue
        if row['id'] == 'static-C7-hwrt':
            row.update(posthoc_reuse=True,prior_posthoc_replay=str(W.OUTPUT))
        if row['id'] != 'static-C7-dense-rc':
            path = Path(row['path'])
            if path.exists():
                record = C.read(path)
                command = record['command']
                native = Path(command[command.index('--out')+1]).parent/'native-record.json'
                row['immutable_native_path'] = str(native)
                row['record_present'] = row['record_present'] and native.is_file()
    return rows


def non_pt(row, references, work):
    R.checked(Path(W.__file__).resolve(),WRAPPER_PIN)
    R.checked(W.PLAN)
    composition = W.install()
    path = Path(row['path'])
    record = C.read(path)
    C.require(record['complete'] and record['native_returncode'] == 0,
        'actual terminal non-PT native required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in record[group].items():R.checked(name,digest)
    if row['posthoc_reuse']:
        prior = C.read(Path(row['prior_posthoc_replay']))
        flag = 'original507_failure_unchanged' if row['id'] == 'static-C7-dense-rc' else 'original516_failure_unchanged'
        C.require(row['id'] in ('static-C7-dense-rc','static-C7-hwrt')
            and prior['complete'] and prior['posthoc'] and not prior['native_executed']
            and prior['source_capture'] == str(path) and prior[flag], 'explicit post-hoc reuse identity differs')
        for group in ('input_sha256','payload_sha256'):
            for name,digest in prior[group].items():R.checked(name,digest)
        if row['id'] == 'static-C7-hwrt':
            C.require(record['classification'] == 'NON_PT_RAW_PILOT_FAILURE_PARTIALS_RETAINED'
                and record['failure'] == 'continuation quality proof: RC state differs beyond registered frame-counter progression'
                and prior['composition'] == composition, 'exact original516/post-hoc616 correction differs')
    if row['id'] == 'static-C7-dense-rc':native = path
    else:
        native = Path(row['immutable_native_path'])
        snapshot = C.read(native)
        C.require(snapshot['classification'] == 'FULL_NON_PT_NATIVE_TERMINAL_ANALYSIS_PENDING'
            and snapshot['complete'] and snapshot['native_returncode'] == 0,
            'original immutable terminal native snapshot required')
        keys = ('command','boundary_id','source_commit','native_pid','environment','environment_switches',
                'native_returncode','elapsed_seconds','child_cpu_seconds','payload_sha256')
        C.require(all(snapshot[key] == record[key] for key in keys), 'final/native snapshot identity differs')
        if row['id'] == 'static-C7-hwrt':
            C.require(prior['immutable_native_record'] == str(native), '616 native snapshot differs')
        else:C.require(record['classification'] == 'FULL_NON_PT_RAW_EXECUTION_VALID_QUALITY_REPLAY_PENDING',
            'unexpected failed or rewritten capture record')
    proof = W.N.verify_capture(native,row['id'],references=references,score_work=work,
        reference_verifier=T.H.verify_reference)
    proof.update(state_counter_composition=composition,source_capture=str(path),native_record=str(native),
        explicit_posthoc_replay=row.get('prior_posthoc_replay'))
    return proof


def program():
    original = R.checked(Path(T.__file__).resolve(),PIN).decode()
    source,edits = original,[]
    old = 'def inventory():\n'
    new = 'def _original_inventory():\n'
    C.require(source.count(old) == 1, 'unique inventory anchor required')
    source = source.replace(old,new,1);edits.append((old,new))
    begin = source.index('            if row[\'posthoc_reuse\']:\n')
    end = source.index("        C.require(proof['execution_evidence_valid']",begin)
    old = source[begin:end]
    new = "            proof = _non_pt(row,references,work/row['id'])\n"
    C.require(source.count(old) == 1 and new not in source, 'unique non-PT branch required')
    source = source.replace(old,new,1);edits.append((old,new))
    restored = source
    for old,new in reversed(edits):
        C.require(restored.count(new) == 1, 'unique full160 inverse anchor required')
        restored = restored.replace(new,old,1)
    C.require(restored == original, 'whole original154 selected intake inverse differs')
    namespace = dict(__file__=T.__file__,__name__='n010_state_bound_selected_intake',_non_pt=non_pt)
    exec(compile(source,'<n010-state-bound-selected-intake>','exec'),namespace)
    namespace['inventory'] = lambda:bind_inventory(namespace['_original_inventory']())
    proof = dict(whole_selected_source_inverse_exact=True,original_selected_sha256=PIN,
        generated_selected_sha256=hashlib.sha256(source.encode()).hexdigest(),
        unchanged_pt_branch_and_final_checks=True,substitutions=[dict(old=a,new=b) for a,b in edits],
        raw_state_composition=W.install(),immutable_native_snapshot_binding=True,
        all_split_reference_dispatch_implemented=False)
    return namespace,proof


def composition():return program()[1]
def inventory():return program()[0]['inventory']()
def verify(lock_path,references,work,inputs):return program()[0]['verify'](lock_path,references,work,inputs)

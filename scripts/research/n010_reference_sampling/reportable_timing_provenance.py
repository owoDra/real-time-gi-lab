"""Plan121: replay valid descriptive pilots without admitting speed claims.

No acquisition occurs here. Preserve the original full-payload verifier and
separate its numerical precision checks from the evidence-integrity checks.
Only fresh, prospectively registered386/388 evidence is eligible for intake.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess

import deferred_image_timing_provenance as D

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT / 'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent / 'experiments/121-reportable-timing-proof-integration.md'
PILOT = RESULTS / '386-reportable-full-renderer-timing-pilot.json'
SIZING = RESULTS / '388-reportable-full-renderer-timing-sizing.json'
PARENT_SHA = '92d42379bd46dfdc365d2a930ef8190a02c9ccb753dd9150e7c1aeef76bfed0e'
AMENDMENT_SHA = 'a1af3c5dac557edfd816ca423758002383c6538287350f146f05d30e440c7633'
MAX_CPU_SECONDS = 120
MAX_ELAPSED_SECONDS = 180


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError('reportable timing proof: ' + message)


def verifier_program():
    """Return an invertible overlay; never read or execute native evidence."""
    require(sha(D.__file__) == PARENT_SHA, 'pinned parent verifier changed')
    original, parent_inverse = D.verifier_program()
    source, edits = original, []

    def change(before, after):
        nonlocal source
        count = source.count(before)
        require(count > 0 and after not in source, 'nonunique/missing overlay: ' + before[:80])
        source = source.replace(before, after)
        edits.append((before, after, count))

    # New immutable results/work paths. Historical185 and absent186 are not
    # reinterpreted. Build184 and the complete sixteen-boundary scope stay.
    change('185-deferred-image-calibration-sizing.json', SIZING.name)
    change('186-deferred-image-calibration-full-renderer.json', PILOT.name)
    change('deferred-image-calibration-sizing-v1', 'reportable-renderer-timing-sizing-v1')
    change('deferred-image-calibration-accepted-v1', 'reportable-renderer-timing-pilot-v1')
    change("all(d['complete'] and d['all_pass'] for d in (build, sizing, accepted))",
           "build['complete'] and build['all_pass'] and sizing['complete'] and sizing['all_pass'] and accepted['complete']")
    # One fresh process is a bounded execution pilot, never an independent
    # replicate interval or demonstrated detection capability.
    change("len(arow['blocks'])==8, 'eight fresh-process blocks'",
           "len(arow['blocks'])==1, 'one fresh process per pilot boundary'")
    change("arow['analysis']==recalculated and recalculated['all_pass'], 'original numerical gates'",
           "arow['analysis']==recalculated, 'retained numerical annotations differ'")
    change("'blocks_per_boundary':8", "'blocks_per_boundary':1")
    change("'scope':'Actual complete isolated-fixture calibration; no historical timing transfer'",
           "'scope':'Actual complete descriptive timing pilot; no precision or speed admission'")
    change("proof['schema']=='n010-deferred-image-renderer-calibration/1'",
           "proof['schema']==('n010-deferred-image-renderer-calibration/1' if mode=='sizing' else 'n010-reportable-renderer-timing-pilot/1')")
    # Check individual native resources and finite raw timestamps after all
    # raw-payload/image/scratch/ledger checks, before recalculating annotations.
    change("        recalculated = C.analysis(arow['blocks'])",
           "        _verify_native_and_timestamps(accepted, arow, boundary, inputs)\n"
           "        recalculated = C.analysis(arow['blocks'])")
    restored = source
    for before, after, count in reversed(edits):
        require(restored.count(after) == count, 'inverse edit count differs')
        restored = restored.replace(after, before)
    require(restored == original, 'whole parent verifier inverse differs')
    return source, dict(parent=parent_inverse, whole_parent_inverse_exact=True,
                        parent_source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                        edits=[dict(before=a, after=b, count=c) for a, b, c in edits])


def verify_registration(data, inputs):
    """Require the actual acquisition commit to contain these exact sources."""
    require(data.get('schema') == 'n010-reportable-renderer-timing-pilot/1', 'fresh pilot schema required')
    require(data.get('accepted_timing') is False and data.get('diagnostic_only') is True,
            'pilot must disclaim accepted performance timing')
    commit = data['source_commit']
    require(isinstance(commit, str) and len(commit) == 40
            and all(c in '0123456789abcdef' for c in commit), 'full source commit required')
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'],
                   cwd=ROOT, check=True, capture_output=True)
    amendment = PLAN.with_name('120-reportable-comparison-readiness-amendment.md')
    require(sha(amendment) == AMENDMENT_SHA, 'handoff amendment changed')
    for path in (PLAN, amendment, Path(__file__).resolve(),
                 HERE / 'readiness_preflight_reportable_timing.py'):
        raw = subprocess.check_output(['git', 'show', commit + ':' + str(path.relative_to(ROOT))], cwd=ROOT)
        digest = sha(path)
        require(hashlib.sha256(raw).hexdigest() == digest, 'source/registration not frozen at acquisition')
        require(data['fixture_input_sha256'].get(str(path)) == digest, 'mandatory pilot source omitted')
        inputs[str(path)] = digest


def verify_native_and_timestamps(proof, row, boundary, inputs):
    block = row['blocks'][0]
    identities = proof['native_resources']
    expected_ids = [r['boundary']['id'] for r in proof['rows']]
    require(len(expected_ids) == len(set(expected_ids)) == 16
            and len(identities) == 16 and {r['boundary_id'] for r in identities} == set(expected_ids),
            'all sixteen original native receipts required')
    selected = next(r for r in identities if r['boundary_id'] == boundary['id'])
    path = Path(selected['receipt_path'])
    receipt = json.loads(path.read_bytes())
    inputs[str(path)] = sha(path)
    require(inputs[str(path)] == selected['receipt_sha256'] and selected['returncode'] == 0,
            'native receipt changed or failed')
    require(receipt['command'] == block['command']
            and isinstance(receipt['boot_id'], str) and bool(receipt['boot_id'])
            and receipt['boot_id'] == proof['execution_environment']['boot_id']
            and type(receipt['pid']) is int and receipt['pid'] > 0
            and type(receipt['start_ticks']) is int and receipt['start_ticks'] > 0,
            'native command or boot/PID/start identity differs')
    require(receipt['affinity'] == [31] and receipt['nice'] == 15
            and receipt['cpu'] == [MAX_CPU_SECONDS] * 2
            and receipt['elapsed_limit_seconds'] == MAX_ELAPSED_SECONDS,
            'actual registered native resource limits differ')
    for sample in block['samples']:
        require(type(sample['gpu_us']) in (float, int) and math.isfinite(sample['gpu_us'])
                and sample['gpu_us'] > 0 and type(sample['known_work_gpu_us']) in (float, int)
                and math.isfinite(sample['known_work_gpu_us']) and sample['known_work_gpu_us'] >= 0,
                'invalid raw GPU timestamp; no filtering')
    live, peak = {}, 0
    for event in block['allocation_ledger']['events']:
        key = (event['device_context'], event['allocation_id'])
        require(type(event['bytes']) is int and event['bytes'] > 0
                and type(event['live_bytes']) is int and event['live_bytes'] >= 0,
                'invalid owned-allocation byte count')
        if event['action'] == 'allocate':
            require(key not in live, 'duplicate owned allocation')
            live[key] = event['bytes']
        elif event['action'] == 'free':
            require(key in live and live[key] == event['bytes'], 'unknown/incorrect owned free')
            del live[key]
        else:
            raise ValueError('reportable timing proof: unknown allocation event')
        current = sum(live.values())
        require(current == event['live_bytes'], 'owned live sum differs')
        peak = max(peak, current)
    ledger = block['allocation_ledger']
    require(not live and ledger['teardown_zero'] is True
            and type(ledger['true_peak_owned_bytes']) is int
            and peak == ledger['true_peak_owned_bytes'] <= 8 * 1024**3,
            'owned-memory true peak/cap/teardown differs')


def _verify_timing_pilot(lock_path, inputs):
    raw = PILOT.read_bytes()
    pilot_digest = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    verify_registration(data, inputs)
    require(len(data['rows']) == 16 and len(data['native_resources']) == 16,
            'partial corpus timing pilot')
    # Boot/PID/start uniqueness is evidence identity, not an independence claim.
    identities = []
    for native in data['native_resources']:
        receipt = json.loads(Path(native['receipt_path']).read_bytes())
        identities.append((receipt['boot_id'], receipt['pid'], receipt['start_ticks']))
    require(len(set(identities)) == 16, 'reused native identity')
    source, inverse = verifier_program()
    scope = dict(__name__='n010_reportable_timing_intake', __file__=str(D.ORIGINAL),
                 _verify_plan=D.verify_plan, _verify_spool=D.verify_spool,
                 _verify_native_and_timestamps=verify_native_and_timestamps)
    exec(compile(source, str(D.ORIGINAL) + '#plan121', 'exec'), scope)
    result = scope['verify_calibration'](lock_path, inputs)
    require(sha(PILOT) == pilot_digest, 'pilot changed during evidence intake')
    require(data['all_pass'] == all(r['analysis']['all_pass'] for r in data['rows']),
            'saved numerical summary inconsistent')
    result.update(evidence_valid=True, timing_classification='TIMING_INCONCLUSIVE',
                  accepted_timing=False, precision_demonstrated=False,
                  all_samples_retained=True, proof_inverse=inverse,
                  limitation='One process per boundary proves execution, not timing precision. '
                      'Fixed PT1024/static/reset-target pilot scope does not qualify other '
                      'quality budgets or history-dependent frame timing.')
    for path in (Path(__file__).resolve(), Path(D.__file__).resolve(), PLAN):
        inputs[str(path)] = sha(path)
    return result


def verify_timing_pilot(lock_path, inputs):
    """Normalize malformed/missing proof to the original fail-closed gate API."""
    try:
        return _verify_timing_pilot(lock_path, inputs)
    except (subprocess.CalledProcessError, OverflowError, TypeError, IndexError) as error:
        raise ValueError('reportable timing evidence invalid: ' + str(error)) from error

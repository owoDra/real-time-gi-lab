#!/usr/bin/env python3
"""Plan118: post-hoc raw-timing arithmetic replay, never proof admission."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import ranked_timing_decision as D
import ranked_timing_observations as O
import timing_uncertainty_orderstats as U

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / 'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent / 'experiments/118-posthoc-ranked-c7-raw-timing-replay.md'
OUTPUT = RESULTS / '378-posthoc-ranked-c7-raw-timing-replay.json'
INPUTS = {}


def checked(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('retained identity differs: ' + str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed during replay: ' + str(path))
    INPUTS[str(path)] = digest
    return raw


def main():
    if OUTPUT.exists():
        raise ValueError('refuse overwriting retained post-hoc replay')
    # Only small archived JSON/timing/schedule files are read. No image or
    # native executable is loaded, and no physical/GPU acquisition is launched.
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    if os.getpriority(os.PRIO_PROCESS, 0) != 15:
        raise ValueError('replay requires actual nice15')
    resource.setrlimit(resource.RLIMIT_AS, (1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    started, cpu_started = time.monotonic(), time.process_time()
    for path in (Path(__file__), PLAN, Path(O.__file__), Path(U.__file__), U.BASE):
        checked(path)
    checked(Path(D.__file__), 'ae1b5e4510bb70afe6a9414ce597efc026c0bacfdd1ac9543aad7c9cdc6bf572')
    data = json.loads(checked(RESULTS / '255-orderstat-uncertainty-c7-calibration-diagnostic.json',
                             'e71e9f9c17852fc3399660c79dce370850f7b4e0a90ea3ecab37f921b1cd864d'))
    checked(Path(U.__file__), data['fixture_input_sha256'][str(Path(U.__file__).resolve())])
    checked(RESULTS.parent / 'experiments/103-ranked-process-median-calibration.md',
            data['prospective_protocol_sha256'])
    baseline = json.loads(checked(RESULTS / '046-calibration-quiet-sizing.json',
                                 '2ab654662ffdef9b873179d95a9142eea7e18ad0635cec37601c51f0f828d36d'))
    if (not data['complete'] or not data['all_pass'] or not data['diagnostic_only']
            or data['accepted_timing'] or data['timing_method'] != 'plan103-v1'
            or data['observation_frames'] != 4 or len(data['rows']) != 1
            or data['rows'][0]['boundary']['id'] != 'C7-hwrt'):
        raise ValueError('original bounded diagnostic scope differs')
    family = [row['boundary']['id'] for row in baseline['rows']]
    if len(family) != 16:
        raise ValueError('original reserved family differs')
    frozen = D.design(family)
    row = data['rows'][0]
    if len(row['blocks']) != 24 or len(data['diagnostic_native_resources']) != 24:
        raise ValueError('all24 original repetitions required')
    records_by_process = []
    processes = []
    frames = 0
    for i, (block, native) in enumerate(zip(row['blocks'], data['diagnostic_native_resources'])):
        command = block['command']
        directory = Path(command[command.index('--out') + 1])
        if directory.name != f'block-{i}' or directory.parent.name != 'C7-hwrt':
            raise ValueError('retained block identity differs')
        receipt = json.loads(checked(native['receipt_path'], native['receipt_sha256']))
        if (receipt != native['actual'] or receipt['command'] != command
                or native['command'] != command or native['returncode'] != 0
                or block['returncode'] != 0 or receipt['cpu'] != [30, 30]
                or receipt['affinity'] != [31] or receipt['nice'] != 15):
            raise ValueError('actual retained native/resource identity differs')
        raw = [json.loads(line) for line in checked(directory / 'calibration-timings.jsonl',
                   block['payload_sha256']['calibration-timings.jsonl']).splitlines()]
        if raw != block['raw_frame_samples']:
            raise ValueError('embedded raw frames differ from actual timing file')
        dose = 1301
        records = U.schedule(dose, i)
        schedule_path = directory.parent / f'block-{i}.schedule.json'
        if json.loads(checked(schedule_path)) != records:
            raise ValueError('pre-native saved schedule differs')
        doses = checked(command[command.index('--calibration-doses') + 1],
                        block['doses_file_sha256']).decode()
        if doses != ''.join(str(r['dose']) + '\n' for r in records for _ in range(4)):
            raise ValueError('raw-frame dose expansion differs')
        # Per-native receipts lack boot_id; use the original acquisition-wide
        # before/after environment identity, explicitly reported in the output.
        identity = [data['execution_environment']['boot_id'], receipt['pid'], receipt['start_ticks']]
        process, observations = O.decode_process(raw, records, identity, 4)
        tagged = [dict(s, **{k: v for k, v in r.items() if k not in s})
                  for s, r in zip(observations, records)]
        if observations != block['samples'] or tagged != block['tagged_samples']:
            raise ValueError('raw-to-mean observation or tagged schedule differs')
        processes.append(process)
        records_by_process.append(dict(index=i, process_identity=identity,
                                       raw_frames=len(raw), observations=len(observations)))
        frames += len(raw)
    decision = D.decide(frozen, 'C7-hwrt', processes, purpose='calibration',
                        quality_status='UNKNOWN', evidence_verified=False,
                        nuisance_model_justified=False)
    old = row['analysis']
    comparisons = dict(
        all_process_paired_values_and_medians_exact=all(
            s['populations'] == retained
            for s, retained in zip(decision['process_summaries'], old['process_summaries'])),
        all_six_ranked_intervals_exact=(decision['log_median_intervals'] == old['log_median_intervals']),
        effect_ratio_interval_exact=(decision['effect_ratio_interval'] == old['effect_ratio_interval']),
        all_four_calibration_checks_exact=(decision['numerical_checks'] == old['checks']),
        family_noncoverage_bound_exact=(frozen['family_noncoverage_bound'] == old['family_noncoverage_bound']))
    for path, digest in list(INPUTS.items()):
        checked(path, digest)
    replay_pass = all(comparisons.values())
    result = dict(schema='n010-posthoc-ranked-c7-timing-replay/1', complete=True,
        numerical_replay_pass=replay_pass, all_pass=False, diagnostic_only=True,
        accepted_timing=False, proof_admission=False, gpu_run=False,
        new_native_acquisitions=0, classification=(
            'POSTHOC_RAW_TIMING_NUMERICAL_REPLAY_CONSISTENT_NO_ADMISSION' if replay_pass else
            'POSTHOC_RAW_TIMING_NUMERICAL_REPLAY_MISMATCH_NO_ADMISSION'),
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        input_sha256=INPUTS, raw_frames=frames, observations=frames // 4,
        retained_processes=records_by_process, comparisons=comparisons, decision=decision,
        source_boot_identity='Original255 acquisition-wide before/after environment record; '
            'individual resource receipts contain PID/start, not individual boot IDs. '
            'No comparison to the current boot or performance pooling is made.',
        not_verified=['Images and scratch payloads', 'Build/binary/shader source proof',
            'Owned memory ledger replay', 'Actual selected GI boundaries/quality/dynamic parity',
            'Conditional nuisance-model justification', 'Full proof intake/final readiness'],
        tests='NOT_RUN; bounded post-hoc archived timing arithmetic replay, not regression tests',
        analysis_resources=dict(affinity=sorted(os.sched_getaffinity(0)), nice=15,
            cpu_limit_seconds=20, address_space_limit_bytes=1024**3,
            cpu_seconds=time.process_time() - cpu_started, elapsed_seconds=time.monotonic() - started))
    with OUTPUT.open('x') as out:
        out.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['classification'], flush=True)
    return 0 if replay_pass else 2


if __name__ == '__main__':
    try:
        status = main()
    except (OSError, ValueError, KeyError, StopIteration, OverflowError) as error:
        if not OUTPUT.exists():
            with OUTPUT.open('x') as out:
                out.write(json.dumps(dict(schema='n010-posthoc-ranked-c7-timing-replay/1',
                    complete=False, numerical_replay_pass=False, all_pass=False,
                    diagnostic_only=True, accepted_timing=False, proof_admission=False,
                    gpu_run=False, new_native_acquisitions=0,
                    classification='POSTHOC_RAW_TIMING_REPLAY_FAILURE_RETAINED_NO_ADMISSION',
                    input_sha256=INPUTS, error=str(error)), indent=2, allow_nan=False) + '\n')
        raise
    raise SystemExit(status)

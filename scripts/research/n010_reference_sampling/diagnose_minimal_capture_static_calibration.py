#!/usr/bin/env python3
"""CPU post-hoc replay/cadence diagnosis of all ten completed static boundaries."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
SCRIPTS = ROOT/'scripts/research/n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
import calibrate_renderer as C


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(values):
    values = sorted(values)
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('invalid diagnostic values')
    return {'count': len(values), 'minimum': values[0], 'maximum': values[-1],
        'median': statistics.median(values),
        'p10_nearest_rank': values[max(0, math.ceil(.1*len(values))-1)],
        'p90_nearest_rank': values[math.ceil(.9*len(values))-1]}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing diagnostic work/result')
    original = Path(C.__file__).resolve()
    if sha(original) != '64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d':
        raise ValueError('original schedule/analysis source changed')
    live_summary = RESULTS/'158-minimal-calibration-full-renderer.json'
    raw = live_summary.read_bytes()
    frozen = json.loads(raw)
    lock_path = RESULTS/'026-dynamic-execution-state-lock.json'
    lock = json.loads(lock_path.read_text())
    sizing_path = RESULTS/'157-minimal-calibration-quiet-sizing.json'
    sizing = json.loads(sizing_path.read_text())
    if (frozen['plan_sha256'] != sha(sizing_path) or not sizing['complete'] or not sizing['all_pass']
        or len(sizing['rows']) != 16 or sizing['lock_sha256'] != sha(lock_path)):
        raise ValueError('complete frozen sizing proof differs')
    doses = {r['boundary']['id']: r['frozen_dose'] for r in sizing['rows']}
    expected = {b['id']: b for b in C.boundaries(lock) if not b['dynamic']}
    rows = {r['boundary']['id']: r for r in frozen['rows'] if not r['boundary']['dynamic']}
    if (len(expected) != 10 or set(rows) != set(expected)
        or frozen['schema'] != 'n010-minimal-capture-renderer-calibration/1'
        or frozen['mode'] != 'accepted' or frozen['lock_sha256'] != sha(lock_path)):
        raise ValueError('fixed static boundary scope differs')
    for name, row in rows.items():
        if row['boundary'] != expected[name] or len(row['blocks']) != 8 or 'analysis' not in row:
            raise ValueError('required completed static boundary missing')
    a.work = a.work.resolve()
    a.work.mkdir(parents=True)
    snapshot = a.work/'158-exact-summary-snapshot.json'
    snapshot.write_bytes(raw)
    inputs = {str(p): sha(p) for p in (Path(__file__).resolve(), original, snapshot, lock_path, sizing_path)}
    prior_path = RESULTS/'155-stopped-calibration-posthoc-diagnosis.json'
    prior = json.loads(prior_path.read_text())
    inputs[str(prior_path)] = sha(prior_path)
    prior_rows = {r['boundary']: r for r in prior['rows']}
    capture_root = ROOT/'out/research/n010-comparison-readiness/minimal-calibration-accepted-v1'
    fixture = ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v2'
    for filename in ('minimal_capture.cpp', 'minimal_runtime.cpp', 'minimal_pt.cpp'):
        p = fixture/filename
        inputs[str(p)] = sha(p)
    result = {'schema': 'n010-minimal-static-calibration-posthoc-diagnosis/1',
        'complete': False, 'gpu_run': False, 'classification': 'POSTHOC_DIAGNOSTIC_ONLY',
        'utc': datetime.now(timezone.utc).isoformat(), 'input_sha256': inputs,
        'source_snapshot': {'original_path': str(live_summary), 'snapshot_path': str(snapshot),
            'sha256': sha(snapshot), 'full_acquisition_complete_at_snapshot': frozen['complete']},
        'scope': 'All ten original static boundaries, all eight blocks and all 64 samples per block. Churn is outside this post-hoc diagnostic, not excluded from calibration.',
        'rows': [], 'calibration_pass_claimed': False, 'thresholds_changed': False,
        'payload_content_hashes_independently_rechecked': False,
        'cadence_ratio_is_direct_gpu_duty_measurement': False}
    for name, row in rows.items():
        replay = C.analysis(row['blocks'])
        if replay != row['analysis']:
            raise ValueError('unchanged decision replay differs: '+name)
        blocks = []
        controls = []
        for index, block in enumerate(row['blocks']):
            samples = block['tagged_samples']
            schedule = C.schedule(doses[name], index)
            if (len(samples) != 64 or len(block['payloads']) != 64
                or any(any(s[k] != tag[k] for k in tag) for s, tag in zip(samples, schedule))
                or not block['images_byte_equal'] or not block['images_byte_equal_to_original_046']
                or not block['known_work_probe_validation'] or not block['allocation_ledger_replay_pass']):
                raise ValueError('retained schedule/image/scratch/ledger metadata differs')
            files = []
            for frame in range(64):
                directory = capture_root/name/f'block-{index}'/'frames'/str(frame)
                if (directory/'gpu').is_dir():
                    directory = directory/'gpu'
                files.append(directory/'total.pfm')
            mtimes = [p.stat().st_mtime_ns for p in files]
            gaps = [(b-c)/1000 for c, b in zip(mtimes, mtimes[1:])]
            if min(gaps) < 0:
                raise ValueError('retained file mtimes are not monotone')
            frame0 = files[0].parent
            output_bytes = {p.name: p.stat().st_size for p in frame0.iterdir() if p.is_file()}
            measured = [s for s in samples if not s['warmup']]
            control = [s['gpu_us'] for s in measured if s['kind'] == 'control']
            controls.extend(control)
            cadence = statistics.median(gaps)
            blocks.append({'block': index, 'sample_count_including_warmup': len(samples),
                'measured_control_gpu_us': describe(control),
                'renderer_call_wall_us_excluding_readback': describe([s['wall_us'] for s in measured]),
                'saved_total_file_mtimes_ns': mtimes,
                'saved_total_file_gap_us': describe(gaps),
                'median_all_frame_gpu_us': statistics.median(s['gpu_us'] for s in samples),
                'median_gpu_to_saved_file_cadence_ratio':
                    statistics.median(s['gpu_us'] for s in samples)/cadence if cadence else None,
                'frame0_saved_file_bytes': output_bytes,
                'unchanged_process_analysis': replay['processes'][index]})
        diag = {'boundary': name, 'decision_replay_matches': True,
            'original_all_pass': replay['all_pass'], 'original_gates': replay['gates'],
            'original_statistics': {k: v for k, v in replay.items() if k not in ('processes', 'gates', 'all_pass')},
            'all_measured_control_gpu_us': describe(controls), 'blocks': blocks}
        if name in prior_rows:
            old = prior_rows[name]
            diag['earlier_029_block0_diagnostic_comparison'] = {
                'old_saved_file_gap_median_us': 1000*old['retained_file_mtime_gap_ms']['median'],
                'new_saved_file_gap_median_us': blocks[0]['saved_total_file_gap_us']['median'],
                'old_three_stream_bytes_per_frame': sum(old['first_two_frames_stream_bytes'][0].values()),
                'new_all_frame0_file_bytes': sum(blocks[0]['frame0_saved_file_bytes'].values()),
                'controlled_causal_comparison': False,
                'scope': 'Different retained acquisitions; old three-stream size is a lower bound, new size is all saved frame files. File cadence is not measured GPU idle time.'}
        result['rows'].append(diag)
    result['complete'] = True
    result['decision_replay_all_match'] = all(r['decision_replay_matches'] for r in result['rows'])
    result['static_pass_boundaries'] = [r['boundary'] for r in result['rows'] if r['original_all_pass']]
    result['static_fail_boundaries'] = [r['boundary'] for r in result['rows'] if not r['original_all_pass']]
    result['conclusions'] = [
        'Minimal capture retains original image/scratch/ledger metadata and all frozen schedule samples. The unchanged static decisions are replayed, not replaced.',
        'Reduced saved bytes or shorter completed-output cadence does not establish accepted timing precision or a cause of remaining failures.',
        'GPU-duration/file-cadence ratios are descriptive proxies. Timestamped GPU busy/idle traces and clock/power causes were not measured.',
        'No timing correction, known-work subtraction, warmup change, exclusion, retry, gate relaxation or Lane M admission follows. All sixteen calibration boundaries remain required.']
    for path, digest in inputs.items():
        if sha(Path(path)) != digest:
            raise ValueError('frozen diagnostic input changed')
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'classification': result['classification'], 'decision_replay_all_match': True,
        'pass': result['static_pass_boundaries'], 'fail': result['static_fail_boundaries']}))

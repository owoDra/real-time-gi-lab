#!/usr/bin/env python3
"""CPU-only post-hoc capture-volume/order diagnosis of user-stopped 029."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from reference_provenance import ROOT, RESULTS, read, sha

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError('refuse existing diagnosis')
    inputs = {str(Path(__file__).resolve()):sha(Path(__file__))}
    partial = read(RESULTS/'029-full-renderer-calibration.json',inputs)
    stop = read(RESULTS/'150-user-requested-calibration-stop.json',inputs)
    if partial['complete'] or stop['preserved_partial']['sha256'] != sha(RESULTS/'029-full-renderer-calibration.json'):
        raise ValueError('stopped partial identity differs')
    source_paths = [ROOT/'scripts/research/n010_comparison_readiness/generate_calibration.py',
        ROOT/'build/n009/src/research/n010_comparison_readiness/generated/n010_runtime.cpp',
        ROOT/'src/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/stream_schema.hpp',
        ROOT/'src/research/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_gpu_layout.hpp',
        ROOT/'shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_bounded_producer.comp.glsl']
    inputs.update({str(p):sha(p) for p in source_paths})
    result = {'schema':'n010-stopped-calibration-posthoc-diagnosis/1','complete':False,
        'gpu_run':False,'classification':'POSTHOC_DIAGNOSTIC_ONLY','input_sha256':inputs,
        'scope':'Two completed C1 boundaries, block 0: whole-frame 64-sample saved hash variation, retained file mtimes and canonicalized first two work streams. No new measurement or cause attribution.',
        'rows':[],'calibration_pass_claimed':False,'thresholds_changed':False}
    for row in partial['rows'][:2]:
        block = row['blocks'][0]; name = row['boundary']['id']
        directory = ROOT/'out/research/n010-comparison-readiness/independent-quiet-calibration-v1/accepted'/name/'block-0'
        hashes = {}
        for rel,digest in block['payload_sha256'].items():
            parts = rel.split('/')
            if parts[0] == 'frames':
                hashes.setdefault('/'.join(parts[2:]),set()).add(digest)
        first_payloads = []
        sizes = []
        canonical = []
        for frame in (0,1):
            payload = {}
            for file in ('probe-work.bin','probe-hits.bin','probe-contributions.bin'):
                path = directory/'frames'/str(frame)/'gpu'/file
                digest = sha(path)
                if digest != block['payload_sha256'][str(path.relative_to(directory))]:
                    raise ValueError('retained payload changed')
                inputs[str(path)] = digest
                payload[file] = path.read_bytes()
            work = np.frombuffer(payload['probe-work.bin'],dtype='<u4').reshape(-1,16).copy()
            count = len(work)
            if len(payload['probe-hits.bin']) != count*32 or len(payload['probe-contributions.bin']) != count*8:
                raise ValueError('retained stream shapes differ')
            # Identity = surface_id, cascade, ray_index, unique within this stream.
            order = np.lexsort((work[:,4],work[:,3],work[:,6]))
            keys = work[order][:,[6,3,4]]
            if np.any(np.all(keys[1:] == keys[:-1],axis=1)):
                raise ValueError('canonical ray identity duplicates')
            # output_id is an append-position index; no physical data is masked.
            work[:,5] = 0
            canonical.append((work[order].tobytes(),
                np.frombuffer(payload['probe-hits.bin'],dtype='u1').reshape(count,32)[order].tobytes(),
                np.frombuffer(payload['probe-contributions.bin'],dtype='u1').reshape(count,8)[order].tobytes()))
            sizes.append({k:len(v) for k,v in payload.items()})
        files = [directory/'frames'/str(i)/'gpu/total.pfm' for i in range(64)]
        mtimes = [p.stat().st_mtime_ns for p in files]
        gaps = [(b-a)/1e6 for a,b in zip(mtimes,mtimes[1:])]
        stats = block['tagged_samples']
        control = [s for s in stats if s['kind']=='control' and not s['warmup']]
        result['rows'].append({'boundary':name,'saved_payload_unique_counts_64_frames':{k:len(v) for k,v in hashes.items()},
            'first_two_frames_stream_bytes':sizes,'ray_count_per_frame':count,
            'first_two_frames_canonical_work_equal':canonical[0][0]==canonical[1][0],
            'first_two_frames_canonical_hits_equal':canonical[0][1]==canonical[1][1],
            'first_two_frames_canonical_contributions_equal':canonical[0][2]==canonical[1][2],
            'canonicalization':'Sort by unique (surface_id,cascade,ray_index); normalize only work.output_id append-position index. This is diagnostic, not an acceptance exclusion.',
            'retained_total_file_mtimes_ns':mtimes,
            'retained_file_mtime_gap_ms':{'median':statistics.median(gaps),'minimum':min(gaps),'maximum':max(gaps)},
            'median_frame_gpu_us':statistics.median(s['gpu_us'] for s in stats),
            'median_frame_wall_us_excludes_readback':statistics.median(s['wall_us'] for s in stats),
            'control_gpu_median_us_by_physical_position':{str(i):statistics.median(s['gpu_us'] for s in control if s['index']%4==i) for i in range(4)}})
    result['conclusions'] = [
        'HDR byte identity is not byte identity of the captured work stream. Native producer atomic appends assign order and output IDs independently each frame.',
        'Only the first two frames per boundary are canonicalized here. Equal canonical fields, if observed, do not prove identical cache/dispatch behavior or explain timing variation.',
        'Saved file mtimes show completed-output cadence, not direct timestamped CPU idle duration. Readback, state export, disk IO and other activity are not separated.',
        'Source performs full diagnostic/state readback and synchronous file output between timed frames. A future prospective minimal/buffered capture can isolate its effect while preserving every image/scratch/timing and full Renderer boundaries.',
        'No GPU clock/power explanation is established; no clock/power change, gate relaxation, sample exclusion or calibration PASS follows.']
    for path,digest in inputs.items():
        if sha(Path(path)) != digest:
            raise ValueError('diagnostic input changed')
    result['complete'] = True
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'classification':result['classification'],'rows':[{k:v for k,v in r.items() if k.startswith(('boundary','first_two_frames_canonical'))} for r in result['rows']]}))

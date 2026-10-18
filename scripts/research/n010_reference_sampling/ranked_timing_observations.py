"""Raw-frame decoding for plan117's conditional numerical core.

Expected records must come from the caller's pinned prospective schedule.
Decoding validates paired identities and arithmetic, not image/scene/native
semantics or evidence admission. It never acquires or starts another process.
"""
import math
import statistics

from ranked_timing_decision import KINDS, ORDERS


def decode_process(raw_frames, records, process_identity, frames_per_observation):
    if type(frames_per_observation) is not int or frames_per_observation < 1:
        raise ValueError('explicit positive observation frame count required')
    if len(records) != 60 or len(raw_frames) != 60 * frames_per_observation:
        raise ValueError('all warmup and measured frames required')
    observations = []
    for i, record in enumerate(records):
        if (set(record) != {'index', 'pair', 'warmup', 'kind', 'arm', 'order', 'dose'}
                or type(record['index']) is not int or record['index'] != i
                or type(record['pair']) is not int or record['pair'] not in range(10)
                or type(record['warmup']) is not bool
                or record['warmup'] != (record['pair'] < 4)
                or record['kind'] not in KINDS or record['order'] not in ORDERS
                or record['arm'] not in ('A', 'B')
                or type(record['dose']) is not int or record['dose'] < 0):
            raise ValueError('invalid frozen observation label')
        begin = i * frames_per_observation
        frames = raw_frames[begin:begin + frames_per_observation]
        for j, frame in enumerate(frames):
            if (type(frame['index']) is not int or frame['index'] != begin + j
                    or type(frame['dose']) is not int or frame['dose'] != record['dose']
                    or type(frame['gpu_us']) not in (int, float)
                    or not math.isfinite(frame['gpu_us']) or frame['gpu_us'] <= 0
                    or type(frame['known_work_gpu_us']) not in (int, float)
                    or not math.isfinite(frame['known_work_gpu_us'])
                    or frame['known_work_gpu_us'] < 0):
                raise ValueError('raw timestamp/index/dose differs; no filtering')
        observations.append(dict(
            index=i, dose=record['dose'],
            gpu_us=statistics.mean(f['gpu_us'] for f in frames),
            known_work_gpu_us=statistics.mean(f['known_work_gpu_us'] for f in frames),
            constituent_indices=list(range(begin, begin + frames_per_observation))))
    # Do not accept reordered rounds, repeated pairs or nonadjacent pseudo-arms.
    for pair in range(10):
        segment = records[pair * 6:(pair + 1) * 6]
        if any(r['pair'] != pair for r in segment):
            raise ValueError('round order differs')
        if {segment[j]['kind'] for j in (0, 2, 4)} != set(KINDS):
            raise ValueError('each round requires all three populations')
        for j in (0, 2, 4):
            a, b = segment[j:j + 2]
            if (a['kind'] != b['kind'] or a['order'] != b['order']
                    or a['arm'] + b['arm'] != a['order']):
                raise ValueError('consecutive paired arms required')
    pairs = {kind: {order: [] for order in ORDERS} for kind in KINDS}
    for kind in KINDS:
        warmups = [r for r in records if r['kind'] == kind and r['warmup'] and r['arm'] == 'A']
        if any(sum(r['order'] == order for r in warmups) != 2 for order in ORDERS):
            raise ValueError('two warmup pairs per kind/order required')
        for pair in range(4, 10):
            indices = [i for i, r in enumerate(records) if r['kind'] == kind and r['pair'] == pair]
            a = next(i for i in indices if records[i]['arm'] == 'A')
            b = next(i for i in indices if records[i]['arm'] == 'B')
            value = math.log(observations[b]['gpu_us'] / observations[a]['gpu_us'])
            if not math.isfinite(value):
                raise ValueError('nonfinite derived paired ratio')
            pairs[kind][records[a]['order']].append(value)
        if any(len(pairs[kind][order]) != 3 for order in ORDERS):
            raise ValueError('three measured pairs per kind/order required')
    return dict(process_identity=list(process_identity), paired_log_ratios=pairs), observations

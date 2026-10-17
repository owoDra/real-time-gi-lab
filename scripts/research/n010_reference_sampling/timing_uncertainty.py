"""Plan100: randomized paired schedules and process-median uncertainty.

No acquisition at import. This is opt-in research analysis, not Renderer code.
"""
import hashlib
import math
import random
import statistics

BLOCKS = 12
KINDS = ('control_a', 'control_b', 'effect')
ORDERS = ('AB', 'BA')
FAMILY_BOUNDARIES = 16
INTERVALS_PER_BOUNDARY = len(KINDS) * len(ORDERS)
INTERVAL_ALPHA = 2 / 2**BLOCKS
FAMILY_ALPHA_BOUND = FAMILY_BOUNDARIES * INTERVALS_PER_BOUNDARY * INTERVAL_ALPHA
RESOLUTION_RATIO = 1.20
SEED_LABEL = 'N010-plan100-order-aware-process-median-v1'


def schedule(dose, block):
    if not isinstance(dose, int) or not 0 < dose <= 100000000:
        raise ValueError('positive frozen known-work dose required')
    if block not in range(BLOCKS):
        raise ValueError('unregistered process block')
    seed = int.from_bytes(hashlib.sha256(f'{SEED_LABEL}:{block}'.encode()).digest(), 'big')
    rng = random.Random(seed)
    orders = {}
    for kind in KINDS:
        warmup = ['AB', 'BA'] * 2
        measured = ['AB', 'BA'] * 3
        rng.shuffle(warmup)
        rng.shuffle(measured)
        orders[kind] = warmup + measured
    records = []
    for pair in range(10):
        kinds = list(KINDS)
        rng.shuffle(kinds)
        for kind in kinds:
            order = orders[kind][pair]
            for arm in order:
                work = dose if kind == 'control_b' or (kind == 'effect' and arm == 'B') else 0
                records.append(dict(index=len(records), pair=pair, warmup=pair < 4,
                                    kind=kind, arm=arm, order=order, dose=work))
    return records


def median_interval(values):
    if len(values) != BLOCKS or any(not math.isfinite(x) for x in values):
        raise ValueError('twelve finite fresh-process summaries required')
    # Closed order-statistic interval. Ties remain; no interpolation/bootstrap.
    return dict(point=statistics.median(values), lower=min(values), upper=max(values),
                repetitions=BLOCKS, noncoverage_bound=INTERVAL_ALPHA)


def analyze(blocks, dose):
    if len(blocks) != BLOCKS:
        raise ValueError('registered fresh-process count differs')
    series = {kind: {order: [] for order in ORDERS} for kind in KINDS}
    summaries = []
    for i, block in enumerate(blocks):
        samples = block['tagged_samples']
        records = schedule(dose, i)
        if len(samples) != len(records):
            raise ValueError('registered observation count differs')
        for s, r in zip(samples, records):
            if any(s.get(k) != v for k, v in r.items()):
                raise ValueError('actual tagged schedule differs')
            if not math.isfinite(s['gpu_us']) or s['gpu_us'] <= 0:
                raise ValueError('nonpositive/nonfinite GPU observation')
        process = {}
        for kind in KINDS:
            process[kind] = {}
            for order in ORDERS:
                values = []
                for pair in range(4, 10):
                    group = [s for s in samples if s['pair'] == pair and s['kind'] == kind]
                    if len(group) != 2 or {s['arm'] for s in group} != {'A', 'B'}:
                        raise ValueError('paired arm identity differs')
                    if group[0]['order'] != order:
                        continue
                    a = next(s['gpu_us'] for s in group if s['arm'] == 'A')
                    b = next(s['gpu_us'] for s in group if s['arm'] == 'B')
                    values.append(math.log(b / a))
                if len(values) != 3:
                    raise ValueError('three measured pairs per kind/order required')
                med = statistics.median(values)
                process[kind][order] = dict(paired_log_ratios=values, median_log_ratio=med)
                series[kind][order].append(med)
        summaries.append(process)
    intervals = {kind: {order: median_interval(values) for order, values in by_order.items()}
                 for kind, by_order in series.items()}
    by_order = {}
    for order in ORDERS:
        ca, cb = intervals['control_a'][order], intervals['control_b'][order]
        effect = intervals['effect'][order]
        bias = max(abs(x) for c in (ca, cb) for x in (c['lower'], c['upper']))
        by_order[order] = dict(
            control_locations_compatible=max(ca['lower'], cb['lower']) <= min(ca['upper'], cb['upper']),
            control_log_bias_allowance=bias,
            lower_log=effect['lower'] - bias, upper_log=effect['upper'] + bias)
    lower = min(v['lower_log'] for v in by_order.values())
    upper = max(v['upper_log'] for v in by_order.values())
    overlap = max(v['lower_log'] for v in by_order.values()) <= min(v['upper_log'] for v in by_order.values())
    checks = dict(
        same_role_control_locations_compatible=all(v['control_locations_compatible'] for v in by_order.values()),
        order_intervals_compatible_after_allowance=overlap,
        positive_effect_after_control_allowance=lower > 0,
        interval_width_within_registered_resolution=upper - lower <= math.log(RESOLUTION_RATIO))
    return dict(process_summaries=summaries, log_median_intervals=intervals, by_order=by_order,
                effect_ratio_interval=dict(lower=math.exp(lower), upper=math.exp(upper),
                                           multiplicative_width=math.exp(upper - lower)),
                family_boundaries=FAMILY_BOUNDARIES, intervals_per_boundary=INTERVALS_PER_BOUNDARY,
                family_noncoverage_bound=FAMILY_ALPHA_BOUND,
                statistical_scope='Process-summary medians under independent repetitions/common medians; '
                                  'bias allowance additionally conditional on the registered nuisance model. '
                                  'Not a distribution-free guarantee against arbitrary carryover or drift.',
                checks=checks, all_pass=all(checks.values()))

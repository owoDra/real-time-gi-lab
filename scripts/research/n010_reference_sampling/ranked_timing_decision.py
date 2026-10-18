"""Plan117: numerical core for prospectively registered timing decisions.

This module performs no acquisition, imports no Renderer, and grants no proof
admission. A full-boundary verifier must validate the raw evidence before using
its conditional classifications. Old diagnostic results remain diagnostic.
"""
import math
import statistics


PROCESSES = 24
KINDS = ('control_a', 'control_b', 'effect')
ORDERS = ('AB', 'BA')
FAMILY_ALPHA = .05
PRACTICAL_RATIO = 1.20


def design(boundary_ids):
    """Freeze the complete simultaneous family before observing new data.

    Each separately claimed dynamic frame is a separate boundary. This avoids
    quietly treating a five-frame trajectory as one calibrated static frame.
    """
    ids = list(boundary_ids)
    if not ids or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError('nonempty explicit boundary identities required')
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate timing boundary')
    interval_count = len(ids) * len(KINDS) * len(ORDERS)
    admitted = []
    for rank in range(1, PROCESSES // 2 + 1):
        alpha = 2 * sum(math.comb(PROCESSES, j) for j in range(rank)) / 2**PROCESSES
        if interval_count * alpha <= FAMILY_ALPHA:
            admitted.append((rank, alpha))
    if not admitted:
        raise ValueError('family too large for registered process count')
    rank, alpha = admitted[-1]
    return dict(schema='n010-ranked-timing-design/1', boundary_ids=ids,
                processes=PROCESSES, rank=rank, intervals_per_boundary=6,
                interval_noncoverage_bound=alpha,
                family_noncoverage_bound=interval_count * alpha,
                family_alpha_limit=FAMILY_ALPHA, practical_ratio=PRACTICAL_RATIO)


def _interval(values, frozen):
    if len(values) != PROCESSES or any(not math.isfinite(x) for x in values):
        raise ValueError('24 finite process summaries required')
    ranked = sorted(values)
    rank = frozen['rank']
    return dict(point=statistics.median(values), lower=ranked[rank - 1],
                upper=ranked[PROCESSES - rank], sorted_values=ranked,
                repetitions=PROCESSES, rank=rank,
                noncoverage_bound=frozen['interval_noncoverage_bound'])


def decide(frozen, boundary_id, processes, *, purpose, quality_status,
           evidence_verified, nuisance_model_justified):
    """Recompute medians/intervals; return a conditional numerical decision.

    Input: 24 process dictionaries, each containing process_identity=[boot_id,
    pid,start_ticks] and paired_log_ratios[kind][order] (three measured pairs).
    The caller must independently verify all raw GPU timestamps, exact paired
    schedule, warmups, physical/quality parity, native identities and resources.
    Boolean caller assessments are NOT evidence of that verification.

    Effects are positive-dose / zero-dose for calibration and candidate /
    baseline for comparison. Controls compare the same role to itself. All
    values, including extremes, remain in the returned evidence.
    """
    if frozen != design(frozen['boundary_ids']):
        raise ValueError('registered design differs from the fixed algorithm')
    if boundary_id not in frozen['boundary_ids']:
        raise ValueError('unregistered boundary')
    if purpose not in ('calibration', 'comparison'):
        raise ValueError('unknown timing purpose')
    if quality_status not in ('PASS', 'FAIL', 'UNKNOWN'):
        raise ValueError('explicit quality classification required')
    if type(evidence_verified) is not bool or type(nuisance_model_justified) is not bool:
        raise ValueError('explicit evidence and nuisance assessments required')
    if len(processes) != PROCESSES:
        raise ValueError('24 original fresh-process repetitions required')
    identities = set()
    boot = None
    series = {kind: {order: [] for order in ORDERS} for kind in KINDS}
    summaries = []
    for process in processes:
        identity = process['process_identity']
        if (not isinstance(identity, list) or len(identity) != 3
                or not isinstance(identity[0], str) or not identity[0]
                or any(type(x) is not int or x <= 0 for x in identity[1:])):
            raise ValueError('boot/PID/start identity required')
        key = tuple(identity)
        if key in identities:
            raise ValueError('reused process is not an independent repetition')
        identities.add(key)
        boot = identity[0] if boot is None else boot
        if identity[0] != boot:
            raise ValueError('do not pool different boots')
        pairs = process['paired_log_ratios']
        if set(pairs) != set(KINDS):
            raise ValueError('missing or extra control/effect population')
        summary = dict(process_identity=identity, populations={})
        for kind in KINDS:
            if set(pairs[kind]) != set(ORDERS):
                raise ValueError('both orders required separately')
            summary['populations'][kind] = {}
            for order in ORDERS:
                values = pairs[kind][order]
                if (not isinstance(values, list) or len(values) != 3
                        or any(type(x) not in (int, float) or not math.isfinite(x)
                               for x in values)):
                    raise ValueError('three finite measured paired log ratios required')
                median = statistics.median(values)
                series[kind][order].append(median)
                summary['populations'][kind][order] = dict(
                    paired_log_ratios=list(values), median_log_ratio=median)
        summaries.append(summary)
    intervals = {kind: {order: _interval(values, frozen)
                        for order, values in by_order.items()}
                 for kind, by_order in series.items()}
    orders = {}
    for order in ORDERS:
        ca, cb = (intervals[k][order] for k in ('control_a', 'control_b'))
        effect = intervals['effect'][order]
        allowance = max(abs(c[k]) for c in (ca, cb) for k in ('lower', 'upper'))
        orders[order] = dict(
            controls_compatible=max(ca['lower'], cb['lower']) <= min(ca['upper'], cb['upper']),
            control_log_bias_allowance=allowance,
            lower_log=effect['lower'] - allowance,
            upper_log=effect['upper'] + allowance)
    lower = min(x['lower_log'] for x in orders.values())
    upper = max(x['upper_log'] for x in orders.values())
    checks = dict(
        same_role_control_locations_compatible=all(x['controls_compatible'] for x in orders.values()),
        order_intervals_compatible_after_allowance=(
            max(x['lower_log'] for x in orders.values()) <=
            min(x['upper_log'] for x in orders.values())))
    if purpose == 'calibration':
        checks.update(positive_effect_after_control_allowance=lower > 0,
                      interval_width_within_registered_resolution=(
                          upper - lower <= math.log(PRACTICAL_RATIO)))
    threshold = math.log(PRACTICAL_RATIO)
    if not evidence_verified:
        outcome = 'INVALID_OR_UNVERIFIED_EVIDENCE'
    elif quality_status != 'PASS':
        outcome = 'QUALITY_UNMATCHED' if quality_status == 'FAIL' else 'QUALITY_NOT_ESTABLISHED'
    elif not nuisance_model_justified or not all(checks.values()):
        outcome = 'TIMING_INCONCLUSIVE'
    elif purpose == 'calibration':
        outcome = 'BOUNDED_CALIBRATION_PASS'
    elif upper < -threshold:
        outcome = 'PRACTICAL_WIN'
    elif lower > threshold:
        outcome = 'PRACTICAL_LOSS'
    elif lower >= -threshold and upper <= threshold:
        outcome = 'PRACTICAL_EQUIVALENCE'
    else:
        outcome = 'TIMING_INCONCLUSIVE'
    # Exponentiation can overflow for corrupt numerical inputs. Refuse it;
    # never replace infinity with a favorable clamped decision.
    ratio = dict(lower=math.exp(lower), upper=math.exp(upper),
                 multiplicative_width=math.exp(upper - lower))
    if any(not math.isfinite(x) or x <= 0 for x in ratio.values()):
        raise ValueError('unrepresentable timing interval')
    return dict(schema='n010-ranked-timing-decision/1', design=frozen,
                boundary_id=boundary_id, purpose=purpose, process_summaries=summaries,
                log_median_intervals=intervals, by_order=orders,
                effect_ratio_interval=ratio, numerical_checks=checks,
                quality_status=quality_status,
                caller_evidence_verified=evidence_verified,
                caller_nuisance_model_justified=nuisance_model_justified,
                conditional_numerical_classification=outcome,
                accepted_timing=False, proof_admission=False,
                statistical_scope='Simultaneous raw median intervals assume independent '
                    'process repetitions and common medians. The expanded effect interval '
                    'additionally assumes effect nuisance shifts are bounded by the '
                    'same-role controls. Compatibility does not prove that model. '
                    'Fresh process identities do not establish statistical independence.')

"""Plan103: independently acquired24-process exact median intervals.

The sealed100 module stays byte-identical. Import performs no acquisition.
"""
import hashlib
from pathlib import Path

BASE = Path(__file__).with_name('timing_uncertainty.py')
if hashlib.sha256(BASE.read_bytes()).hexdigest() != '84f9845c84bfece4ea255c3e83c612faa85096f6b398a490dda5bafdcfe9cac3':
    raise ValueError('sealed100 analysis changed')
source = BASE.read_text()
edits = [
    ('Plan100: randomized paired schedules and process-median uncertainty.',
     'Plan103: randomized paired schedules and exact ranked process-median intervals.'),
    ('BLOCKS = 12', 'BLOCKS = 24\nINTERVAL_RANK = 4'),
    ('INTERVAL_ALPHA = 2 / 2**BLOCKS',
     'INTERVAL_ALPHA = 2 * sum(math.comb(BLOCKS, j) for j in range(INTERVAL_RANK)) / 2**BLOCKS'),
    ("SEED_LABEL = 'N010-plan100-order-aware-process-median-v1'",
     "SEED_LABEL = 'N010-plan103-ranked-process-median-v1'"),
    ('twelve finite fresh-process summaries required', 'twenty-four finite fresh-process summaries required'),
    ('    # Closed order-statistic interval. Ties remain; no interpolation/bootstrap.\n'
     '    return dict(point=statistics.median(values), lower=min(values), upper=max(values),',
     '    # Registered exact order statistic; retain ties and all ranked values.\n'
     '    ranked = sorted(values)\n'
     '    return dict(point=statistics.median(values), lower=ranked[INTERVAL_RANK-1],\n'
     '                upper=ranked[BLOCKS-INTERVAL_RANK], rank=INTERVAL_RANK, sorted_values=ranked,'),
]
revised = source
for old, new in edits:
    if revised.count(old) != 1:
        raise ValueError('nonunique plan103 analysis edit')
    revised = revised.replace(old, new)
inverse = revised
for old, new in reversed(edits):
    if inverse.count(new) != 1:
        raise ValueError('nonunique plan103 analysis inverse')
    inverse = inverse.replace(new, old)
if inverse != source:
    raise ValueError('whole100 analysis inverse differs')
exec(compile(revised, str(BASE), 'exec'), globals())
next_rank_alpha = 2 * sum(math.comb(BLOCKS, j) for j in range(INTERVAL_RANK+1)) / 2**BLOCKS
if FAMILY_ALPHA_BOUND > .05 or FAMILY_BOUNDARIES * INTERVALS_PER_BOUNDARY * next_rank_alpha <= .05:
    raise ValueError('registered rank is not the largest admitted by the family coverage budget')

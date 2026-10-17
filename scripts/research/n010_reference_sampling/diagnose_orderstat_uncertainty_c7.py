#!/usr/bin/env python3
"""Plan103: one independent fixed24-process C7 calibration acquisition."""
import hashlib
import json
from pathlib import Path

SEALED100 = Path(__file__).with_name('diagnose_uncertainty_c7.py')
if hashlib.sha256(SEALED100.read_bytes()).hexdigest() != '69544025aa208fb85bd0a3a3a5b59bcff647e03c9d6ea42ad74adb5ea4334761':
    raise ValueError('sealed100 acquisition changed')
root = Path(__file__).resolve().parents[3]
results = root / 'research/lanes/n010-comparison-readiness/results'
for name in ('252-all-split-original-sealed-dark-full-control.json',
             '253-all-split-original-sealed-lit-full-control.json'):
    data = json.loads((results/name).read_bytes())
    if not data['complete'] or not data['all_pass']:
        raise ValueError('finish both original full sealed controls before new GPU acquisition')
prototype = json.loads((results/'254-wide8-cpu-bvh-prototype.json').read_bytes())
if prototype['classification'] not in ('EXECUTION_PROTOTYPE_COMPLETE_NO_ADMISSION',
                                        'EXECUTION_PROTOTYPE_FAILURE_PARTIALS_RETAINED'):
    raise ValueError('terminal254 required; do not overlap or wait automatically')
source = SEALED100.read_text()
edits = [
    ('import timing_uncertainty as U', 'import timing_uncertainty_orderstats as U', 1),
    ('250-uncertainty-c7-calibration-diagnostic', '255-orderstat-uncertainty-c7-calibration-diagnostic', 1),
    ('uncertainty-c7-diagnostic-v1', 'orderstat-uncertainty-c7-diagnostic-v1', 1),
    ('100-order-aware-timing-uncertainty.md', '103-ranked-process-median-calibration.md', 2),
    ('n010-uncertainty-c7-diagnostic/1', 'n010-orderstat-uncertainty-c7-diagnostic/1', 1),
    ("timing_method='plan100-v1'", "timing_method='plan103-v1'", 1),
    ('BASE,SEALED098,Path(U.__file__),RESULTS.parent/',
     'BASE,SEALED098,SEALED100,Path(U.__file__),U.BASE,RESULTS.parent/', 1),
    ("addition = F.addition.replace('8*1024**3', '12*1024**3').replace('requires8GiB', 'requires12GiB')",
     "addition = F.addition.replace('8*1024**3', '24*1024**3').replace('requires8GiB', 'requires24GiB')", 1),
    ("addition = addition.replace('6*1024**3', '8*1024**3').replace('exceeds6GiB', 'exceeds8GiB')",
     "addition = addition.replace('6*1024**3', '16*1024**3').replace('exceeds6GiB', 'exceeds16GiB')", 1),
    ('plan100 acquisition wall budget exhausted', 'plan103 acquisition wall budget exhausted', 1),
]
revised = source
for old, new, count in edits:
    if revised.count(old) != count or new in revised:
        raise ValueError('plan103 acquisition edit count differs: ' + old[:80])
    revised = revised.replace(old, new)
inverse = revised
for old, new, count in reversed(edits):
    if inverse.count(new) != count:
        raise ValueError('plan103 acquisition inverse count differs')
    inverse = inverse.replace(new, old)
if inverse != source:
    raise ValueError('whole100 acquisition inverse differs')
exec(compile(revised, str(SEALED100), 'exec'), globals())

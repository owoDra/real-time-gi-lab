#!/usr/bin/env python3
"""Plan100: bounded prospective C7 uncertainty-method acquisition only."""
import hashlib
import sys
from pathlib import Path

import diagnose_four_frame_c7 as F
import timing_uncertainty as U

SEALED098 = Path(F.__file__)
if hashlib.sha256(SEALED098.read_bytes()).hexdigest() != '02f6a84de18a88f74c6117115ffb824cf3e726976b9baaaebd0aeaf384e9f1eb':
    raise ValueError('sealed098 changed')
if sys.argv[1:] != ['--mode', 'diagnostic']:
    raise ValueError('plan100 diagnostic only; reuses frozen246 sizing')
BASE = F.BASE
source = F.source
if hashlib.sha256(BASE.read_bytes()).hexdigest() != F.EXPECTED:
    raise ValueError('sealed063 changed')

addition = F.addition.replace('8*1024**3', '12*1024**3').replace('requires8GiB', 'requires12GiB')
addition = addition.replace('6*1024**3', '8*1024**3').replace('exceeds6GiB', 'exceeds8GiB')
edits = [
    ("stem='207-contiguous-c7-sizing' if mode=='sizing' else '208-contiguous-c7-precision-diagnostic'",
     "stem='UNUSED_PLAN100_SIZING' if mode=='sizing' else '250-uncertainty-c7-calibration-diagnostic'"),
    ("sizing_path=RESULTS/'207-contiguous-c7-sizing.json'", "sizing_path=RESULTS/'246-four-frame-c7-sizing.json'"),
    ('contiguous-c7-diagnostic-v3', 'uncertainty-c7-diagnostic-v1'),
    ("for p in (Path(__file__),HERE/'build_contiguous_c7_capture_v3.py'",
     "for p in (Path(__file__),BASE,SEALED098,Path(U.__file__),RESULTS.parent/'experiments/100-order-aware-timing-uncertainty.md',HERE/'build_contiguous_c7_capture_v3.py'"),
    ("schema='n010-contiguous-c7-diagnostic/1'", "schema='n010-uncertainty-c7-diagnostic/1'"),
    ('    def execute(doses,directory):', '    def execute_native(doses,directory):'),
    ('    try:\n        row=dict(boundary=boundary);', addition + '\n    try:\n        row=dict(boundary=boundary);'),
    ('            for i in range(8):', '            for i in range(U.BLOCKS):'),
    ('            for i in range(U.BLOCKS):',
     "            campaign_started=time.monotonic()\n            for i in range(U.BLOCKS):\n                if time.monotonic()-campaign_started>180:raise ValueError('plan100 acquisition wall budget exhausted')"),
    ('records=C.schedule(frozen,i)',
     "records=U.schedule(frozen,i)\n                (work/boundary['id']).mkdir(parents=True,exist_ok=True)\n                (work/boundary['id']/f'block-{i}.schedule.json').write_text(json.dumps(records,indent=2)+'\\n')"),
    ("row['analysis']=C.analysis(row['blocks'])", "row['analysis']=U.analyze(row['blocks'],frozen)"),
    ('schedule_analysis_source_sha256=sha(C.__file__),',
     'schedule_analysis_source_sha256=sha(Path(U.__file__)), original_schedule_analysis_not_used=True,'),
    ("tests='NOT_RUN; isolated scientific acquisition, not regression validation')",
     "tests='NOT_RUN; isolated scientific acquisition, not regression validation', observation_frames=4, individual_frame_precision_not_claimed=True, timing_method='plan100-v1', python_version=sys.version, schedule_seed_label=U.SEED_LABEL, prospective_protocol_sha256=sha(RESULTS.parent/'experiments/100-order-aware-timing-uncertainty.md'))"),
]
revised = source
for old, new in edits:
    if revised.count(old) != 1:
        raise ValueError('nonunique plan100 edit: ' + old[:80])
    revised = revised.replace(old, new)
inverse = revised
for old, new in reversed(edits):
    if inverse.count(new) != 1:
        raise ValueError('nonunique plan100 inverse')
    inverse = inverse.replace(new, old)
if inverse != source:
    raise ValueError('whole frozen063 inverse differs')
exec(compile(revised, str(BASE), 'exec'), globals())

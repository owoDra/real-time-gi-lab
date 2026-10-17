#!/usr/bin/env python3
"""Plan099: symmetric positions within paired four-frame static observations."""
import hashlib
import sys
from pathlib import Path

SEALED098=Path(__file__).with_name('diagnose_four_frame_c7.py')
EXPECTED098='02f6a84de18a88f74c6117115ffb824cf3e726976b9baaaebd0aeaf384e9f1eb'
if hashlib.sha256(SEALED098.read_bytes()).hexdigest()!=EXPECTED098:
    raise ValueError('sealed098 driver changed')
if '--mode' not in sys.argv or sys.argv[sys.argv.index('--mode')+1]!='diagnostic':
    raise ValueError('plan099 reuses246 sizing; diagnostic mode only')
source=SEALED098.read_text()
expanded='''        if len(doses)%2:raise ValueError('interleaved observations require pairs')
        pattern=(0,1,1,0,1,0,0,1)
        constituent_indices=[None]*len(doses)
        expanded=[]
        for first in range(0,len(doses),2):
            base=4*first
            for side in (0,1):
                constituent_indices[first+side]=[base+j for j,x in enumerate(pattern) if x==side]
            expanded.extend(doses[first+x] for x in pattern)
        if sorted(j for group in constituent_indices for j in group)!=list(range(4*len(doses))):
            raise ValueError('raw frame mapping missing/duplicate')'''
edits=[
    ('247-four-frame-c7-precision-diagnostic','248-interleaved-four-frame-c7-precision-diagnostic'),
    ('four-frame-c7-diagnostic-v1','interleaved-four-frame-c7-diagnostic-v1'),
    ("RESULTS.parent/'experiments/098-four-frame-c7-observation-diagnosis.md',HERE/",
     "SEALED098,RESULTS.parent/'experiments/098-four-frame-c7-observation-diagnosis.md',RESULTS.parent/'experiments/099-interleaved-four-frame-c7-diagnosis.md',HERE/"),
    ("schema='n010-four-frame-c7-diagnostic/1'", "schema='n010-interleaved-four-frame-c7-diagnostic/1'"),
    ('        expanded=[dose for dose in doses for _ in range(4)]',expanded),
    ("            frames=raw[4*i:4*i+4]\n            if any(f['dose']!=dose or f['index']!=4*i+j for j,f in enumerate(frames)):",
     "            indices=constituent_indices[i]\n            frames=[raw[j] for j in indices]\n            if any(f['dose']!=dose or f['index']!=j for j,f in zip(indices,frames)):"),
    ('constituent_indices=list(range(4*i,4*i+4))','constituent_indices=indices'),
    ("individual_frame_precision_not_claimed=True,\n            cpu_wall_scope=",
     "individual_frame_precision_not_claimed=True, paired_lane_pattern=list(pattern),\n            order_scope='AB/BA is first actual occurrence; arms interleaved symmetrically',\n            cpu_wall_scope="),
]
revised=source
for a,b in edits:
    if revised.count(a)!=1:raise ValueError('nonunique interleave edit: '+a[:70])
    revised=revised.replace(a,b)
inverse=revised
for a,b in reversed(edits):
    if inverse.count(b)!=1:raise ValueError('nonunique interleave inverse')
    inverse=inverse.replace(b,a)
if inverse!=source:raise ValueError('interleave driver inverse differs')
exec(compile(revised,str(SEALED098),'exec'),globals())

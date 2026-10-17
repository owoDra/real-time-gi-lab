#!/usr/bin/env python3
"""Plan098: all raw frames retained, four-frame static GPU mean observations."""
import hashlib
from pathlib import Path

BASE=Path(__file__).with_name('diagnose_contiguous_c7.py')
EXPECTED='0dd268e9c701fcca65519b168e8404e05d49e809de3685d8834c77f8b32a904d'
if hashlib.sha256(BASE.read_bytes()).hexdigest()!=EXPECTED:
    raise ValueError('sealed063/065 diagnostic driver changed')
source=BASE.read_text()
addition='''
    def execute(doses,directory):
        import shutil
        if shutil.disk_usage(WORK).free < 8*1024**3:
            raise ValueError('four-frame diagnostic requires8GiB free disk')
        expanded=[dose for dose in doses for _ in range(4)]
        if not doses or len(expanded)>256:
            raise ValueError('four-frame expansion exceeds exact fixture capacity')
        block=execute_native(expanded,directory)
        raw=block['samples']
        if len(raw)!=4*len(doses):raise ValueError('four-frame sample count differs')
        if any(not math.isfinite(f['gpu_us']) or f['gpu_us']<=0 or
               not math.isfinite(f['known_work_gpu_us']) or f['known_work_gpu_us']<0 for f in raw):
            raise ValueError('nonfinite/nonpositive GPU frame sample; no filtering')
        grouped=[]
        for i,dose in enumerate(doses):
            frames=raw[4*i:4*i+4]
            if any(f['dose']!=dose or f['index']!=4*i+j for j,f in enumerate(frames)):
                raise ValueError('four-frame constituent identity differs')
            grouped.append(dict(index=i,dose=dose,
                gpu_us=statistics.mean(f['gpu_us'] for f in frames),
                known_work_gpu_us=statistics.mean(f['known_work_gpu_us'] for f in frames),
                constituent_indices=list(range(4*i,4*i+4))))
        block['raw_frame_samples']=raw
        block['samples']=grouped
        block['observation_unit']=dict(kind='arithmetic_mean_of_four_original_gpu_frame_intervals',
            frames_per_observation=4,original_gpu_frames=len(raw),observations=len(grouped),
            individual_frame_precision_not_claimed=True,
            cpu_wall_scope='Native batch/cached-call only; no independent frame CPU times')
        root=directory.parent.parent
        retained=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
        if retained>6*1024**3:raise ValueError('four-frame retained spool exceeds6GiB')
        block['retained_work_bytes_after_this_native']=retained
        return block
'''
edits=[
    ("stem='207-contiguous-c7-sizing' if mode=='sizing' else '208-contiguous-c7-precision-diagnostic'",
     "stem='246-four-frame-c7-sizing' if mode=='sizing' else '247-four-frame-c7-precision-diagnostic'"),
    ("sizing_path=RESULTS/'207-contiguous-c7-sizing.json'", "sizing_path=RESULTS/'246-four-frame-c7-sizing.json'"),
    ('contiguous-c7-sizing-v3','four-frame-c7-sizing-v1'),
    ('contiguous-c7-diagnostic-v3','four-frame-c7-diagnostic-v1'),
    ("for p in (Path(__file__),HERE/'build_contiguous_c7_capture_v3.py'",
     "for p in (Path(__file__),BASE,RESULTS.parent/'experiments/098-four-frame-c7-observation-diagnosis.md',HERE/'build_contiguous_c7_capture_v3.py'"),
    ("schema='n010-contiguous-c7-diagnostic/1'","schema='n010-four-frame-c7-diagnostic/1'"),
    ('    def execute(doses,directory):','    def execute_native(doses,directory):'),
    ('    try:\n        row=dict(boundary=boundary);',addition+'\n    try:\n        row=dict(boundary=boundary);'),
    ("tests='NOT_RUN; isolated scientific acquisition, not regression validation')",
     "tests='NOT_RUN; isolated scientific acquisition, not regression validation', observation_frames=4, individual_frame_precision_not_claimed=True)"),
]
revised=source
for a,b in edits:
    if revised.count(a)!=1:raise ValueError('nonunique four-frame edit: '+a[:60])
    revised=revised.replace(a,b)
inverse=revised
for a,b in reversed(edits):
    if inverse.count(b)!=1:raise ValueError('nonunique four-frame inverse')
    inverse=inverse.replace(b,a)
if inverse!=source:raise ValueError('four-frame whole driver inverse differs')
exec(compile(revised,str(BASE),'exec'),globals())

#!/usr/bin/env python3
"""Plan077: original Xoshiro API repair before first native control."""
from pathlib import Path
import hashlib
import diagnose_selected_bounce_paths as D

original=Path(__file__).with_name('validate_all_split_furnace.py')
if hashlib.sha256(original.read_bytes()).hexdigest()!='b38107f672368de0e8178e9077073643022e77207e651e015b7746104a436054':
    raise ValueError('original076 driver identity differs')
D.checked(original)
D.checked(D.RESULTS.parent/'experiments/076-bounded-all-split-furnace-control.md')
import json
failed=json.loads(D.checked(D.RESULTS/'219-bounded-all-split-furnace-control.json'))
if failed['complete'] or len(failed['attempts'])!=1 or failed['attempts'][0]['returncode']==0:
    raise ValueError('original219 compile failure required')
for p,h in failed['payload_sha256'].items():D.checked(Path(p),h)
source=original.read_text()
for a,b in (
    ('all-split-furnace-control-v1','all-split-furnace-control-v2'),
    ('219-bounded-all-split-furnace-control.json','220-bounded-all-split-furnace-control.json'),
    ('076-bounded-all-split-furnace-control.md','077-furnace-original-iid-constructor-repair.md'),
    ('Xoshiro256 prime(seed);','Xoshiro256 prime(seed,pixel,0);'),
    ('        Xoshiro256 iid_rng(seed);\n',''),
    ('        for(uint32_t n=0;n<16384;++n) {','        for(uint32_t n=0;n<16384;++n) {\n            Xoshiro256 iid_rng(seed,pixel,n);'),
    ('Xoshiro256 dark_prime(seed);','Xoshiro256 dark_prime(seed,pixel,0);')):
    source=D.once(source,a,b)
exec(compile(source,str(original)+'#plan077','exec'),{'__name__':'__main__','__file__':__file__})

#!/usr/bin/env python3
"""Plan097: verifier-only V3 construction fix; production traversal unchanged."""
import hashlib
from pathlib import Path
import diagnose_selected_bounce_paths as D

SEALED096=Path(__file__).with_name('diagnose_batched_box_cpu_bvh.py')
EXPECTED096='570c32b6d2ff8885b89182b5ce6ef6480526d3ffa54cdc833e9069b5aeab9ce1'
if hashlib.sha256(SEALED096.read_bytes()).hexdigest()!=EXPECTED096:
    raise ValueError('sealed096 changed')
D.checked(SEALED096)
old_include=D.checked(Path(__file__).with_name('batched_box_cpu_bvh.inc')).decode()
new_include=D.checked(Path(__file__).with_name('batched_box_verifier_repaired.inc')).decode()
old='            for (int a=0;a<3;++a) {box.lo[a]=packet.lo[a][lane];box.hi[a]=packet.hi[a][lane];}'
new=('            box.lo={packet.lo[0][lane],packet.lo[1][lane],packet.lo[2][lane]};\n'
     '            box.hi={packet.hi[0][lane],packet.hi[1][lane],packet.hi[2][lane]};')
if D.once(old_include,old,new)!=new_include or D.once(new_include,new,old)!=old_include:
    raise ValueError('verifier-only include inverse differs')
source=SEALED096.read_text()
edits=[('batched_box_cpu_bvh.inc','batched_box_verifier_repaired.inc'),
       ('batched-box-cpu-bvh-v1','batched-box-verifier-repaired-v1'),
       ('244-batched-box-cpu-bvh-prototype.json','245-batched-box-verifier-repaired-prototype.json'),
       ('096-batched-box-exact-cpu-bvh-prototype.md','097-batched-box-verifier-build-amendment.md')]
revised=source
for a,b in edits:revised=D.once(revised,a,b)
inverse=revised
for a,b in reversed(edits):inverse=D.once(inverse,b,a)
if inverse!=source:raise ValueError('096 driver inverse differs')
exec(compile(revised,str(SEALED096),'exec'),globals())

#!/usr/bin/env python3
"""Plan095 implementation amendment: only ignore SIMD padding lane explicitly."""
import hashlib
from pathlib import Path
import diagnose_selected_bounce_paths as D

SEALED094=Path(__file__).with_name('diagnose_simd_slab_cpu_bvh.py')
EXPECTED094='14b15439c14c369e57f5c9c899561cf135d27fd08bb92c8e53fd1996be0d57b9'
if hashlib.sha256(SEALED094.read_bytes()).hexdigest()!=EXPECTED094:
    raise ValueError('sealed094 changed')
D.checked(SEALED094)
old_include=D.checked(Path(__file__).with_name('simd_slab_cpu_bvh.inc')).decode()
new_include=D.checked(Path(__file__).with_name('simd_slab_neutral_padding.inc')).decode()
old='const auto nan = _mm256_cmp_pd(a, b, _CMP_UNORD_Q);'
new='const auto nan = _mm256_or_pd(_mm256_cmp_pd(a, b, _CMP_UNORD_Q),\n            _mm256_castsi256_pd(_mm256_set_epi64x(-1LL, 0, 0, 0)));'
if D.once(old_include,old,new)!=new_include or D.once(new_include,new,old)!=old_include:
    raise ValueError('padding-only include/inverse differs')
source=SEALED094.read_text()
edits=[('simd_slab_cpu_bvh.inc','simd_slab_neutral_padding.inc'),
       ('simd-slab-cpu-bvh-v1','simd-slab-neutral-padding-v1'),
       ('242-simd-slab-cpu-bvh-prototype.json','243-simd-slab-neutral-padding-prototype.json'),
       ('094-simd-slab-exact-cpu-bvh-prototype.md','095-simd-slab-neutral-padding-amendment.md')]
revised=source
for a,b in edits:revised=D.once(revised,a,b)
inverse=revised
for a,b in reversed(edits):inverse=D.once(inverse,b,a)
if inverse!=source:raise ValueError('094 dispatch inverse differs')
exec(compile(revised,str(SEALED094),'exec'),globals())

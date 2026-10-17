#!/usr/bin/env python3
"""Plan096: batch original box predicates, preserve parent events and query bits."""
import hashlib
import json
from pathlib import Path
import diagnose_selected_bounce_paths as D

BASE=Path(__file__).with_name('diagnose_near_first_cpu_bvh.py')
if hashlib.sha256(BASE.read_bytes()).hexdigest()!='712e9dacebde39d84e988bb362d49a4b2008ba1312478c719b22e215bfae4b2f':
    raise ValueError('sealed090 driver changed')
D.checked(BASE)
prior=json.loads(D.checked(D.RESULTS/'243-simd-slab-neutral-padding-prototype.json'))
profile=json.loads(D.checked(D.RESULTS/'241-posthoc-cpu-profile-inline-attribution.json'))
if not prior['complete'] or prior['execution_promising'] or not profile['complete']:
    raise ValueError('stopped243 and measured hotspot prerequisites required')

def optimize(header):
    first=header.index('class Bvh {');last=header.index('// ---------------------------------------------------------------- integrator',first)
    original=header[first:last]
    legacy=D.once(D.once(original,'class Bvh {','class LegacyBvh {'),'explicit Bvh(','explicit LegacyBvh(')
    old_start=original.index('    template <class Visit>\n    void traverse(')
    old_end=original.index('    const std::vector<Triangle>& tris_;',old_start)
    scalar=original[old_start:old_end]
    renamed=D.once(scalar,'    void traverse(','    void traverse_scalar(')
    addition=D.checked(D.HERE/'batched_box_cpu_bvh.inc').decode()
    edits=[
        (': tris_(tris) {',': tris_(tris)\n#ifdef N010_VERIFY_BVH\n        , legacy_(tris)\n#endif\n    {'),
        ('            build(0, std::uint32_t(tris.size()));\n        }\n    }',
         '            build(0, std::uint32_t(tris.size()));\n        }\n        build_packets();\n    }'),
        ('        return best;', '''#ifdef N010_VERIFY_BVH
        const auto expected=legacy_.closest(ray,tmin,tmax,ignore);++paired_closest_count;
        if(best.tri!=expected.tri||std::memcmp(&best.t,&expected.t,sizeof(double)))
            throw std::runtime_error("batched/original closest identity differs");
#endif
        return best;'''),
        ('        return blocked;', '''#ifdef N010_VERIFY_BVH
        const auto expected=legacy_.occluded(ray,tmax,ignore_a,ignore_b);++paired_occluded_count;
        if(blocked!=expected)throw std::runtime_error("batched/original occlusion identity differs");
#endif
        return blocked;'''),
        ('private:\n    struct Node {','public:\n    mutable uint64_t paired_closest_count{},paired_occluded_count{},paired_slab_count{},paired_cached_slab_count{};\nprivate:\n    struct Node {'),
        (scalar,renamed+addition+'\n'),
        ('    std::vector<Node> nodes_;','    std::vector<Node> nodes_;\n#ifdef N010_VERIFY_BVH\n    LegacyBvh legacy_;\n#endif'),
    ]
    revised=original
    for a,b in edits:revised=D.once(revised,a,b)
    inverse=revised
    for a,b in reversed(edits):inverse=D.once(inverse,b,a)
    if inverse!=original:raise ValueError('batched class inverse differs')
    transformed=D.once(header,original,legacy+revised)
    if D.once(transformed,legacy+revised,original)!=header:raise ValueError('header inverse differs')
    return '#include <immintrin.h>\n'+transformed,dict(class_edit_inverse_exact=True,whole_header_inverse_exact=True,
        original_bvh_sha256=hashlib.sha256(original.encode()).hexdigest(),
        optimized_bvh_sha256=hashlib.sha256(revised.encode()).hexdigest(),
        original_scalar_traversal_retained=True,original_left_first_surviving_parent_and_triangle_order=True,
        packed_group_bytes_at_least=384,packed_index_bytes_per_original_node=4,
        changes=[dict(old=a,new=b) for a,b in edits])

source=BASE.read_text();a=source.index('def optimize(header):');b=source.index('\n\ndef main():',a)
edits=[(source[a:b],'# Plan096 optimize() supplied by wrapper.'),
    ('near-first-cpu-bvh-v1','batched-box-cpu-bvh-v1'),
    ('238-near-first-cpu-bvh-prototype.json','244-batched-box-cpu-bvh-prototype.json'),
    ('090-near-first-exact-cpu-bvh-prototype.md','096-batched-box-exact-cpu-bvh-prototype.md'),
    ('n010-near-first-cpu-bvh-prototype/1','n010-batched-box-cpu-bvh-prototype/1'),
    ('n010_near_first_paired','n010_batched_box_paired'),
    ('n010_near_first_exporter','n010_batched_box_exporter'),
    ("flags = ['c++', '-std=c++20'","flags = ['c++', '-mavx2', '-std=c++20'"),
    ('<<oracle.bvh().paired_occluded_count',
     '<<oracle.bvh().paired_occluded_count<<",\\\\\\\"paired_slabs\\\\\\\":"<<oracle.bvh().paired_slab_count<<",\\\\\\\"paired_cached_slabs\\\\\\\":"<<oracle.bvh().paired_cached_slab_count'),
    ("if counts['paired_closest'] <= 0 or counts['paired_occluded'] <= 0:",
     "if any(counts[k] <= 0 for k in ('paired_closest','paired_occluded','paired_slabs','paired_cached_slabs')):"),
]
revised=source
for a,b in edits:revised=D.once(revised,a,b)
inverse=revised
for a,b in reversed(edits):inverse=D.once(inverse,b,a)
if inverse!=source:raise ValueError('driver inverse differs')
exec(compile(revised,str(BASE),'exec'),globals())

#!/usr/bin/env python3
"""Plan094: SIMD original-order box predicate, original query/payload pairing."""
import hashlib
from pathlib import Path
import diagnose_selected_bounce_paths as D

BASE = Path(__file__).with_name('diagnose_near_first_cpu_bvh.py')
BASE_SHA = '712e9dacebde39d84e988bb362d49a4b2008ba1312478c719b22e215bfae4b2f'
if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
    raise ValueError('sealed090 execution driver changed')
D.checked(BASE)
profile = __import__('json').loads(D.checked(D.RESULTS/'241-posthoc-cpu-profile-inline-attribution.json'))
if not profile['complete'] or not profile['debug_text_and_addresses_exact']:
    raise ValueError('actual measured inline hotspot attribution required')

def optimize(header):
    start=header.index('class Bvh {');end=header.index('// ---------------------------------------------------------------- integrator',start)
    original=header[start:end]
    legacy=D.once(D.once(original,'class Bvh {','class LegacyBvh {'),'explicit Bvh(','explicit LegacyBvh(')
    addition=D.checked(D.HERE/'simd_slab_cpu_bvh.inc').decode()
    edits=[
        (': tris_(tris) {',': tris_(tris)\n#ifdef N010_VERIFY_BVH\n        , legacy_(tris)\n#endif\n    {'),
        ('            build(0, std::uint32_t(tris.size()));\n        }\n    }',
         '''            build(0, std::uint32_t(tris.size()));
        }
        packed_boxes_.resize(nodes_.size());
        for (size_t i=0;i<nodes_.size();++i) {
            for (int a=0;a<3;++a) {
                packed_boxes_[i].lo[a]=nodes_[i].box.lo[a];
                packed_boxes_[i].hi[a]=nodes_[i].box.hi[a];
            }
            packed_boxes_[i].lo[3]=packed_boxes_[i].hi[3]=0;
        }
    }'''),
        ('        return best;', '''#ifdef N010_VERIFY_BVH
        const auto expected=legacy_.closest(ray,tmin,tmax,ignore);++paired_closest_count;
        if(best.tri!=expected.tri||std::memcmp(&best.t,&expected.t,sizeof(double)))
            throw std::runtime_error("SIMD/original closest identity differs");
#endif
        return best;'''),
        ('        return blocked;', '''#ifdef N010_VERIFY_BVH
        const auto expected=legacy_.occluded(ray,tmax,ignore_a,ignore_b);++paired_occluded_count;
        if(blocked!=expected)throw std::runtime_error("SIMD/original occlusion identity differs");
#endif
        return blocked;'''),
        ('private:\n    struct Node {','public:\n    mutable uint64_t paired_closest_count{},paired_occluded_count{},paired_slab_count{};\nprivate:\n    struct Node {'),
        ('    template <class Visit>\n    void traverse(',addition+'\n    template <class Visit>\n    void traverse('),
        ('        std::uint32_t stack[128];', '''        const auto origin4=_mm256_set_pd(0,ray.origin.z,ray.origin.y,ray.origin.x);
        const auto inverse4=_mm256_set_pd(0,inv.z,inv.y,inv.x);
        std::uint32_t stack[128];'''),
        ('            if (!slab(node.box, ray.origin, inv, tmin, tmax)) continue;', '''            const bool intersects=slab_simd(packed_boxes_[ni],origin4,inverse4,tmin,tmax);
#ifdef N010_VERIFY_BVH
            ++paired_slab_count;
            if(intersects!=slab(node.box,ray.origin,inv,tmin,tmax))
                throw std::runtime_error("SIMD/original visited box predicate differs");
#endif
            if(!intersects)continue;'''),
        ('    std::vector<Node> nodes_;','    std::vector<Node> nodes_;\n#ifdef N010_VERIFY_BVH\n    LegacyBvh legacy_;\n#endif'),
    ]
    revised=original
    for a,b in edits:revised=D.once(revised,a,b)
    inverse=revised
    for a,b in reversed(edits):inverse=D.once(inverse,b,a)
    if inverse!=original:raise ValueError('SIMD class inverse differs')
    combined=legacy+revised
    transformed=D.once(header,original,combined)
    if D.once(transformed,combined,original)!=header:raise ValueError('SIMD header inverse differs')
    return '#include <immintrin.h>\n'+transformed,dict(class_edit_inverse_exact=True,
        whole_header_inverse_exact=True,original_bvh_sha256=hashlib.sha256(original.encode()).hexdigest(),
        optimized_bvh_sha256=hashlib.sha256(revised.encode()).hexdigest(),
        original_left_first_node_and_triangle_order=True,original_watertight_intersection_unchanged=True,
        packed_box_bytes_per_node=64,changes=[dict(old=a,new=b) for a,b in edits])

source=BASE.read_text()
a=source.index('def optimize(header):');b=source.index('\n\ndef main():',a)
old_optimize=source[a:b]
edits=[
    (old_optimize,'# Plan094 optimize() is defined in the wrapper.'),
    ('near-first-cpu-bvh-v1','simd-slab-cpu-bvh-v1'),
    ('238-near-first-cpu-bvh-prototype.json','242-simd-slab-cpu-bvh-prototype.json'),
    ('090-near-first-exact-cpu-bvh-prototype.md','094-simd-slab-exact-cpu-bvh-prototype.md'),
    ('n010-near-first-cpu-bvh-prototype/1','n010-simd-slab-cpu-bvh-prototype/1'),
    ('n010_near_first_paired','n010_simd_slab_paired'),
    ('n010_near_first_exporter','n010_simd_slab_exporter'),
    ("flags = ['c++', '-std=c++20'", "flags = ['c++', '-mavx2', '-std=c++20'"),
    ('<<oracle.bvh().paired_occluded_count', '<<oracle.bvh().paired_occluded_count<<",\\\\\\\"paired_slabs\\\\\\\":"<<oracle.bvh().paired_slab_count'),
    ("if counts['paired_closest'] <= 0 or counts['paired_occluded'] <= 0:",
     "if counts['paired_closest'] <= 0 or counts['paired_occluded'] <= 0 or counts['paired_slabs'] <= 0:"),
]
revised=source
for a,b in edits:
    if revised.count(a)!=1:raise ValueError('nonunique execution edit: '+a[:60])
    revised=revised.replace(a,b)
inverse=revised
for a,b in reversed(edits):
    if inverse.count(b)!=1:raise ValueError('nonunique execution inverse')
    inverse=inverse.replace(b,a)
if inverse!=source:raise ValueError('execution driver inverse differs')
exec(compile(revised,str(BASE),'exec'),globals())

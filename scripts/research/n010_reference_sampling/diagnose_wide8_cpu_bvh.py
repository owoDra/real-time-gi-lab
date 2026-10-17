#!/usr/bin/env python3
"""Plan102: isolated eight-wide topology, original-query identity and fixed cost."""
import hashlib
import json
from pathlib import Path
import diagnose_selected_bounce_paths as D

BASE = Path(__file__).with_name('diagnose_near_first_cpu_bvh.py')
if hashlib.sha256(BASE.read_bytes()).hexdigest() != '712e9dacebde39d84e988bb362d49a4b2008ba1312478c719b22e215bfae4b2f':
    raise ValueError('sealed090 driver changed')
D.checked(BASE)
prior = json.loads(D.checked(D.RESULTS / '245-batched-box-verifier-repaired-prototype.json'))
if not prior['complete'] or prior['execution_promising']:
    raise ValueError('terminal stopped245 required')
for stem in ('252-all-split-original-sealed-dark-full-control.json',
             '253-all-split-original-sealed-lit-full-control.json'):
    control = json.loads(D.checked(D.RESULTS / stem))
    if not control['complete'] or not control['all_pass']:
        raise ValueError('finish original sealed controls before separate execution prototype')
cpu_flags = [line.split(':', 1)[1].split() for line in
             Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('flags')]
if not cpu_flags or not all('avx512f' in flags for flags in cpu_flags):
    raise ValueError('registered AVX512F CPU capability missing')


def optimize(header):
    first = header.index('class Bvh {')
    last = header.index('// ---------------------------------------------------------------- integrator', first)
    original = header[first:last]
    legacy = D.once(D.once(original, 'class Bvh {', 'class LegacyBvh {'), 'explicit Bvh(', 'explicit LegacyBvh(')
    start = original.index('    template <class Visit>\n    void traverse(')
    end = original.index('    const std::vector<Triangle>& tris_;', start)
    scalar = original[start:end]
    renamed = D.once(scalar, '    void traverse(', '    void traverse_scalar(')
    addition = D.checked(D.HERE / 'wide8_cpu_bvh.inc').decode()
    edits = [
        (': tris_(tris) {', ': tris_(tris)\n#ifdef N010_VERIFY_BVH\n        , legacy_(tris)\n#endif\n    {'),
        ('            build(0, std::uint32_t(tris.size()));\n        }\n    }',
         '            build(0, std::uint32_t(tris.size()));\n        }\n        build_wide();\n    }'),
        ('        return best;', '''#ifdef N010_VERIFY_BVH
        const auto expected=legacy_.closest(ray,tmin,tmax,ignore);++paired_closest_count;
        if(best.tri!=expected.tri||std::memcmp(&best.t,&expected.t,sizeof(double)))
            throw std::runtime_error("wide/original closest identity differs");
#endif
        return best;'''),
        ('        return blocked;', '''#ifdef N010_VERIFY_BVH
        const auto expected=legacy_.occluded(ray,tmax,ignore_a,ignore_b);++paired_occluded_count;
        if(blocked!=expected)throw std::runtime_error("wide/original occlusion identity differs");
#endif
        return blocked;'''),
        ('private:\n    struct Node {',
         'public:\n    mutable uint64_t paired_closest_count{},paired_occluded_count{},paired_slab_count{},paired_cached_slab_count{};\nprivate:\n    struct Node {'),
        (scalar, renamed + addition + '\n'),
        ('    std::vector<Node> nodes_;', '    std::vector<Node> nodes_;\n#ifdef N010_VERIFY_BVH\n    LegacyBvh legacy_;\n#endif'),
    ]
    revised = original
    for old, new in edits:
        revised = D.once(revised, old, new)
    inverse = revised
    for old, new in reversed(edits):
        inverse = D.once(inverse, new, old)
    if inverse != original:
        raise ValueError('wide class inverse differs')
    changed = D.once(header, original, legacy + revised)
    if D.once(changed, legacy + revised, original) != header:
        raise ValueError('wide whole-header inverse differs')
    return '#include <immintrin.h>\n' + changed, dict(
        class_edit_inverse_exact=True, whole_header_inverse_exact=True,
        original_bvh_sha256=hashlib.sha256(original.encode()).hexdigest(),
        optimized_bvh_sha256=hashlib.sha256(revised.encode()).hexdigest(),
        original_scalar_traversal_retained=True,
        separate_intrinsics_include_added=True,
        original_triangle_build_bounds_leaf_order_and_intersection_retained=True,
        flattened_topology='breadth-first expansion to <=8 frontier entries; original DFS lane order',
        runtime_parent_containment_and_leaf_coverage_guards=True,
        changes=[dict(old=a, new=b) for a, b in edits])


WIDE_MAIN_TAIL = r'''    out<<"]\n";
    std::cout<<"{\"paired_closest\":"<<oracle.bvh().paired_closest_count
             <<",\"paired_occluded\":"<<oracle.bvh().paired_occluded_count
             <<",\"paired_boxes\":"<<oracle.bvh().paired_slab_count
             <<",\"paired_cached\":"<<oracle.bvh().paired_cached_slab_count<<"}\n";
    return out?0:5;'''

source = BASE.read_text()
start = source.index('def optimize(header):')
end = source.index('\n\ndef main():', start)
tail_start = source.index("    new_tail = '''", end)
tail_end = source.index('    paired_main = ', tail_start)
edits = [
    (source[start:end], '# Plan102 optimize() supplied by the wrapper.'),
    (source[tail_start:tail_end], '    new_tail = WIDE_MAIN_TAIL\n'),
    ('near-first-cpu-bvh-v1', 'wide8-cpu-bvh-v1'),
    ('238-near-first-cpu-bvh-prototype.json', '254-wide8-cpu-bvh-prototype.json'),
    ('090-near-first-exact-cpu-bvh-prototype.md', '102-wide8-exact-cpu-bvh-prototype.md'),
    ('n010-near-first-cpu-bvh-prototype/1', 'n010-wide8-cpu-bvh-prototype/1'),
    ('n010_near_first_paired', 'n010_wide8_paired'),
    ('n010_near_first_exporter', 'n010_wide8_exporter'),
    ("flags = ['c++', '-std=c++20'", "flags = ['c++', '-mavx512f', '-std=c++20'"),
    ('cpu_limit_seconds=220, elapsed_limit_seconds=300', 'cpu_limit_seconds=360, elapsed_limit_seconds=480'),
    ('resource.setrlimit(resource.RLIMIT_CPU, (220,) * 2)', 'resource.setrlimit(resource.RLIMIT_CPU, (360,) * 2)'),
    ('timeout=300, preexec_fn=limits', 'timeout=480, preexec_fn=limits'),
    ("actual['cpu'] != [220] * 2", "actual['cpu'] != [360] * 2"),
    ("if counts['paired_closest'] <= 0 or counts['paired_occluded'] <= 0:",
     "if any(counts[k] <= 0 for k in ('paired_closest','paired_occluded','paired_boxes','paired_cached')):"),
]
revised = source
for old, new in edits:
    revised = D.once(revised, old, new)
inverse = revised
for old, new in reversed(edits):
    inverse = D.once(inverse, new, old)
if inverse != source:
    raise ValueError('whole090 driver inverse differs')
exec(compile(revised, str(BASE), 'exec'), globals())

#!/usr/bin/env python3
"""N007 read-only source-contract audit and analytic shadow demonstration.

This is a CPU diagnostic of current source semantics, NOT a faithful replay of
historic GPU binaries or proof about a particular Sponza PFM pixel.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SOURCE = Path('src/research/lane_n_end_to_end_renderer')
SHADERS = Path('shaders/research/lane_n_end_to_end_renderer')


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def shadow_triangle_hit(origin, direction, max_t, tri):
    """CPU Moller-Trumbore, two-sided, t in (1e-4,max_t)."""
    a,b,c = tri
    e1, e2 = sub(b,a), sub(c,a)
    p = cross(direction,e2)
    det = dot(e1,p)
    if abs(det)<1e-8:
        return False
    inv=1.0/det
    v=sub(origin,a)
    u=dot(v,p)*inv
    if not 0<=u<=1:
        return False
    q=cross(v,e1)
    v2=dot(direction,q)*inv
    if v2<0 or u+v2>1:
        return False
    t=dot(e2,q)*inv
    return 1e-4<=t<=max_t


def lambert_light(position, normal, light, radius, blockers=()):
    """Controlled illustration of CPU shadowed vs GPU probe unshadowed form."""
    lv=sub(light,position)
    dist2=dot(lv,lv)
    if dist2<=1e-12:
        return (0.0,0.0,False)
    d=math.sqrt(dist2)
    direction=tuple(x/d for x in lv)
    cos=max(0.0,dot(normal,direction))
    raw=cos*(radius*radius)/(radius*radius+dist2)/math.pi
    # Epsilon is an illustrative, finite ray origin offset, not a recreation
    # of source-camera-dependent epsilon values.
    shifted=tuple(position[i]+normal[i]*8e-4 for i in range(3))
    blocked=any(shadow_triangle_hit(shifted,direction,d-0.002,tri) for tri in blockers)
    return (0.0 if blocked else raw,raw,blocked)


def source_audit(root: Path):
    root=root.resolve()
    path={
        'cmake': root/SOURCE/'CMakeLists.txt',
        'runtime': root/SOURCE/'n001_runtime.cpp',
        'cpu': root/SOURCE/'n001_reference.cpp',
        'radiance': root/SHADERS/'n001_physical_radiance.comp.glsl',
        'gpu_software': root/SHADERS/'n003_composite_software.comp.glsl',
        'gpu_hwrt': root/SHADERS/'n001_composite.comp.glsl',
        'legacy_hash': root/SHADERS/'imported/integration/i001_radiance.comp.glsl',
    }
    s={k:v.read_text(encoding='utf-8') for k,v in path.items()}
    checks={
        'compiled_radiance_is_physical_glsl': bool(re.search(
            r'add_compute_shader\(\s*i001_radiance\s+shaders/research/lane_n_end_to_end_renderer/n001_physical_radiance\.comp\.glsl\s*\)',s['cmake'])),
        'runtime_uses_compiled_i001_spv_twice': s['runtime'].count('"i001_radiance.spv"')==2,
        'cpu_direct_shadow_bvh': 'const auto blocker = bvh.trace(' in s['cpu'],
        'cpu_primary_center_ray': 'float(x) + 0.5F' in s['cpu'] and 'float(y) + 0.5F' in s['cpu'],
        'cpu_global_p99_stop': bool(re.search(r'result\.converged\s*=\s*delta\.p99_abs\s*<=',s['cpu'])),
        'gpu_probe_lacks_shadow_query': 'point_light_lambert' in s['radiance'] and all(
            x not in s['radiance'] for x in ('visible_to_light','rayQuery','bvh.trace','trace(')),
        'gpu_software_direct_shadow': bool(re.search(r'visible_to_light\(\s*position,\s*normal,\s*light_direction,\s*distance_to_light\s*\)',s['gpu_software'])),
        'gpu_software_indirect_lookup': 'indirect += lookup_probe(' in s['gpu_software'],
        'gpu_hwrt_direct_shadow': 'visible_to_light(position, normal, light_direction, distance_to_light)' in s['gpu_hwrt'],
        'old_hash_shader_exists_but_not_compiled_under_i001': 'deterministic_radiance' in s['legacy_hash'] and not bool(re.search(
            r'add_compute_shader\(\s*i001_radiance\s+shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_radiance',s['cmake'])),
    }
    # Synthetic occlusion geometry: a horizontal blocker separating the point
    # and point light. Normal faces the light, so NdotL is positive.
    blocker=((-1.0,1.0,-1.0),(1.0,1.0,-1.0),(0.0,1.0,1.0))
    lit=lambert_light((0,0,0),(0,1,0),(0,2,0),0.5)
    occluded=lambert_light((0,0,0),(0,1,0),(0,2,0),0.5,(blocker,))
    return {
        'schema_version':1,
        'purpose':'CPU source-contract and controlled geometry hypothesis test only',
        'no_gpu_execution':True,
        'no_historic_pfm_read':True,
        'checks':checks,
        'all_source_checks_pass':all(checks.values()),
        'analytical_occluder_example':{
            'lit_shadowed':lit[0], 'lit_unshadowed':lit[1],
            'blocked_shadowed':occluded[0], 'blocked_unshadowed':occluded[1],
            'occlusion_detected':occluded[2],
            'demonstrates_possible_model_mismatch':occluded[0]==0 and occluded[1]>0 and lit[0]>0,
        },
        'historic_m3b_root_cause_proven':False,
        'reference_physical_correctness_proven':False,
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    ap.add_argument('--output',type=Path,default=Path('out/research/n007-reference-validity/p1a-cpu-source-contract.json'))
    args=ap.parse_args()
    result=source_audit(args.root)
    dest=args.output.resolve()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'checks_pass':sum(result['checks'].values()),'checks_total':len(result['checks']),
                      'analytical_example':result['analytical_occluder_example'],
                      'historic_m3b_root_cause_proven':False,'output':str(dest)},indent=2))
    return 0 if result['all_source_checks_pass'] and result['analytical_occluder_example']['demonstrates_possible_model_mismatch'] else 1

if __name__=='__main__':
    raise SystemExit(main())

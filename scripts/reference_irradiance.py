#!/usr/bin/env python3
"""Reference indirect irradiance with Mitsuba 3 (llvm_ad_rgb), for the radiance-cascade comparisons.

Computes, at the first surface seen through each pixel, the quantity the renderer's GI pass outputs:
E = integral over the hemisphere of the shading normal (turned to face the camera) of L_in cos, where L_in is
one bounce of sun light: a ray that hits a surface returns albedo / pi * sunE * max(n . sun, 0) * V(sun), and a
ray that hits nothing returns the sky radiance. This is the renderer's transport model (one bounce, sun only at
the hit, sky on escape) with exact visibility; differences against it are the radiance cascades' and the
interval tracers' errors. Alpha-masked materials are treated as holes where opacity < cutoff (as the
renderer's alpha test). Normal maps are not applied (the renderer's G-buffer applies them).
S3: hits on toon materials (vertex attribute toon = 1) return the emission-side operator of src/core/style.ts
instead of the Lambert term: sat(albedo) / pi * sunE * ramp(n.l * V) (the emission-side proxy).

Usage: python scripts/reference_irradiance.py box/out/mitsuba/sponza [--spp 256] [--width 960] [--height 540]
         [--sky r,g,b] [--seed N] [--out FILE.pfm]
Needs DRJIT_LIBLLVM_PATH (see docs/spec/10-evaluation.md).
"""
import argparse
import json
import math
import os
import time

import drjit as dr
import mitsuba as mi

mi.set_variant("llvm_ad_rgb")

ap = argparse.ArgumentParser()
ap.add_argument("scene_dir")
ap.add_argument("--spp", type=int, default=256)
ap.add_argument("--width", type=int, default=960)
ap.add_argument("--height", type=int, default=540)
ap.add_argument("--sky", default="0,0,0")
ap.add_argument("--out", default=None)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--albedo", action="store_true", help="write the first-hit albedo instead (orientation check)")
a = ap.parse_args()
desc = json.load(open(os.path.join(a.scene_dir, "scene.json")))
sky = [float(x) for x in a.sky.split(",")]

# Textured materials: the base-colour factor is applied in the integrator (to hits with vertex attribute tex = 1),
# so it must be the same for all. Untextured materials carry their colour as the reflectance.
tex_factors = {tuple(m["factor"]) for m in desc["materials"] if m["texture"]}
assert len(tex_factors) <= 1, f"textured materials with different base colour factors: {tex_factors}"
tex_factor = list(tex_factors.pop()) if tex_factors else [1.0, 1.0, 1.0]

scene_dict = {"type": "scene"}
for i, m in enumerate(desc["materials"]):
    if m["texture"]:
        refl = {"type": "bitmap", "filename": os.path.join(a.scene_dir, m["texture"])}
    else:
        refl = {"type": "rgb", "value": m["factor"]}
    bsdf = {"type": "twosided", "bsdf": {"type": "diffuse", "reflectance": refl}}
    if m["opacity"]:
        bsdf = {"type": "mask", "opacity": {"type": "bitmap", "filename": os.path.join(a.scene_dir, m["opacity"]), "raw": True}, "bsdf": bsdf}
    scene_dict[f"m{i}"] = {"type": "ply", "filename": os.path.join(a.scene_dir, m["mesh"]), "bsdf": bsdf, "face_normals": False}
cam = desc["camera"]
scene_dict["sensor"] = {
    "type": "perspective", "fov_axis": "y", "fov": cam["fovYDeg"], "near_clip": cam["near"],
    "to_world": mi.ScalarTransform4f().look_at(origin=cam["eye"], target=cam["target"], up=[0, 1, 0]),
    "film": {"type": "hdrfilm", "width": a.width, "height": a.height, "rfilter": {"type": "box"}, "pixel_format": "rgb"},
    "sampler": {"type": "independent", "sample_count": a.spp},
}
sd = desc["sunDir"]
sun_dir = mi.Vector3f([c / math.sqrt(sum(x * x for x in sd)) for c in sd])
sun_e = mi.Color3f(desc["sunE"])
cutoff = 0.5
MASK_STEPS = 12


def intersect(scene, ray, active, primary=False):
    """Closest hit, stepping through alpha-masked texels below the cutoff. Primary rays also step through
    back faces of single-sided materials, which the G-buffer culls (the tracers and the shadow map do not)."""
    si = scene.ray_intersect(ray, active)
    for _ in range(MASK_STEPS):
        bsdf = si.bsdf(ray)
        nt = bsdf.eval_null_transmission(si, active & si.is_valid())
        hole = active & si.is_valid() & (nt[0] > 1.0 - cutoff)
        if primary:
            ds = si.shape.eval_attribute_1("vertex_ds", si, active & si.is_valid())
            hole |= active & si.is_valid() & (ds < 0.5) & (dr.dot(si.n, ray.d) > 0)
        if not dr.any(hole):
            break
        ray = mi.Ray3f(si.spawn_ray(ray.d))
        si2 = scene.ray_intersect(ray, hole)
        si = dr.select(hole, si2, si)
    return si


TOON = desc.get("toon")
has_toon = any(m.get("toon") for m in desc["materials"])


def toon_sun(alb, x):
    l = 0.2126 * alb[0] + 0.7152 * alb[1] + 0.0722 * alb[2]
    sat = dr.clip(l + TOON["saturation"] * (alb - l), 0.0, 1.0)
    ramp = dr.select(x > TOON["t1"], 1.0, dr.select(x > TOON["t0"], TOON["mid"], 0.0))
    return sat / math.pi * sun_e * ramp


def albedo(si, ray, active):
    tex = si.shape.eval_attribute_1("vertex_tex", si, active) > 0.5
    return si.bsdf(ray).eval_diffuse_reflectance(si, active) * dr.select(tex, mi.Color3f(tex_factor), mi.Color3f(1.0))


def facing(n, d):
    return dr.select(dr.dot(n, d) > 0, -n, n)


class RefIrradiance(mi.SamplingIntegrator):
    def __init__(self, props):
        mi.SamplingIntegrator.__init__(self, props)

    def sample(self, scene, sampler, ray, medium=None, active=True):
        ray = mi.Ray3f(ray)
        si = intersect(scene, ray, mi.Bool(active), primary=True)
        valid = si.is_valid()
        ctx = mi.BSDFContext()
        if a.albedo:
            alb = albedo(si, ray, valid)
            return dr.select(valid, alb, 0.0), valid, []
        n1 = facing(si.sh_frame.n, ray.d)
        frame = mi.Frame3f(n1)
        d = frame.to_world(mi.warp.square_to_cosine_hemisphere(sampler.next_2d(valid)))
        ray2 = mi.Ray3f(si.p + n1 * 1e-3 * (1 + dr.max(dr.abs(si.p))), d)
        si2 = intersect(scene, ray2, valid)
        hit = valid & si2.is_valid()
        n2 = facing(si2.n, d)
        ndl = dr.maximum(dr.dot(n2, sun_dir), 0.0)
        alb = albedo(si2, ray2, hit)
        lit = hit & (ndl > 0)
        sray = mi.Ray3f(si2.p + n2 * 1e-3 * (1 + dr.max(dr.abs(si2.p))), sun_dir)
        sh = intersect(scene, sray, lit)
        vis = lit & ~sh.is_valid()
        l_hit = dr.select(vis, alb / math.pi * sun_e * ndl, 0.0)
        if has_toon:
            toon = hit & (si2.shape.eval_attribute_1("vertex_toon", si2, hit) > 0.5)
            l_hit = dr.select(toon, toon_sun(alb, dr.select(vis, ndl, 0.0)), l_hit)
        l_in = dr.select(hit, l_hit, dr.select(valid, mi.Color3f(sky), 0.0))
        # Cosine-weighted sampling: E = pi * L_in.
        return l_in * math.pi, valid, []


mi.register_integrator("refirr", lambda props: RefIrradiance(props))
scene_dict["integrator"] = {"type": "refirr"}
t0 = time.time()
scene = mi.load_dict(scene_dict)
print(f"loaded {len(desc['materials'])} meshes in {time.time() - t0:.1f} s", flush=True)
t0 = time.time()
img = mi.render(scene, spp=a.spp, seed=a.seed)
out = a.out or os.path.join(a.scene_dir, f"E{'-albedo' if a.albedo else ''}-{a.width}x{a.height}-{a.spp}spp-sky{a.sky.replace(',', '_')}-seed{a.seed}.pfm")
mi.Bitmap(img).write(out)
print(f"rendered {a.width}x{a.height} at {a.spp} spp in {time.time() - t0:.1f} s -> {out}", flush=True)

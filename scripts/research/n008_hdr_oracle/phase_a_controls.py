#!/usr/bin/env python3
"""N008 Phase A physically known controls A1-A10 (protocol experiments/001).

Expected values come from closed forms / quadrature on analytic primitives in
this file; the oracle is only executed and read back. Gates are the frozen
preregistered ones; do not edit them to make a control pass."""
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

np.seterr(divide="ignore", invalid="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import n008lib as L  # noqa: E402

PI = math.pi
MARGIN = 1e-6          # world units, boundary exclusion
MARGIN_MAX_FRACTION = 0.05
EXACT_F64 = 1e-9
EXACT_F32 = 1e-6
SEEDS = L.N007_SEEDS
DET_SPP = 64           # deterministic (centre) controls
STAT_SPP = 1024        # statistical controls, per seed

GRAY = (0.8, 0.8, 0.8)


# --------------------------------------------------------------------------- gates
class Result:
    def __init__(self, cid, title):
        self.cid, self.title = cid, title
        self.checks, self.runs, self.notes = [], [], {}

    def check(self, name, ok, **detail):
        self.checks.append({"name": name, "pass": bool(ok), **{k: _jsonable(v) for k, v in detail.items()}})
        return ok

    @property
    def passed(self):
        return all(c["pass"] for c in self.checks) and all(r["geometry_hash_match"] for r in self.runs)

    def to_json(self):
        return {"id": self.cid, "title": self.title, "pass": self.passed, "checks": self.checks,
                "runs": [{k: r[k] for k in ("name", "scene_sha256", "geometry_sha256", "geometry_hash_match", "triangles",
                                             "spp", "seeds", "run_counters")} for r in self.runs],
                "notes": {k: _jsonable(v) for k, v in self.notes.items()}}


def _jsonable(v):
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, np.ndarray):
        return [_jsonable(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def render(res: Result, scene: L.Scene, out: Path, name: str, spp: int):
    meta = L.run_oracle(scene, out, name, seeds=SEEDS, spp=spp)
    meta["name"] = name
    meta["run_counters"] = [{k: r[k] for k in ("seed", "primary_hits", "shadow_tests", "shadow_blocked", "backface_absorbed")}
                            for r in meta["runs"]]
    res.runs.append(meta)
    data = L.pooled(meta)
    data["meta"] = meta
    return data


def check_margin(res, valid):
    frac = 1.0 - float(valid.mean())
    return res.check("margin_fraction<=0.05", frac <= MARGIN_MAX_FRACTION, margin_fraction=frac,
                     margin_pixels=int((~valid).sum()))


def check_exact(res, label, data, expected: dict, valid, components=L.COMPONENTS):
    """expected: component -> HxWx3 array (missing components expected zero).
    Only `components` are gated; 'total' is gated only when all parts are known."""
    ok_all = True
    for k, comp in enumerate(L.COMPONENTS):
        if comp not in components:
            continue
        e = expected.get(comp)
        if e is None:
            e = sum(expected.get(c, 0.0) for c in L.COMPONENTS[:3]) if comp == "total" else np.zeros_like(data["mean"][..., 0, :])
        e = np.broadcast_to(e, data["mean"][..., k, :].shape)
        worst64, fails64, worst32, fails32 = 0.0, 0, 0.0, 0
        for run in data["per_seed"]:
            m = run["mean"][..., k, :]
            err = np.abs(m - e)
            zero = e == 0
            bad = np.where(zero, m != 0, err > EXACT_F64 * np.abs(e)) & valid[..., None]
            fails64 += int(bad.sum())
            rel = np.where(zero, np.where(m != 0, np.inf, 0.0), err / np.where(zero, 1, np.abs(e)))
            worst64 = max(worst64, float(np.max(np.where(valid[..., None], rel, 0.0))))
        for r in data["meta"]["runs"]:
            m = L.read_pfm(Path(r["prefix"] + f".{comp}.pfm"))
            e32 = e
            err = np.abs(m - e32)
            zero = e32 == 0
            bad = np.where(zero, m != 0, err > EXACT_F32 * np.abs(e32)) & valid[..., None]
            fails32 += int(bad.sum())
            rel = np.where(zero, np.where(m != 0, np.inf, 0.0), err / np.where(zero, 1, np.abs(e32)))
            worst32 = max(worst32, float(np.max(np.where(valid[..., None], rel, 0.0))))
        ok = fails64 == 0 and fails32 == 0
        ok_all &= ok
        res.check(f"{label}:{comp}:exact", ok, f64_failures=fails64, f64_worst_rel=worst64,
                  f32_failures=fails32, f32_worst_rel=worst32)
    return ok_all


def check_zero_all(res, label, data):
    nonzero = 0
    for run in data["per_seed"]:
        nonzero += int(np.count_nonzero(run["mean"]))
        nonzero += int(np.count_nonzero(run["m2"]))  # every sample zero <=> second moment zero
    for r in data["meta"]["runs"]:
        for comp in L.COMPONENTS:
            nonzero += int(np.count_nonzero(L.read_pfm(Path(r["prefix"] + f".{comp}.pfm"))))
    return res.check(f"{label}:all_samples_zero", nonzero == 0, nonzero_values=nonzero)


def check_stat(res, label, data, comp, expected, mask, tau, allowance=None):
    """Preregistered S gate: region per channel and per-pixel 99.9%."""
    k = L.COMPONENTS.index(comp)
    m = data["mean"][..., k, :]
    se = data["se"][..., k, :]
    e = np.broadcast_to(expected, m.shape)
    a = np.zeros_like(m) if allowance is None else np.broadcast_to(allowance, m.shape)
    sel = mask
    npx = int(sel.sum())
    region = []
    ok = npx > 0
    for c in range(3):
        mr = float(m[..., c][sel].mean()); er = float(e[..., c][sel].mean())
        ser = float(np.sqrt(np.sum(se[..., c][sel] ** 2)) / npx)
        ar = float(a[..., c][sel].mean())
        bound = 5 * ser + tau * abs(er) + ar
        cok = abs(mr - er) <= bound
        ok &= cok
        region.append({"channel": c, "mean": mr, "expected": er, "se": ser, "abs_diff": abs(mr - er), "bound": bound,
                       "rel_diff": abs(mr - er) / abs(er) if er else None,
                       "min_detectable_rel": bound / abs(er) if er else None, "pass": cok})
    pix_ok = np.abs(m - e) <= 6 * se + tau * np.abs(e) + a
    frac = float(pix_ok[sel].mean()) if npx else 0.0
    ok &= frac >= 0.999
    z = (m - e) / np.maximum(6 * se + tau * np.abs(e) + a, 1e-300)
    return res.check(f"{label}:{comp}:statistical", ok, pixels=npx, region=region, pixel_pass_fraction=frac,
                     worst_pixel_ratio_to_bound=float(np.max(np.abs(z[sel]))) if npx else None)


# --------------------------------------------------------------------------- shared geometry
def lambert_point(rho, intensity, p, n, light, falloff="inverse_square", s=0.0):
    l = np.asarray(light, float) - p
    d2 = np.sum(l * l, axis=-1)
    d = np.sqrt(d2)
    cos = np.sum(n * l, axis=-1) / d
    g = np.where(cos > 0, cos / (d2 if falloff == "inverse_square" else s * s + d2), 0.0)
    return np.asarray(rho)[None, None, :] / PI * np.asarray(intensity)[None, None, :] * g[..., None]


def nearest(hits):
    """hits: list of t arrays -> (index of nearest, t)."""
    T = np.stack(hits)
    return np.argmin(T, axis=0), np.min(T, axis=0)


def face_forward(n, d):
    n = np.broadcast_to(np.asarray(n, float), d.shape)
    s = np.where(np.sum(n * d, axis=-1) < 0, 1.0, -1.0)
    return n * s[..., None]


# --------------------------------------------------------------------------- controls
A1_RECTS = [("e1", (1.0, 2.0, 3.0), (0.4, 0.3, -4.0), (1.2, 0, 0), (0, 0.9, 0)),
            ("e2", (3.0, 1.0, 0.5), (-1.6, -1.2, -4.0), (0.6, 0, 0), (0, 0.6, 0)),
            ("e3", (5.0, 5.0, 5.0), (-1.6, 0.3, -4.0), (0, 0.9, 0), (0.6, 0, 0))]  # e3 back-facing (-Z)


def build_a1(sampling="center"):
    sc = L.Scene(L.Camera((0, 0, 0), (0, 0, -1), tan_x=0.5, tan_y=0.375), max_bounces=1, sampling=sampling)
    for name, le, p0, eu, ev in A1_RECTS:
        sc.material(name, (0, 0, 0), le)
        sc.quad(name, p0, eu, ev)
    return sc, A1_RECTS


def control_a1(out):
    res = L_result("A1", "camera/handedness projection with front- and back-facing emitters")
    sc, rects = build_a1()
    cam = sc.camera
    o, d = L.camera_rays(cam, sc.width, sc.height)
    ts, margins, normals = zip(*(L.ray_parallelogram(o, d, p0, eu, ev) for _, _, p0, eu, ev in rects))
    idx, t = nearest(list(ts))
    emission = np.zeros(d.shape)
    for i, (_, le, *_r) in enumerate(rects):
        front = (d @ normals[i]) < 0
        emission[(idx == i) & np.isfinite(t) & front] = le
    valid = np.all(np.stack([np.abs(m) >= MARGIN for m in margins]), axis=0)
    check_margin(res, valid)
    data = render(res, sc, out, "A1", DET_SPP)
    check_exact(res, "A1", data, {"emission": emission}, valid)
    # Handedness: e1 occupies right/upper image region, e2 left/lower.
    cov = {name: ((idx == i) & np.isfinite(t)) for i, (name, *_r) in enumerate(rects)}
    ys, xs = np.nonzero(cov["e1"])
    res.check("A1:e1_right_upper", xs.min() > sc.width / 2 and ys.max() < sc.height / 2, x_min=int(xs.min()), y_max=int(ys.max()))
    ys, xs = np.nonzero(cov["e2"])
    res.check("A1:e2_left_lower", xs.max() < sc.width / 2 and ys.min() > sc.height / 2, x_max=int(xs.max()), y_min=int(ys.min()))
    got = data["mean"][..., 0, :] > 0
    want = emission > 0
    res.check("A1:coverage_mismatch==0", int(((got != want).any(-1) & valid).sum()) == 0,
              mismatched=int(((got != want).any(-1) & valid).sum()), covered=int(want.any(-1).sum()))
    return res


def L_result(cid, title):
    return Result(cid, title)


def floor_occluder_scene(falloff="inverse_square", s=0.0):
    cam = L.Camera((0, 4, 5), (0, 0, -0.5))
    sc = L.Scene(cam, max_bounces=8, falloff=falloff, soft_scale=s)
    sc.material("floor", (0.8, 0.5, 0.2))
    sc.material("black", (0, 0, 0))
    floor = ((-4, 0, 4), (8, 0, 0), (0, 0, -8))
    occ = ((-0.6, 1.5, 0.5), (1.0, 0, 0), (0, 0, -1.0))
    sc.quad("floor", *floor)
    sc.quad("black", *occ)
    light, inten = (0.3, 3.2, -0.4), (20.0, 20.0, 20.0)
    sc.point(light, inten)
    return sc, floor, occ, light, inten


def expected_floor_occluder(sc, floor, occ, light, inten, rho, falloff="inverse_square", s=0.0):
    o, d = L.camera_rays(sc.camera, sc.width, sc.height)
    tf, mf, nf = L.ray_parallelogram(o, d, *floor)
    to, mo, _ = L.ray_parallelogram(o, d, *occ)
    on_floor = np.isfinite(tf) & (tf < to)
    p = o + d * np.where(np.isfinite(tf), tf, 0)[..., None]
    v = np.asarray(light) - p
    dist = np.linalg.norm(v, axis=-1)
    ts, ms, _ = L.ray_parallelogram(p, v / dist[..., None], *occ)
    shadow = np.isfinite(ts) & (ts < dist)
    n = face_forward(nf, d)
    direct = lambert_point(rho, inten, p, n, light, falloff, s)
    direct = np.where((on_floor & ~shadow)[..., None], direct, 0.0)
    valid = (np.abs(mf) >= MARGIN) & (np.abs(mo) >= MARGIN) & (~on_floor | (np.abs(ms) >= MARGIN))
    return direct, valid, on_floor, shadow


def control_a2(out, cid="A2", falloff="inverse_square", s=0.0):
    res = Result(cid, f"lit vs occluded floor, coloured albedo, point light ({falloff})")
    sc, floor, occ, light, inten = floor_occluder_scene(falloff, s)
    direct, valid, on_floor, shadow = expected_floor_occluder(sc, floor, occ, light, inten, (0.8, 0.5, 0.2), falloff, s)
    check_margin(res, valid)
    data = render(res, sc, out, cid, DET_SPP)
    check_exact(res, cid, data, {"direct": direct}, valid)
    lit = on_floor & ~shadow & valid
    res.check(f"{cid}:lit_pixels_strictly_positive", bool(np.all(data["mean"][lit][:, 3, :] > 0)) and lit.sum() > 500,
              lit_pixels=int(lit.sum()), shadow_pixels=int((on_floor & shadow & valid).sum()))
    res.check(f"{cid}:shadow_pixels_present", int((on_floor & shadow & valid).sum()) > 50,
              shadow_pixels=int((on_floor & shadow & valid).sum()))
    ratio = data["mean"][lit][:, 1, :]
    res.check(f"{cid}:channel_ratio_equals_albedo_ratio",
              bool(np.allclose(ratio[:, 1] / ratio[:, 0], 0.5 / 0.8, rtol=1e-9) and np.allclose(ratio[:, 2] / ratio[:, 0], 0.2 / 0.8, rtol=1e-9)))
    return res


def build_a3(D, sampling="center"):
    sc = L.Scene(L.Camera((0, 3.0, 4.0), (0, 0, -0.5)), max_bounces=D, sampling=sampling)
    sc.material("floor", (0.6, 0.6, 0.6))
    sc.material("emit", (0, 0, 0), (5.0, 4.0, 3.0))
    sc.quad("floor", (-3, 0, 3), (6, 0, 0), (0, 0, -6))
    sc.quad("emit", (-0.5, 2.0, -0.5), (1.0, 0, 0), (0, 0, 1.0))
    return sc


def control_a3(out):
    res = Result("A3", "area light: square emitter over floor, closed-form point-to-rectangle irradiance")
    cam = L.Camera((0, 3.0, 4.0), (0, 0, -0.5))
    rho, le = (0.6, 0.6, 0.6), (5.0, 4.0, 3.0)
    floor = ((-3, 0, 3), (6, 0, 0), (0, 0, -6))
    emit = ((-0.5, 2.0, -0.5), (1.0, 0, 0), (0, 0, 1.0))  # normal (1,0,0)x(0,0,1) = -Y, faces floor
    o, d = L.camera_rays(cam, 128, 96)
    tf, mf, _ = L.ray_parallelogram(o, d, *floor)
    te, me, ne = L.ray_parallelogram(o, d, *emit)
    on_floor = np.isfinite(tf) & (tf < te)
    p = o + d * np.where(on_floor, tf, 0)[..., None]
    F = L.rect_point_form_factor(p[..., 0], p[..., 2], 2.0, -0.5, 0.5, -0.5, 0.5)
    direct = np.where(on_floor[..., None], np.asarray(rho) * np.asarray(le) * F[..., None], 0.0)
    emission = np.where((np.isfinite(te) & (te <= tf) & ((d @ ne) < 0))[..., None], np.asarray(le), 0.0)
    valid = (np.abs(mf) >= MARGIN) & (np.abs(me) >= MARGIN)
    check_margin(res, valid)
    for D in (1, 8):
        sc = build_a3(D)
        data = render(res, sc, out, f"A3_D{D}", STAT_SPP)
        check_stat(res, f"A3_D{D}", data, "direct", direct, on_floor & valid, tau=1e-6)
        check_exact(res, f"A3_D{D}", data, {"emission": emission}, valid, components=("emission", "indirect"))
    res.notes["emitter_seen_from_back_by_camera"] = bool(not emission.any())
    return res


def control_a4(out):
    res = Result("A4", "backface / two-sided / one-sided / culling-free shadow")
    light, inten = (2.0, 1.2, -2.3), (8.0, 8.0, 8.0)
    sheet_front_px = ((0, 0, -1), (0, 0, -2), (0, 2, 0))   # normal +X
    sheet_front_nx = ((0, 0, -1), (0, 2, 0), (0, 0, -2))   # normal -X
    cases = [("A4a", (3, 1, -2), True, sheet_front_px, "lit side"),
             ("A4b", (-3, 1, -2), True, sheet_front_px, "unlit side"),
             ("A4c", (3, 1, -2), False, sheet_front_nx, "one-sided back face")]
    for cid, cpos, two, rect, label in cases:
        cam = L.Camera(cpos, (0, 1, -2))
        sc = L.Scene(cam, max_bounces=8)
        sc.material("sheet", (0.7, 0.7, 0.7), two_sided=two)
        sc.quad("sheet", *rect)
        sc.point(light, inten)
        o, d = L.camera_rays(cam, sc.width, sc.height)
        t, m, n = L.ray_parallelogram(o, d, *rect)
        hit = np.isfinite(t)
        p = o + d * np.where(hit, t, 0)[..., None]
        if cid == "A4a":
            direct = np.where(hit[..., None], lambert_point((0.7,) * 3, inten, p, face_forward(n, d), light), 0.0)
        else:
            direct = np.zeros(d.shape)
        valid = np.abs(m) >= MARGIN
        check_margin(res, valid)
        data = render(res, sc, out, cid, DET_SPP)
        check_exact(res, f"{cid}({label})", data, {"direct": direct}, valid)
        if cid == "A4a":
            res.check("A4a:lit_pixels_positive", bool(np.all(data["mean"][hit & valid][:, 3, :] > 0)), pixels=int((hit & valid).sum()))
        if cid == "A4c":
            absorbed = sum(r["backface_absorbed"] for r in data["meta"]["runs"])
            res.check("A4c:backface_absorbed_counter>0", absorbed > 0, absorbed=absorbed)
    # A4d: one-sided occluder whose front faces away from the light still shadows.
    cam = L.Camera((0, 3.5, 3.5), (0, 0, 0))
    sc = L.Scene(cam, max_bounces=1)
    sc.material("floor", (0.5, 0.5, 0.5))
    sc.material("occ", (0.9, 0.9, 0.9), two_sided=False)
    floor = ((-3, 0, 3), (6, 0, 0), (0, 0, -6))
    occ = ((-0.5, 1.2, -0.5), (1.0, 0, 0), (0, 0, 1.0))   # normal -Y (away from light)
    sc.quad("floor", *floor)
    sc.quad("occ", *occ)
    light4, inten4 = (0.2, 3.0, 0.1), (15.0, 15.0, 15.0)
    sc.point(light4, inten4)
    o, d = L.camera_rays(cam, sc.width, sc.height)
    tf, mf, nf = L.ray_parallelogram(o, d, *floor)
    to, mo, _ = L.ray_parallelogram(o, d, *occ)
    on_floor = np.isfinite(tf) & (tf < to)
    p = o + d * np.where(np.isfinite(tf), tf, 0)[..., None]
    v = np.asarray(light4) - p
    dist = np.linalg.norm(v, axis=-1)
    ts, ms, _ = L.ray_parallelogram(p, v / dist[..., None], *occ)
    shadow = np.isfinite(ts) & (ts < dist)
    direct = np.where((on_floor & ~shadow)[..., None], lambert_point((0.5,) * 3, inten4, p, face_forward(nf, d), light4), 0.0)
    valid = (np.abs(mf) >= MARGIN) & (np.abs(mo) >= MARGIN) & (~on_floor | (np.abs(ms) >= MARGIN))
    check_margin(res, valid)
    data = render(res, sc, out, "A4d", DET_SPP)
    check_exact(res, "A4d(back-facing occluder shadows)", data, {"direct": direct}, valid)
    res.check("A4d:shadow_pixels_present", int((on_floor & shadow & valid).sum()) > 50, shadow_pixels=int((on_floor & shadow & valid).sum()))
    return res


def unit_box(sc, mat):
    L.box_triangles(sc, mat, (0, 0, 0), np.eye(3), (1, 1, 1))


def control_a5(out):
    res = Result("A5", "empty/dark scenes and sealed light; strict positivity inside")
    outside = L.Camera((0, 0, 5), (0, 0, 0))
    inside = L.Camera((0, 0, 0.8), (0, 0, -1))
    light = (0.2, 0.1, -0.3)
    sc = L.Scene(outside, max_bounces=8)
    sc.point((0, 0, -2), (10, 10, 10))
    check_zero_all(res, "A5a(no geometry)", render(res, sc, out, "A5a", DET_SPP))
    sc = L.Scene(inside, max_bounces=8)
    sc.material("wall", GRAY)
    unit_box(sc, "wall")
    check_zero_all(res, "A5b(no light)", render(res, sc, out, "A5b", DET_SPP))
    sc.point(light, (0, 0, 0))
    check_zero_all(res, "A5c(zero intensity)", render(res, sc, out, "A5c", DET_SPP))
    for sampling in ("center", "box"):
        sc = L.Scene(outside, max_bounces=8, sampling=sampling)
        sc.material("wall", GRAY)
        unit_box(sc, "wall")
        sc.point(light, (10, 10, 10))
        data = render(res, sc, out, f"A5d_{sampling}", STAT_SPP)
        check_zero_all(res, f"A5d(sealed light, camera outside, {sampling})", data)
        res.check(f"A5d_{sampling}:camera_sees_box", sum(r["primary_hits"] for r in data["meta"]["runs"]) > 0)
    sc = L.Scene(inside, max_bounces=8)
    sc.material("wall", GRAY)
    unit_box(sc, "wall")
    sc.point(light, (10, 10, 10))
    data = render(res, sc, out, "A5e", DET_SPP)
    res.check("A5e:every_pixel_direct>0", bool(np.all(data["mean"][..., 1, :] > 0)), min_direct=float(data["mean"][..., 1, :].min()))
    res.check("A5e:every_pixel_total>0", bool(np.all(data["mean"][..., 3, :] > 0)))
    return res


def sphere_scene(rho, light, inten, D, level=6, far=math.inf):
    cam = L.Camera((0, 0, 0.5), (0, 0, -1), far=far)
    sc = L.Scene(cam, max_bounces=D)
    sc.material("sphere", rho)
    v, f = L.icosphere(level)
    for a, b, c in f:
        sc.tri("sphere", v[a], v[b], v[c])
    sc.point(light, inten)
    return sc, v, f


def sphere_expected(sc, rho, light, inten, D, mesh):
    o, d = L.camera_rays(sc.camera, sc.width, sc.height)
    b = d @ o
    c = o @ o - 1.0
    t = -b + np.sqrt(b * b - c)
    p = o + d * t[..., None]
    n_in = -p
    direct = lambert_point(rho, inten, p, n_in, light)
    l = np.asarray(light) - p
    dist = np.linalg.norm(l, axis=-1)
    dev, sag = L.sphere_mesh_bounds(*mesh)
    cos_inc = np.abs(np.sum(d * p, axis=-1))
    delta = sag / cos_inc
    allowance = (np.asarray(rho) / PI * np.asarray(inten))[None, None, :] * (
        (dev + 2 * delta / dist) / (dist - delta) ** 2 + np.abs(1 / (dist - delta) ** 2 - 1 / dist ** 2))[..., None]
    rho = np.asarray(rho); I = np.asarray(inten)
    indirect = I / PI * sum(rho ** (k + 1) for k in range(1, D))
    return direct, allowance, indirect, {"facet_normal_deviation_rad": dev, "max_sagitta": sag}


def control_a6(out, cid="A6", far=math.inf):
    res = Result(cid, "sphere furnace: constant multi-bounce indirect (analytic)" if cid == "A6" else
                 "upper-distance culling: furnace with camera far 1.6, secondary paths up to 2.0")
    cases = [("a", (0.5, 0.5, 0.5), (0, 0, 0), (1, 1, 1), 8), ("b", (0.9, 0.6, 0.3), (0.3, 0.2, -0.1), (2, 2, 2), 8),
             ("c", (0.9, 0.6, 0.3), (0.3, 0.2, -0.1), (2, 2, 2), 2)]
    if cid == "A10":
        cases = [cases[1]]
    for tag, rho, light, inten, D in cases:
        name = f"{cid}{tag}" if cid == "A6" else cid
        sc, v, f = sphere_scene(rho, light, inten, D, far=far)
        direct, allowance, indirect, bounds = sphere_expected(sc, rho, light, inten, D, (v, f))
        res.notes[f"{name}_mesh"] = {**bounds, "triangles": len(f)}
        res.notes[f"{name}_expected_indirect"] = indirect
        data = render(res, sc, out, name, STAT_SPP)
        mask = np.ones(direct.shape[:2], bool)
        check_stat(res, name, data, "direct", direct, mask, tau=0.0, allowance=allowance)
        check_stat(res, name, data, "indirect", indirect, mask, tau=2e-3)
        if cid == "A10":
            res.check("A10:all_primary_hits_within_far", sum(r["primary_hits"] for r in data["meta"]["runs"]) == 4 * STAT_SPP * sc.width * sc.height)
        if tag == "b" and cid == "A6":
            # Diagnostic only (not gated): level-5 mesh indirect error.
            sc5, v5, f5 = sphere_scene(rho, light, inten, D, level=5)
            d5 = render(res, sc5, out, "A6b_level5_diag", 256)
            res.notes["A6b_level5_indirect_rel_err"] = (d5["mean"][..., 2, :].mean(axis=(0, 1)) / indirect - 1).tolist()
            res.notes["A6b_level6_indirect_rel_err"] = (data["mean"][..., 2, :].mean(axis=(0, 1)) / indirect - 1).tolist()
    return res


def build_a7(D, sampling="center"):
    sc = L.Scene(L.Camera((0, 1.25, 4.5), (0, 1.25, 0), tan_x=1.0, tan_y=0.75), max_bounces=D, sampling=sampling)
    sc.material("floor", (0.7, 0.5, 0.3)); sc.material("ceil", (0.4, 0.6, 0.8))
    sc.quad("floor", (-2, 0, 2), (4, 0, 0), (0, 0, -4)); sc.quad("ceil", (-2, 2.5, -2), (4, 0, 0), (0, 0, 4))
    sc.point((0.3, 1.2, -0.4), (10.0, 10.0, 10.0))
    return sc


def control_a7(out):
    res = Result("A7", "two-bounce non-symmetric floor/ceiling: direct analytic, indirect 2-D Gauss-Legendre quadrature")
    cam = L.Camera((0, 1.25, 4.5), (0, 1.25, 0), tan_x=1.0, tan_y=0.75)
    rf, rc = np.array((0.7, 0.5, 0.3)), np.array((0.4, 0.6, 0.8))
    light, inten = np.array((0.3, 1.2, -0.4)), np.array((10.0, 10.0, 10.0))
    H = 2.5
    floor = ((-2, 0, 2), (4, 0, 0), (0, 0, -4))
    ceil = ((-2, H, -2), (4, 0, 0), (0, 0, 4))
    sc = build_a7(2)
    assert sc.camera == cam
    o, d = L.camera_rays(cam, sc.width, sc.height)
    tf, mf, nf = L.ray_parallelogram(o, d, *floor)
    tc, mc, nc = L.ray_parallelogram(o, d, *ceil)
    idx, t = nearest([tf, tc])
    hit = np.isfinite(t)
    p = o + d * np.where(hit, t, 0)[..., None]
    on_f = hit & (idx == 0); on_c = hit & (idx == 1)
    direct = np.zeros(d.shape)
    direct[on_f] = lambert_point(rf, inten, p, face_forward(nf, d), light)[on_f]
    direct[on_c] = lambert_point(rc, inten, p, face_forward(nc, d), light)[on_c]

    def indirect_at(points, recv_y, src_y, rho_recv, rho_src, panels, order):
        X, Z, W = L.gauss_legendre_square(-2, 2, -2, 2, panels, order)
        hy = abs(light[1] - src_y)
        dl = np.sqrt((X - light[0]) ** 2 + hy ** 2 + (Z - light[2]) ** 2)
        Lsrc = rho_src[None, :] / PI * inten[None, :] * (hy / dl ** 3)[:, None]
        out_vals = np.zeros((len(points), 3))
        h2 = (recv_y - src_y) ** 2
        for i0 in range(0, len(points), 256):
            pts = points[i0:i0 + 256]
            r2 = (pts[:, 0:1] - X[None, :]) ** 2 + h2 + (pts[:, 2:3] - Z[None, :]) ** 2
            kern = h2 / r2 ** 2 * W[None, :]
            out_vals[i0:i0 + 256] = kern @ Lsrc
        return rho_recv[None, :] / PI * out_vals

    indirect = np.zeros(d.shape)
    quad_rel = 0.0
    for mask, ry, sy, rr, rs in ((on_f, 0.0, H, rf, rc), (on_c, H, 0.0, rc, rf)):
        pts = p[mask]
        a = indirect_at(pts, ry, sy, rr, rs, 8, 8)
        b = indirect_at(pts, ry, sy, rr, rs, 16, 8)
        quad_rel = max(quad_rel, float(np.max(np.abs(a - b) / np.abs(b))))
        indirect[mask] = b
    res.check("A7:quadrature_order_doubling_rel<=1e-8", quad_rel <= 1e-8, rel=quad_rel)
    valid = (~on_f | (np.abs(mf) >= MARGIN)) & (~on_c | (np.abs(mc) >= MARGIN))
    check_margin(res, valid)
    data = render(res, sc, out, "A7", STAT_SPP)
    check_exact(res, "A7", data, {"direct": direct}, valid, components=("emission", "direct"))
    check_stat(res, "A7", data, "indirect", indirect, hit & valid, tau=1e-6)
    return res


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def control_a8(out):
    res = Result("A8", "moving rigid occluder frozen at target pose; geometry attestation; stale-pose detector")
    cam = L.Camera((0, 5, 5), (0, 0, 0))
    floor = ((-4, 0, 4), (8, 0, 0), (0, 0, -8))
    light, inten = (0.5, 4.0, 1.0), (30.0, 30.0, 30.0)
    rest_c, tgt_c = np.array((-1.5, 0.5, 1.0)), np.array((0.6, 1.1, -0.4))
    R = rot_y(math.radians(30)) @ rot_x(math.radians(10))
    half = (0.5, 0.5, 0.5)

    def base():
        sc = L.Scene(cam, max_bounces=8)
        sc.material("floor", GRAY); sc.material("black", (0, 0, 0))
        sc.quad("floor", *floor)
        sc.point(light, inten)
        return sc

    rest = base()
    L.box_triangles(rest, "black", rest_c, np.eye(3), half)
    frozen = base()
    for mat, *vs in rest.triangles:
        if mat == "black":
            frozen.tri(mat, *[R @ (np.array(v) - rest_c) + tgt_c for v in vs])
        else:
            frozen.tri(mat, *vs)
    authored = base()
    L.box_triangles(authored, "black", tgt_c, R.T, half)  # rows of R.T = columns of R = box axes

    o, d = L.camera_rays(cam, 128, 96)
    tf, mf, nf = L.ray_parallelogram(o, d, *floor)
    axes = R.T
    t0, t1 = L.ray_obb(o, d, tgt_c, axes, half)
    box_hit = (t1 >= t0) & (t1 > 0)
    on_floor = np.isfinite(tf) & ~(box_hit & (t0 < tf))
    p = o + d * np.where(np.isfinite(tf), tf, 0)[..., None]
    blocked, bm = L.segment_blocked_obb(p, light, tgt_c, axes, half)
    direct = np.where((on_floor & ~blocked)[..., None], lambert_point(GRAY, inten, p, face_forward(nf, d), light), 0.0)
    silhouette = np.abs(t1 - t0) >= MARGIN
    valid = (np.abs(mf) >= MARGIN) & (~box_hit | silhouette) & (~on_floor | (bm >= MARGIN))
    check_margin(res, valid)
    for name, sc in (("A8_frozen", frozen), ("A8_authored", authored)):
        data = render(res, sc, out, name, DET_SPP)
        check_exact(res, name, data, {"direct": direct}, valid)
    res.check("A8:shadow_present", int((on_floor & blocked & valid).sum()) > 50, shadow_pixels=int((on_floor & blocked & valid).sum()))
    res.check("A8:frozen_and_authored_hash_differ_but_both_attested",
              res.runs[0]["geometry_sha256"] != res.runs[1]["geometry_sha256"] and res.runs[0]["geometry_hash_match"] and res.runs[1]["geometry_hash_match"])
    stale = render(res, rest, out, "A8_stale_rest_pose", DET_SPP)
    m = stale["mean"][..., 3, :]
    e = direct
    mismatch = (np.where(e == 0, m != 0, np.abs(m - e) > EXACT_F32 * np.abs(e)).any(-1)) & valid
    frac = float(mismatch.sum() / valid.sum())
    res.check("A8:stale_rest_pose_detected(>=1%)", frac >= 0.01, mismatch_fraction=frac)
    return res


def room_quads(include_room2=True):
    H = 2.5
    q = {
        "floor1": ((-2, 0, 2), (2, 0, 0), (0, 0, -4)), "ceil1": ((-2, H, -2), (2, 0, 0), (0, 0, 4)),
        "back1": ((-2, 0, -2), (2, 0, 0), (0, H, 0)), "front1": ((-2, 0, 2), (0, H, 0), (2, 0, 0)),
        "wallx-": ((-2, 0, -2), (0, 0, 4), (0, H, 0)), "partition": ((0, 0, -2), (0, 0, 4), (0, H, 0)),
    }
    if include_room2:
        q.update({
            "floor2": ((0, 0, 2), (2, 0, 0), (0, 0, -4)), "ceil2": ((0, H, -2), (2, 0, 0), (0, 0, 4)),
            "back2": ((0, 0, -2), (2, 0, 0), (0, H, 0)), "front2": ((0, 0, 2), (0, H, 0), (2, 0, 0)),
            "wallx+": ((2, 0, -2), (0, H, 0), (0, 0, 4)),
        })
    return q


def control_a9(out):
    res = Result("A9", "no-leak rooms: sealed partition, strict positivity, pillar shadow direct/indirect decomposition")
    light, inten = (-1.0, 1.5, 0.3), (10.0, 10.0, 10.0)
    quads = room_quads(True)

    def two_rooms(cam, sampling="center"):
        sc = L.Scene(cam, max_bounces=8, sampling=sampling)
        sc.material("wall", GRAY)
        for qd in quads.values():
            sc.quad("wall", *qd)
        sc.point(light, inten)
        return sc

    cam2 = L.Camera((1.5, 1.2, 1.5), (0, 1.0, -1.0))
    for sampling in ("center", "box"):
        data = render(res, two_rooms(cam2, sampling), out, f"A9a_{sampling}", STAT_SPP)
        check_zero_all(res, f"A9a(room 2, {sampling})", data)
        res.check(f"A9a_{sampling}:every_pixel_hits_geometry",
                  sum(r["primary_hits"] for r in data["meta"]["runs"]) == 4 * STAT_SPP * 128 * 96)
    data = render(res, two_rooms(L.Camera((-1.8, 1.2, 1.8), (-0.5, 1.0, -1.0))), out, "A9b", 256)
    res.check("A9b:every_pixel_total>0", bool(np.all(data["mean"][..., 3, :] > 0)))
    res.check("A9b:every_pixel_direct>0", bool(np.all(data["mean"][..., 1, :] > 0)))

    # A9c: room 1 alone with floor-to-ceiling pillar.
    cam = L.Camera((-0.2, 1.6, 1.8), (-1.2, 0.5, -1.2))
    sc = L.Scene(cam, max_bounces=8)
    sc.material("wall", GRAY)
    room = room_quads(False)
    for qd in room.values():
        sc.quad("wall", *qd)
    pc, ph = np.array((-1.1, 1.25, -0.7)), np.array((0.2, 1.25, 0.2))
    L.box_triangles(sc, "wall", pc, np.eye(3), ph)
    sc.point(light, inten)
    o, d = L.camera_rays(cam, sc.width, sc.height)
    hits = [L.ray_parallelogram(o, d, *qd) for qd in room.values()]
    tw = [h[0] for h in hits]
    iw, twall = nearest(tw)
    t0, t1 = L.ray_obb(o, d, pc, np.eye(3), ph)
    on_pillar = (t1 >= t0) & (t0 > 0) & (t0 < twall)
    t = np.where(on_pillar, t0, twall)
    p = o + d * t[..., None]
    n = np.zeros(d.shape)
    wall_margin = np.full(t.shape, np.inf)
    for i, (tt, mm, nn) in enumerate(hits):
        sel = ~on_pillar & (iw == i)
        n[sel] = face_forward(nn, d)[sel]
        wall_margin[sel] = np.abs(mm)[sel]
    local = (p - pc) / ph
    face_axis = np.argmax(np.abs(local), axis=-1)
    sorted_abs = np.sort(np.abs(local), axis=-1)
    pillar_edge_margin = (1 - sorted_abs[..., 1]) * ph.min()
    for ax in range(3):
        sel = on_pillar & (face_axis == ax)
        nn = np.zeros(3); nn[ax] = 1
        n[sel] = (nn[None, :] * np.sign(local[..., ax][sel])[:, None])
    direct = lambert_point(GRAY, inten, p, n, light)
    blocked, bm = L.segment_blocked_obb(p, light, pc, np.eye(3), ph)
    blocked = np.where(on_pillar, False, blocked)  # convex pillar never shadows its own lit face
    direct = np.where(blocked[..., None], 0.0, direct)
    valid = (wall_margin >= MARGIN) & (~on_pillar | (pillar_edge_margin >= MARGIN)) & (np.abs(t1 - t0) >= MARGIN) & \
            (on_pillar | (bm >= MARGIN))
    check_margin(res, valid)
    data = render(res, sc, out, "A9c", STAT_SPP)
    lit = valid & ~blocked
    shadowed = valid & blocked
    check_exact(res, "A9c", data, {"direct": direct}, valid, components=("emission", "direct"))
    res.check("A9c:shadowed_pixels_present", int(shadowed.sum()) > 100, shadowed=int(shadowed.sum()), lit=int(lit.sum()))
    res.check("A9c:shadowed_direct_exactly_zero", bool(np.all(data["mean"][shadowed][:, 1, :] == 0)))
    res.check("A9c:shadowed_indirect_strictly_positive", bool(np.all(data["mean"][shadowed][:, 2, :] > 0)),
              min_indirect=float(data["mean"][shadowed][:, 2, :].min()))
    res.check("A9c:every_pixel_total>0", bool(np.all(data["mean"][..., 3, :] > 0)))
    return res


CONTROLS = {
    "A1": control_a1,
    "A2": control_a2,
    "A2b": lambda out: control_a2(out, "A2b", "n001_soft", 1.5),
    "A3": control_a3,
    "A4": control_a4,
    "A5": control_a5,
    "A6": control_a6,
    "A7": control_a7,
    "A8": control_a8,
    "A9": control_a9,
    "A10": lambda out: control_a6(out, "A10", far=1.6),
}


def git_head():
    try:
        sha = subprocess.run(["git", "-C", str(L.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(L.ROOT), "status", "--porcelain", "--", "src/research/n008_hdr_oracle",
                                "scripts/research/n008_hdr_oracle"], capture_output=True, text=True).stdout.strip()
        return sha, bool(dirty)
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(L.ROOT / "out/research/n008-hdr-oracle/phase-a"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--summary")
    args = ap.parse_args()
    out = Path(args.out)
    sha, dirty = git_head()
    results = []
    for cid, fn in CONTROLS.items():
        if args.only and cid not in args.only:
            continue
        t0 = time.time()
        r = fn(out)
        r.notes["wall_seconds_diagnostic"] = round(time.time() - t0, 2)
        results.append(r)
        print(f"{cid:4s} {'PASS' if r.passed else 'FAIL'}  ({r.notes['wall_seconds_diagnostic']} s)", flush=True)
        for c in r.checks:
            if not c["pass"]:
                print("     FAIL", json.dumps(c)[:600], flush=True)
    summary = {"schema": "n008-phase-a-controls/1", "source_commit": sha, "source_dirty": dirty,
               "oracle_binary": str(L.oracle_binary().relative_to(L.ROOT)), "python": platform.python_version(),
               "numpy": np.__version__, "seeds": list(SEEDS), "all_pass": all(r.passed for r in results),
               "controls": [r.to_json() for r in results]}
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, indent=1) + "\n")
    print("ALL PASS" if summary["all_pass"] else "SOME CONTROLS FAILED")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

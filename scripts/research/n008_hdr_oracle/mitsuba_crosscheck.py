#!/usr/bin/env python3
"""N008 Phase A independent-integrator cross-check X1-X6 (protocol experiments/001).

Each cell's scene is written once as a .n008 file; the oracle renders that file
and this script independently parses the same file into a Mitsuba 3 scene
(identical triangles, float32 in Mitsuba). Requires `mitsuba==3.6.4` and numpy
(see requirements-crosscheck.txt); CPU `scalar_rgb` variant only."""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n008lib as L  # noqa: E402
import phase_a_controls as A  # noqa: E402

MI_SEEDS = tuple(range(16))
MI_SPP = 256
ORACLE_SPP = 1024
TAU = 1e-3


def parse_n008(path: Path) -> dict:
    """Independent parser of the oracle scene format (no shared code with C++)."""
    sc = {"materials": {}, "order": [], "tris": {}, "points": []}
    for line in path.read_text().splitlines():
        w = line.split("#")[0].split()
        if not w:
            continue
        k = w[0]
        if k == "n008scene":
            assert w[1] == "1"
        elif k == "resolution":
            sc["width"], sc["height"] = int(w[1]), int(w[2])
        elif k == "camera":
            v = [float(x) for x in w[1:13]]
            sc["camera"] = {"origin": v[0:3], "forward": v[3:6], "up": v[6:9], "tan_x": v[9], "tan_y": v[10],
                            "near": v[11], "far": float(w[13])}
        elif k == "sampling":
            sc["sampling"] = w[1]
        elif k == "max_bounces":
            sc["max_bounces"] = int(w[1])
        elif k == "falloff":
            if w[1] != "inverse_square":
                raise SystemExit("Mitsuba cross-check supports inverse_square only")
        elif k == "secondary_far":
            if w[1] != "inf":
                raise SystemExit("Mitsuba cross-check supports secondary_far inf only")
        elif k == "material":
            vals = [float(x) for x in w[2:9]]
            sc["materials"][w[1]] = {"rho": vals[0:3], "emit": vals[3:6], "two_sided": vals[6] != 0}
            sc["order"].append(w[1])
        elif k == "point":
            v = [float(x) for x in w[1:7]]
            sc["points"].append((v[0:3], v[3:6]))
        elif k == "tri":
            sc["tris"].setdefault(w[1], []).append([float(x) for x in w[2:11]])
        else:
            raise SystemExit(f"unknown directive {k}")
    return sc


def write_ply(path: Path, tris: list):
    with path.open("wb") as f:
        n = len(tris)
        f.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {3 * n}\nproperty float x\nproperty float y\n"
                 f"property float z\nelement face {n}\nproperty list uchar int vertex_indices\nend_header\n").encode())
        for t in tris:
            f.write(struct.pack("<9f", *t))
        for i in range(n):
            f.write(struct.pack("<B3i", 3, 3 * i, 3 * i + 1, 3 * i + 2))


def mitsuba_scene(sc: dict, work: Path, analytic_sphere=False):
    import mitsuba as mi
    cam = sc["camera"]
    o = np.array(cam["origin"]); f = np.array(cam["forward"])
    d = {"type": "scene",
         "integrator": {"type": "path", "max_depth": sc["max_bounces"] + 1, "rr_depth": sc["max_bounces"] + 2,
                        "hide_emitters": False},
         "sensor": {"type": "perspective", "fov_axis": "x", "fov": math.degrees(2 * math.atan(cam["tan_x"])),
                    "near_clip": 1e-4, "far_clip": 1e4 if math.isinf(cam["far"]) else cam["far"],
                    "to_world": mi.ScalarTransform4f().look_at(origin=o.tolist(), target=(o + f).tolist(), up=cam["up"]),
                    "film": {"type": "hdrfilm", "width": sc["width"], "height": sc["height"], "rfilter": {"type": "box"},
                             "pixel_format": "rgb", "component_format": "float32"},
                    "sampler": {"type": "independent", "sample_count": MI_SPP}}}
    if abs(cam["tan_y"] - cam["tan_x"] * sc["height"] / sc["width"]) > 1e-12:
        raise SystemExit("non-square pixels are not representable in this cross-check")
    for name in sc["order"]:
        m = sc["materials"][name]
        if name not in sc["tris"]:
            continue
        bsdf = {"type": "diffuse", "reflectance": {"type": "rgb", "value": m["rho"]}}
        if m["two_sided"]:
            bsdf = {"type": "twosided", "material": bsdf}
        if analytic_sphere and name == "sphere":
            shape = {"type": "sphere", "radius": 1.0, "center": [0, 0, 0], "bsdf": bsdf}
        else:
            ply = work / f"{name}.ply"
            write_ply(ply, sc["tris"][name])
            shape = {"type": "ply", "filename": str(ply), "face_normals": True, "bsdf": bsdf}
        if any(e > 0 for e in m["emit"]):
            shape["emitter"] = {"type": "area", "radiance": {"type": "rgb", "value": m["emit"]}}
        d[f"shape_{name}"] = shape
    for i, (pos, inten) in enumerate(sc["points"]):
        d[f"light_{i}"] = {"type": "point", "position": pos, "intensity": {"type": "rgb", "value": inten}}
    return mi.load_dict(d)


def render_mitsuba(scene):
    import mitsuba as mi
    imgs = [np.array(mi.render(scene, seed=s, spp=MI_SPP), dtype=np.float64)[..., :3] for s in MI_SEEDS]
    stack = np.stack(imgs)
    return {"mean": stack.mean(0), "se": stack.std(0, ddof=1) / math.sqrt(len(imgs)),
            "image_means": stack.mean(axis=(1, 2))}


def compare(cid, oracle, mits, label="", gated=True):
    mo, so = oracle["mean"][..., 3, :], oracle["se"][..., 3, :]
    mm, sm = mits["mean"], mits["se"]
    region = []
    ok = True
    npx = mo.shape[0] * mo.shape[1]
    for c in range(3):
        a = float(mo[..., c].mean()); b = float(mm[..., c].mean())
        se_o = float(np.sqrt(np.sum(so[..., c] ** 2)) / npx)
        se_m = float(mits["image_means"][:, c].std(ddof=1) / math.sqrt(len(MI_SEEDS)))
        bound = 5 * math.sqrt(se_o ** 2 + se_m ** 2) + TAU * abs(b)
        cok = abs(a - b) <= bound
        ok &= cok
        region.append({"channel": c, "oracle": a, "mitsuba": b, "rel_diff": abs(a - b) / abs(b) if b else None,
                       "bound": bound, "min_detectable_rel": bound / abs(b) if b else None, "pass": cok})
    nz = (mo != 0) | (mm != 0)
    z = (mo - mm) / np.sqrt(so ** 2 + sm ** 2 + (TAU * mm) ** 2)
    zsel = np.abs(z[nz]) if nz.any() else np.array([0.0])
    frac = float(np.mean(zsel <= 6))
    ok &= frac >= 0.999
    zero_disagree = int(np.sum((mo == 0) & (mm > 1e-6))) + int(np.sum((mm == 0) & (mo > 1e-6)))
    return {"id": cid, "label": label, "gated": gated, "pass": bool(ok), "region": region,
            "pixel_channels_nonzero": int(nz.sum()), "pixel_z_le_6_fraction": frac,
            "max_abs_z": float(zsel.max()), "zero_disagreements_reported_not_gated": zero_disagree}


def build_x6():
    """Cornell-like closed room with coloured walls, ceiling area light and pillar."""
    cam = L.Camera((-0.2, 1.6, 1.8), (-1.2, 0.5, -1.2))
    sc = L.Scene(cam, max_bounces=8, sampling="box")
    sc.material("white", (0.75, 0.75, 0.75)); sc.material("red", (0.75, 0.15, 0.1)); sc.material("green", (0.15, 0.7, 0.2))
    sc.material("lamp", (0, 0, 0), (8.0, 8.0, 8.0), two_sided=False)
    q = A.room_quads(False)
    for name, quad in q.items():
        sc.quad({"wallx-": "red", "partition": "green"}.get(name, "white"), *quad)
    L.box_triangles(sc, "white", (-1.1, 1.25, -0.7), np.eye(3), (0.2, 1.25, 0.2))
    sc.quad("lamp", (-1.3, 2.49, -0.3), (0.6, 0, 0), (0, 0, 0.6))  # normal -Y
    return sc


def cells():
    s2, *_ = A.floor_occluder_scene()
    s2.sampling = "box"
    s4, _, _ = A.sphere_scene((0.9, 0.6, 0.3), (0.3, 0.2, -0.1), (2, 2, 2), 8)
    s4.sampling = "box"
    return [("X1", "A1 emitters/handedness", A.build_a1("box")[0]),
            ("X2", "A2 lit/occluded floor D=8", s2),
            ("X3", "A3 area light D=8", A.build_a3(8, "box")),
            ("X4", "A6b sphere furnace (same mesh)", s4),
            ("X5a", "A7 floor/ceiling D=2", A.build_a7(2, "box")),
            ("X5b", "A7 floor/ceiling D=8", A.build_a7(8, "box")),
            ("X6", "Cornell-like room, area light, pillar, D=8", build_x6())]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(L.ROOT / "out/research/n008-hdr-oracle/phase-a-x"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--summary")
    args = ap.parse_args()
    import mitsuba as mi
    mi.set_variant("scalar_rgb")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    results, runs = [], []
    for cid, label, scene in cells():
        if args.only and cid not in args.only:
            continue
        t0 = time.time()
        meta = L.run_oracle(scene, out, cid, spp=ORACLE_SPP)
        oracle = L.pooled(meta)
        work = out / f"{cid}_mitsuba"; work.mkdir(exist_ok=True)
        parsed = parse_n008(out / f"{cid}.n008")
        mits = render_mitsuba(mitsuba_scene(parsed, work))
        r = compare(cid, oracle, mits, label)
        r["oracle_geometry_sha256"] = meta["geometry_sha256"]
        r["geometry_hash_match"] = meta["geometry_hash_match"]
        r["pass"] = r["pass"] and meta["geometry_hash_match"]
        r["wall_seconds_diagnostic"] = round(time.time() - t0, 1)
        results.append(r)
        print(f"{cid:4s} {'PASS' if r['pass'] else 'FAIL'} {label}  "
              f"rel={[round(x['rel_diff'], 6) if x['rel_diff'] else None for x in r['region']]} "
              f"zfrac={r['pixel_z_le_6_fraction']:.5f} maxz={r['max_abs_z']:.2f} ({r['wall_seconds_diagnostic']} s)", flush=True)
        if cid == "X4":
            mits_a = render_mitsuba(mitsuba_scene(parsed, work, analytic_sphere=True))
            d = compare("X4-analytic-sphere", oracle, mits_a, "diagnostic only: oracle mesh vs Mitsuba analytic sphere", gated=False)
            results.append(d)
            print(f"     diag {d['id']} rel={[round(x['rel_diff'], 6) for x in d['region']]} zfrac={d['pixel_z_le_6_fraction']:.5f}")
    gated = [r for r in results if r["gated"]]
    summary = {"schema": "n008-phase-a-crosscheck/1", "mitsuba_version": mi.__version__, "variant": mi.variant(),
               "mitsuba_seeds": list(MI_SEEDS), "mitsuba_spp_per_seed": MI_SPP, "oracle_seeds": list(L.N007_SEEDS),
               "oracle_spp_per_seed": ORACLE_SPP, "tau": TAU, "all_pass": all(r["pass"] for r in gated), "cells": results}
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, indent=1) + "\n")
    print("ALL PASS" if summary["all_pass"] else "SOME CELLS FAILED")
    return 0 if summary["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

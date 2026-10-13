#!/usr/bin/env python3
"""N008 Phase A sensitivity diagnostics (post-hoc, NOT preregistered gates).

Each case injects a known transport defect through scene switches only (no
oracle code change) and re-applies the frozen Phase A gate. A useful gate must
FAIL on every case; `detected=true` means the gate failed as required."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n008lib as L  # noqa: E402
import phase_a_controls as A  # noqa: E402


def n1_far_truncation(out):
    """N001-style secondary rays truncated at camera far (A10 geometry)."""
    rho, light, inten, D = (0.9, 0.6, 0.3), (0.3, 0.2, -0.1), (2, 2, 2), 8
    sc, v, f = A.sphere_scene(rho, light, inten, D, far=1.6)
    sc.secondary_far = "camera"
    _, _, indirect, _ = A.sphere_expected(sc, rho, light, inten, D, (v, f))
    res = A.Result("N1", "secondary_far=camera on A10")
    data = A.render(res, sc, out, "N1", 256)
    ok = A.check_stat(res, "N1", data, "indirect", indirect, np.ones(data["mean"].shape[:2], bool), tau=2e-3)
    return res, not ok


def n2_soft_falloff(out):
    """N001 soft falloff rendered, judged against inverse-square physics (A2)."""
    sc, floor, occ, light, inten = A.floor_occluder_scene("n001_soft", 1.5)
    direct, valid, *_ = A.expected_floor_occluder(sc, floor, occ, light, inten, (0.8, 0.5, 0.2))
    res = A.Result("N2", "n001_soft falloff vs inverse-square expectation")
    data = A.render(res, sc, out, "N2", 16)
    ok = A.check_exact(res, "N2", data, {"direct": direct}, valid, components=("direct",))
    return res, not ok


def n3_light_offset(out):
    """Light position displaced by 1 mm (world-transform / units slip) on A2."""
    sc, floor, occ, light, inten = A.floor_occluder_scene()
    direct, valid, *_ = A.expected_floor_occluder(sc, floor, occ, light, inten, (0.8, 0.5, 0.2))
    sc.points = [((light[0], light[1] + 1e-3, light[2]), inten)]
    res = A.Result("N3", "light displaced 1e-3")
    data = A.render(res, sc, out, "N3", 16)
    ok = A.check_exact(res, "N3", data, {"direct": direct}, valid, components=("direct",))
    return res, not ok


def n4_albedo_half_percent(out):
    """Floor albedo 0.5% low on A7 two-bounce (BSDF/reflectance scale error)."""
    sc = A.build_a7(2)
    rho, emit, two = sc.materials["floor"]
    sc.materials["floor"] = (tuple(r * 0.995 for r in rho), emit, two)
    sc.materials = dict(sc.materials)
    res = A.Result("N4", "floor albedo x0.995 on A7")
    # Re-run the frozen A7 expectation through the control itself on the defective scene.
    orig = A.build_a7
    A.build_a7 = lambda D, sampling="center": sc
    try:
        r = A.control_a7(out)
    finally:
        A.build_a7 = orig
    failed = [c["name"] for c in r.checks if not c["pass"]]
    res.checks = r.checks
    res.runs = r.runs
    return res, bool(failed)


def n5_one_sided_walls(out):
    """X6 room: oracle walls one-sided (wrong orientation semantics) vs Mitsuba two-sided."""
    import mitsuba as mi
    import mitsuba_crosscheck as X
    mi.set_variant("scalar_rgb")
    good = X.build_x6()
    bad = X.build_x6()
    bad.materials = {k: (v[0], v[1], False if k != "lamp" else v[2]) for k, v in bad.materials.items()}
    meta = L.run_oracle(bad, out, "N5", spp=256)
    work = out / "N5_mitsuba"; work.mkdir(parents=True, exist_ok=True)
    (out / "N5_good.n008").write_text(good.text())
    mits = X.render_mitsuba(X.mitsuba_scene(X.parse_n008(out / "N5_good.n008"), work))
    r = X.compare("N5", L.pooled(meta), mits, "one-sided oracle walls")
    res = A.Result("N5", "one-sided walls vs two-sided Mitsuba")
    res.checks = [{"name": "N5:crosscheck", "pass": r["pass"], "region": r["region"]}]
    return res, not r["pass"]


CASES = [n1_far_truncation, n2_soft_falloff, n3_light_offset, n4_albedo_half_percent, n5_one_sided_walls]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(L.ROOT / "out/research/n008-hdr-oracle/phase-a-sensitivity"))
    ap.add_argument("--summary")
    args = ap.parse_args()
    out = Path(args.out)
    rows = []
    for fn in CASES:
        res, detected = fn(out)
        rows.append({"id": res.cid, "defect": fn.__doc__.strip(), "detected": bool(detected),
                     "failed_checks": [c["name"] for c in res.checks if not c["pass"]]})
        print(f"{res.cid} detected={detected} {rows[-1]['failed_checks']}", flush=True)
    summary = {"schema": "n008-phase-a-sensitivity/1", "post_hoc_diagnostic_not_gate": True,
               "all_detected": all(r["detected"] for r in rows), "cases": rows}
    if args.summary:
        Path(args.summary).write_text(json.dumps(summary, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

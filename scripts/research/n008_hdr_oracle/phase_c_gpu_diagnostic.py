#!/usr/bin/env python3
"""N008 Phase C diagnostic: compare a frozen GPU Renderer capture (N007 capture
layout: frame-state.bin, geometry-state.bin, gpu/{direct,indirect,total}.pfm,
gpu/hits.bin) against a locked Phase B oracle cell. Diagnostic only: no
performance/architecture change, and NO quality score is produced for cells
whose reference is NO_SUPPORT or INELIGIBLE."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import n008lib as L  # noqa: E402
import phase_b_ladder as B  # noqa: E402

LUMA = np.array((0.2126, 0.7152, 0.0722))
SCORABLE = {"STATISTICALLY_ELIGIBLE": ("total", "direct", "indirect"), "DIRECT_DETERMINISTIC_PROVED": ("direct",)}


def gpu_hits(path: Path, n: int):
    raw = path.read_bytes()
    if len(raw) != 32 * n:
        raise SystemExit("hits.bin size mismatch")
    rec = np.frombuffer(raw, dtype=np.dtype([("n", "<f4", (3,)), ("t", "<f4"), ("prim", "<u4"), ("mat", "<u4"),
                                             ("inst", "<u4"), ("flag", "<u4")]))
    return rec


def compare(capture: Path, cell: str, transport: str, phase_b: Path, summary: dict) -> dict:
    row = next(c for c in summary["cells"] if c["cell"] == cell and c["transport"] == transport)
    work = phase_b / f"{cell}_{transport}"
    frame_sha = hashlib.sha256((capture / "frame-state.bin").read_bytes()).hexdigest()
    geom_sha = hashlib.sha256((capture / "geometry-state.bin").read_bytes()).hexdigest()
    state_match = (frame_sha, geom_sha) == (row["state_sha256"]["frame"], row["state_sha256"]["geometry"])
    out = {"cell": cell, "transport": transport, "reference_classification": row["classification"],
           "capture_state_sha256": {"frame": frame_sha, "geometry": geom_sha}, "state_bytes_match_reference": state_match}
    if not state_match:
        out["verdict"] = "STATE_MISMATCH_NO_COMPARISON"
        return out
    runs = [L.read_sidecar(Path(str(B.level_prefix(work, i, B.LEVELS[-1])) + ".f64")) for i in range(4)]
    ref = sum(r["mean"] for r in runs) / 4
    h, w = ref.shape[:2]
    gpu = {k: L.read_pfm(capture / "gpu" / f"{k}.pfm") @ LUMA for k in ("direct", "indirect", "total")}
    refY = {k: ref[..., L.COMPONENTS.index(k), :] @ LUMA for k in ("direct", "indirect", "total")}
    # Primary visibility agreement (oracle hit sidecar vs GPU hits, both top-down row-major).
    oh = np.frombuffer((work / "o.hits").read_bytes(), dtype=np.dtype([("t", "<f8"), ("tri", "<u4"), ("front", "<u4")]), offset=16)
    gh = gpu_hits(capture / "gpu" / "hits.bin", h * w)
    o_hit, g_hit = oh["t"] >= 0, gh["flag"] == 1
    both = o_hit & g_hit
    geom = (capture / "geometry-state.bin").read_bytes()
    n = struct.unpack_from("<2I", geom)[1]
    meta = np.frombuffer(geom, dtype=np.dtype([("v", "<f4", (9,)), ("m", "<u4", (4,))]), offset=8)["m"]
    prim_ids = meta[:, 0]
    o_prim = np.where(o_hit, prim_ids[np.minimum(oh["tri"], n - 1)], 0xFFFFFFFF)
    out["primary"] = {
        "oracle_hits": int(o_hit.sum()), "gpu_hits": int(g_hit.sum()), "mask_mismatch": int((o_hit != g_hit).sum()),
        "primitive_mismatch_on_common": int((both & (o_prim != gh["prim"])).sum()),
        "max_rel_t_diff_on_common_same_primitive": float(np.max(np.abs(oh["t"][both & (o_prim == gh["prim"])] - gh["t"][both & (o_prim == gh["prim"])]) /
                                                         oh["t"][both & (o_prim == gh["prim"])])) if (both & (o_prim == gh["prim"])).any() else None,
        "oracle_backface_single_sided": int((o_hit & (meta[np.minimum(oh["tri"], n - 1), 3] == 0) & (oh["front"] == 0)).sum()),
    }
    comps = {}
    for k in ("direct", "indirect", "total"):
        g, r = gpu[k].ravel(), refY[k].ravel()
        comps[k] = {"gpu_positive": int((g > 0).sum()), "reference_positive": int((r > 0).sum()),
                    "gpu_only_positive": int(((g > 0) & (r <= 0)).sum()), "reference_only_positive": int(((r > 0) & (g <= 0)).sum()),
                    "gpu_sum": float(g.sum()), "reference_sum": float(r.sum()),
                    "gpu_sum_on_reference_zero": float(g[r <= 0].sum())}
        if k in SCORABLE.get(row["classification"], ()):
            act = r > 0
            err = np.abs(g[act] - r[act])
            comps[k]["scored_on_reference_active"] = {
                "pixels": int(act.sum()), "rmse": float(np.sqrt(np.mean((g[act] - r[act]) ** 2))),
                "mean_signed_bias": float(np.mean(g[act] - r[act])), "relative_bias_of_sum": float((g[act].sum() - r[act].sum()) / r[act].sum()),
                "p99_abs": float(np.quantile(err, 0.99))}
    out["components_luma"] = comps
    if row["classification"] in SCORABLE:
        out["verdict"] = "DIAGNOSTIC_COMPARISON_ON_ELIGIBLE_COMPONENTS"
    else:
        out["verdict"] = "NOT_SCORED_REFERENCE_" + row["classification"]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", required=True, type=Path)
    ap.add_argument("--cell", required=True)
    ap.add_argument("--transport", default="T_B2")
    ap.add_argument("--phase-b", required=True, type=Path)
    ap.add_argument("--summary", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    a = ap.parse_args()
    res = compare(a.capture, a.cell, a.transport, a.phase_b, json.loads(a.summary.read_text()))
    text = json.dumps(res, indent=1, allow_nan=False)
    if a.output:
        a.output.write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()

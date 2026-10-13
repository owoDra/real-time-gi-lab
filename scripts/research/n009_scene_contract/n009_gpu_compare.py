#!/usr/bin/env python3
"""N009 GPU diagnostic + back-face gates BF1-BF3, using the UNCHANGED N008
phase_c_gpu_diagnostic.compare.

C1-C5 are compared with the N009 ladder summary. C7 (leak-medium under BF-P) is
compared with the locked N008 B7 reference after a mechanical equivalence check:
identical frame bytes, identical vertices and ids, and sided = 1 everywhere (the
N008 reference transport T_B was already two-sided, and the oracle geometry hash
covers vertices and material only)."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "n008_hdr_oracle"))
import n008lib as L  # noqa: E402
import phase_c_gpu_diagnostic as C  # noqa: E402  (N008, unchanged)

N008_B7_STATE = L.ROOT / "out/research/n008-hdr-oracle/phase-b-states/leak-medium"
NPX = 320 * 180


def c7_equivalence(capture: Path) -> dict:
    cap, ref = L.read_state(capture), L.read_state(N008_B7_STATE)
    out = {"frame_bytes_identical": (capture / "frame-state.bin").read_bytes() == (N008_B7_STATE / "frame-state.bin").read_bytes(),
           "vertices_identical": bool(np.array_equal(cap["verts"], ref["verts"])),
           "ids_identical": bool(np.array_equal(cap["meta"][:, :3], ref["meta"][:, :3])),
           "sided_all_one": bool((cap["meta"][:, 3] == 1).all())}
    out["equivalent_under_bf_p"] = all(out.values())
    return out


def run(capture: Path, cell: str, transport: str, n009_summary: dict, n009_ladder: Path, n008_summary: dict,
        n008_phase_b: Path) -> dict:
    sided = L.read_state(capture)["meta"][:, 3]
    bf1 = bool((sided == 1).all())
    if cell == "C7":
        eq = c7_equivalence(capture)
        if not eq["equivalent_under_bf_p"]:
            return {"cell": cell, "transport": transport, "c7_equivalence": eq, "verdict": "NOT_EQUIVALENT_NO_COMPARISON"}
        summary = copy.deepcopy(n008_summary)
        geom = hashlib.sha256((capture / "geometry-state.bin").read_bytes()).hexdigest()
        for row in summary["cells"]:
            if row["cell"] == "B7":
                row["state_sha256"] = dict(row["state_sha256"], geometry=geom)
        res = C.compare(capture, "B7", transport, n008_phase_b, summary)
        res["c7_equivalence"] = eq
        res["cell"] = "C7"
    else:
        res = C.compare(capture, cell, transport, n009_ladder, n009_summary)
    res["bf1_all_sided_one"] = bf1
    if "primary" in res:
        mism = res["primary"]["mask_mismatch"] + res["primary"]["primitive_mismatch_on_common"]
        res["bf2_primary_mismatch_pixels"] = mism
        res["bf2_pass"] = mism <= 0.001 * NPX
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--captures", type=Path, required=True, help="directory of N009 captures <cell>-<regime>-<backend>")
    ap.add_argument("--n009-summary", type=Path, required=True)
    ap.add_argument("--n009-ladder", type=Path, required=True)
    ap.add_argument("--n008-summary", type=Path, required=True)
    ap.add_argument("--n008-phase-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    s9, s8 = json.loads(a.n009_summary.read_text()), json.loads(a.n008_summary.read_text())
    rows = []
    for cap in sorted(p for p in a.captures.iterdir() if p.is_dir() and (p / "gpu" / "total.pfm").exists()):
        cell = cap.name.split("-")[0]
        for t in ("T_B2", "T_B8"):
            r = run(cap, cell, t, s9, a.n009_ladder, s8, a.n008_phase_b)
            r["capture"] = cap.name
            rows.append(r)
            print(cap.name, t, r.get("verdict"), "bf2", r.get("bf2_primary_mismatch_pixels"), flush=True)
    c7 = [r for r in rows if r["cell"] == "C7" and "components_luma" in r]
    bf3 = [r["components_luma"]["direct"]["scored_on_reference_active"]["max_rel"] for r in c7
           if "scored_on_reference_active" in r["components_luma"]["direct"]]
    gates = {"BF1": all(r["bf1_all_sided_one"] for r in rows),
             "BF2_C7": bool(c7) and all(r.get("bf2_pass") for r in c7),
             "BF3_C7_direct_max_rel": max(bf3) if bf3 else None,
             "BF3": bool(bf3) and max(bf3) <= 1e-4}
    a.output.write_text(json.dumps({"schema": "n009-gpu-compare/1", "gates": gates, "rows": rows}, indent=1,
                                   allow_nan=False) + "\n")
    print(json.dumps(gates))


if __name__ == "__main__":
    main()

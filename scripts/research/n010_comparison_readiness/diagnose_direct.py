#!/usr/bin/env python3
"""Post-hoc diagnostic on immutable N009 inputs; no scoring mask rescue."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n008_hdr_oracle"))
import n008lib as L
from phase_c_gpu_diagnostic import gpu_hits


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(binary, work):
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    for cap in sorted((ROOT / "out/research/n009-scene-contract/gpu-bc2419c").iterdir()):
        if not cap.is_dir():
            continue
        cell = cap.name.split("-")[0]
        if cell not in ("C1", "C2", "C4", "C5", "C7"):
            continue
        ref = (ROOT / "out/research/n008-hdr-oracle/phase-b-9aab73b/B7_T_B2" if cell == "C7"
               else ROOT / f"out/research/n009-scene-contract/ladder-bc2419c/{cell}_T_B2")
        state = L.read_state(cap)
        w, h = state["width"], state["height"]
        gh = gpu_hits(cap / "gpu/hits.bin", w * h)
        oh = np.frombuffer((ref / "o.hits").read_bytes(),
                          dtype=[("t", "<f8"), ("tri", "<u4"), ("front", "<u4")], offset=16)
        r = L.read_sidecar(ref / "o.s0.f64")["mean"][..., 1, 0].ravel()
        g = L.read_pfm(cap / "gpu/direct.pfm")[..., 0].ravel()
        o_hit, g_hit = oh["t"] >= 0, gh["flag"] == 1
        op = state["meta"][np.minimum(oh["tri"], len(state["meta"]) - 1), 0]
        matched = o_hit & g_hit & (op == gh["prim"])
        # Preserve both signs, including reference-zero leaks.
        mismatch = matched & ((r > 0) != (g > 0))
        ids = np.flatnonzero(mismatch)
        tsv = work / f"{cap.name}.pixels.tsv"
        tsv.write_text("".join(f"{i} {oh['t'][i]:.17g} {oh['tri'][i]} {g[i]:.17g} {r[i]:.17g}\n"
                               for i in ids))
        p = subprocess.run([str(binary), str(cap), str(tsv)], capture_output=True, text=True, check=True)
        detail = json.loads(p.stdout)
        (work / f"{cap.name}.rays.json").write_text(json.dumps(detail, indent=2) + "\n")
        rows.append({"capture": cap.name, "state_sha256": state["sha256"],
                     "hits_sha256": sha(cap / "gpu/hits.bin"),
                     "direct_pfm_sha256": sha(cap / "gpu/direct.pfm"),
                     "reference_f64_sha256": sha(ref / "o.s0.f64"),
                     "reference_hits_sha256": sha(ref / "o.hits"),
                     "matched_primary_pixels": int(matched.sum()),
                     "gpu_zero_reference_positive": int((matched & (r > 0) & (g <= 0)).sum()),
                     "gpu_positive_reference_zero": int((matched & (r <= 0) & (g > 0)).sum()),
                     "diagnostic": detail})
    return {"schema": "n010-n009-posthoc-direct/1",
            "preregistration_commit": "3f2e78e",
            "historical_parent": "6e7e96246cf7e9e38394bdce89519bf09320c6b1",
            "classification": "post-hoc CPU diagnosis; not repaired GPU validation",
            "binary_sha256": sha(binary), "rows": rows}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", type=Path, default=ROOT / "build/n010-cpu/direct_diagnostic")
    ap.add_argument("--work", type=Path, default=ROOT / "out/research/n010-comparison-readiness/direct-diagnostic")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run(args.binary, args.work)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for row in result["rows"]:
        print(row["capture"], row["gpu_zero_reference_positive"], row["gpu_positive_reference_zero"])

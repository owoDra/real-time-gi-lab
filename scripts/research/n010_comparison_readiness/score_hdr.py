#!/usr/bin/env python3
"""Full-image linear HDR scoring; no masks based on observed candidate errors."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n008_hdr_oracle"))
import n008lib as L
from qualify_references import scene_for_state
LUMA = np.array((0.2126, 0.7152, 0.0722))


def metrics(gpu, reference):
    g, r = np.asarray(gpu, float).ravel(), np.asarray(reference, float).ravel()
    if g.shape != r.shape or not np.isfinite(g).all() or not np.isfinite(r).all():
        raise ValueError("HDR shape or finiteness failure")
    if (g < 0).any() or (r < 0).any():
        raise ValueError("negative physical radiance")
    err = g-r
    rmse = float(np.sqrt(np.mean(err**2)))
    scale = float(np.sqrt(np.mean(r**2)))
    active = r > 0
    return {"pixels": len(r), "scoring_exclusions": 0, "rmse": rmse,
            "reference_rms": scale, "nrmse": rmse/scale if scale > 0 else None,
            "signed_sum_bias": float(err.sum()/r.sum()) if r.sum() > 0 else None,
            "reference_sum": float(r.sum()), "gpu_sum": float(g.sum()),
            "active_pixels": int(active.sum()),
            "active_p99_absolute": float(np.quantile(np.abs(err[active]), .99)) if active.any() else None,
            "active_p99_relative": float(np.quantile(np.abs(err[active])/r[active], .99)) if active.any() else None,
            "active_max_relative": float((np.abs(err[active])/r[active]).max()) if active.any() else None,
            "gpu_zero_reference_positive": int(((g <= 0) & active).sum()),
            "reference_zero_leak_pixels": int(((g > 0) & ~active).sum()),
            "reference_zero_leak_energy": float(g[~active].sum()),
            "whole_image_max_absolute": float(np.abs(err).max())}


def score(capture, row, reference_work, output):
    state = L.read_state(capture)
    if row["classification"] != "STATISTICALLY_ELIGIBLE":
        raise ValueError("no total/indirect scoring against ineligible reference")
    if not (state["meta"][:, 3] == 1).all():
        raise ValueError("capture violates BF-P two-sided geometry")
    state_byte_equal = state["sha256"] == row["state_sha256"]
    # Frame counter/probe configuration changes may leave physical transport
    # identical. Require the COMPLETE derived oracle input bytes, not a loose
    # camera tolerance or a selected-pixel equivalence check.
    derived_scene = scene_for_state(state, {"T_B2": 2, "T_B8": 8}[row["transport"]])
    physical_scene_equal = hashlib.sha256(derived_scene.text().encode()).hexdigest() == row["scene_sha256"]
    if not physical_scene_equal:
        raise ValueError("capture/reference complete physical scene identity mismatch")
    spp = row["levels"][-1]["spp"]
    runs = [L.read_sidecar(reference_work / f"o.n{spp}.s{i}.f64") for i in range(4)]
    for i, run in enumerate(runs):
        if run["seed"] != L.N007_SEEDS[i] or run["spp"] != spp:
            raise ValueError("reference replicate identity mismatch")
    files = row["levels"][-1]["all_payload_sha256"]
    for name, sha in files.items():
        if hashlib.sha256((reference_work/name).read_bytes()).hexdigest() != sha:
            raise ValueError("reference bytes changed after qualification")
    ref = np.mean([r["mean"] for r in runs], axis=0)
    values = {}
    image_dir = capture / "gpu" if (capture / "gpu").is_dir() else capture
    if (capture / "frames.json").exists():
        meta = json.loads((capture / "frames.json").read_text())
        required = {"T_B2": 2, "T_B8": 8}[row["transport"]]
        if meta.get("family","pixel-pt") == "pixel-pt" and meta["vertices"] != required:
            raise ValueError("path tracer/reference finite vertex boundary mismatch")
    for component in ("direct", "indirect", "total"):
        g = L.read_pfm(image_dir / f"{component}.pfm") @ LUMA
        r = ref[..., L.COMPONENTS.index(component), :] @ LUMA
        values[component] = metrics(g, r)
        np.save(output.parent / f"{output.stem}.{component}.error.npy", g-r)
    t, i = values["total"], values["indirect"]
    passed = (t["nrmse"] is not None and i["nrmse"] is not None and
              i["signed_sum_bias"] is not None and t["nrmse"] <= .05 and
              i["nrmse"] <= .1 and abs(i["signed_sum_bias"]) <= .05)
    return {"schema": "n010-full-image-hdr-score/1", "cell": row["cell"],
            "transport": row["transport"], "state_sha256": state["sha256"],
            "reference_state_sha256": row["state_sha256"],
            "state_bytes_equal": state_byte_equal,
            "complete_oracle_scene_sha256": row["scene_sha256"],
            "complete_physical_scene_bytes_equal": physical_scene_equal,
            "components": values, "pilot_quality_target": "PASS" if passed else "FAIL",
            "normalization": "whole-image reference RMS; linear luma",
            "scoring_exclusions": 0,
            "capture_directory": str(capture),
            "capture_payload_sha256": {c + ".pfm": hashlib.sha256((image_dir / (c+".pfm")).read_bytes()).hexdigest()
                                       for c in ("direct", "indirect", "total")},
            "superiority_claim": False}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", type=Path, required=True)
    ap.add_argument("--qualification", type=Path, required=True)
    ap.add_argument("--reference-work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError("refuse to overwrite score")
    row = json.loads(a.qualification.read_text())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    result = score(a.capture, row, a.reference_work, a.output)
    result["qualification_sha256"] = hashlib.sha256(a.qualification.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

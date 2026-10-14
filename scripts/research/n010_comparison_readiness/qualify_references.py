#!/usr/bin/env python3
"""N010 locked-state RQMC reference ladder, retaining every level and all seeds."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n008_hdr_oracle"))
sys.path.insert(0, str(ROOT / "scripts/research/n007_reference_validity"))
import n008lib as L
from check_convergence import assess

LEVELS = (8192, 16384, 32768, 65536, 131072, 262144)
NET = ROOT / "out/research/n010-comparison-readiness/sobol16x262144.bin"
BINARY = ROOT / "build/n010-cpu/n010_rqmc_oracle"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scene_for_state(state, vertices):
    sc = L.state_scene(state, vertices)
    # Prospective N010 precision correction: preserve the frame's direction
    # without N008's float32 (origin+forward) cancellation.
    origin = state["camera_pos_near"][:3].astype(np.float64)
    forward = state["camera_forward_far"][:3].astype(np.float64)
    sc.camera.origin = tuple(origin)
    sc.camera.target = tuple(origin + forward)
    return sc


def qualification(lock, selected, work, validation):
    valid = json.loads(validation.read_text())
    if not valid.get("complete") or not valid.get("all_pass"):
        raise ValueError("sampler physical validation not complete/PASS")
    if valid["binary_sha256"] != sha(BINARY) or valid["sobol_table_sha256"] != sha(NET):
        raise ValueError("sampler validation identity mismatch")
    records = []
    for cell in selected:
        cell_spec = lock["cells"][cell]
        state = L.read_state(ROOT / cell_spec["state_directory"])
        if state["sha256"] != cell_spec["state_sha256"]:
            raise ValueError(f"{cell}: locked state mismatch")
        for transport, vertices in (("T_B2", 2), ("T_B8", 8)):
            out = work / f"{cell}_{transport}"
            out.mkdir(parents=True, exist_ok=True)
            sc = scene_for_state(state, vertices)
            scene_path = out / "scene.n008"
            if scene_path.exists() and scene_path.read_text() != sc.text():
                raise ValueError("changed scene under existing acquisition path")
            scene_path.write_text(sc.text())
            manifests, levels = [], []
            for spp in LEVELS:
                prefix = out / f"o.n{spp}"
                meta_path = out / f"n{spp}.meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text())
                    if (meta["binary_sha256"], meta["net_sha256"], meta["scene_sha256"]) != (
                            sha(BINARY), sha(NET), sha(scene_path)):
                        raise ValueError("resume source/input mismatch")
                else:
                    if Path(str(prefix) + ".s0.f64").exists():
                        raise ValueError("partial level retained; inspect before any new acquisition")
                    cmd = [str(BINARY), "--net", str(NET), "--scene", str(scene_path), "--out", str(prefix),
                           "--seeds", ",".join(map(str, L.N007_SEEDS)), "--spp", str(spp)]
                    started = time.monotonic()
                    p = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    meta = json.loads(p.stdout)
                    meta.update(binary_sha256=sha(BINARY), net_sha256=sha(NET),
                                source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                                wall_seconds_diagnostic=time.monotonic()-started)
                    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
                references = [{"seed": seed, "path": str(Path(str(prefix) + f".s{i}.total.pfm").name),
                               "sha256": sha(Path(str(prefix) + f".s{i}.total.pfm"))}
                              for i, seed in enumerate(L.N007_SEEDS)]
                manifests.append({"spp": spp, "references": references})
                manifest = {"schema_version": 1, "source_commit": meta["source_commit"],
                            "scene_sha256": sha(scene_path),
                            "frame_state_sha256": state["sha256"]["frame"], "levels": manifests}
                manifest_path = out / f"screen-n{spp}.json"
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
                screen = assess(manifest_path)
                runs = [L.read_sidecar(Path(str(prefix) + f".s{i}.f64")) for i in range(4)]
                means = np.stack([r["mean"] for r in runs])
                levels.append({"spp": spp, "screen": screen,
                               "geometry_hash_match": meta["geometry_sha256"] == sc.geometry_sha256(),
                               "components_union_positive": {
                                   k: int((means[..., j, :].max(-1) > 0).any(0).sum())
                                   for j, k in enumerate(L.COMPONENTS)},
                               "replicate_means_se_max": float((means.std(0, ddof=1)/2).max()),
                               "all_payload_sha256": {p.name: sha(p) for p in sorted(out.glob(f"o.n{spp}.*"))}})
                row = {"cell": cell, "transport": transport, "state_sha256": state["sha256"],
                       "scene_sha256": sha(scene_path), "levels": levels,
                       "classification": "STATISTICALLY_ELIGIBLE" if screen["status"] == "statistical-screen-pass"
                       and all(l["geometry_hash_match"] for l in levels) else "INELIGIBLE"}
                (out / "qualification.json").write_text(json.dumps(row, indent=2, allow_nan=False) + "\n")
                print(cell, transport, spp, screen["status"], flush=True)
                if row["classification"] == "STATISTICALLY_ELIGIBLE":
                    break
            records.append(row)
    return {"schema": "n010-reference-qualification/1", "cells": records,
            "sampler_validation_sha256": sha(validation), "state_lock_sha256": lock["_sha256"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lock", type=Path, required=True)
    ap.add_argument("--validation", type=Path, required=True)
    ap.add_argument("--cells", nargs="+", required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    lock = json.loads(a.lock.read_text())
    lock["_sha256"] = sha(a.lock)
    result = qualification(lock, a.cells, a.work, a.validation)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")

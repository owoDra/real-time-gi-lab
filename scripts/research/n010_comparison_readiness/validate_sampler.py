#!/usr/bin/env python3
"""N010 sampling validation: reuse independent N008 analytic expected values."""
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
import phase_a_controls as P

NET = ROOT / "out/research/n010-comparison-readiness/sobol16x262144.bin"
BINARY = ROOT / "build/n010-cpu/n010_rqmc_oracle"


def render(res, scene, out, name, spp):
    out.mkdir(parents=True, exist_ok=True)
    scene_path = out / f"{name}.n008"
    if scene_path.exists():
        raise ValueError(f"refuse to overwrite validation {scene_path}")
    scene_path.write_text(scene.text())
    cmd = [str(BINARY), "--net", str(NET), "--scene", str(scene_path),
           "--out", str(out / name), "--seeds", ",".join(map(str, L.N007_SEEDS)), "--spp", str(spp)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    meta = json.loads(proc.stdout)
    meta.update(name=name, geometry_hash_match=meta["geometry_sha256"] == scene.geometry_sha256())
    meta["run_counters"] = [{k: r[k] for k in ("seed", "primary_hits", "shadow_tests", "shadow_blocked",
                                             "backface_absorbed")} for r in meta["runs"]]
    (out / f"{name}.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    res.runs.append(meta)
    runs = [L.read_sidecar(Path(r["prefix"] + ".f64")) for r in meta["runs"]]
    means = np.stack([r["mean"] for r in runs])
    return {"mean": means.mean(0), "se": means.std(0, ddof=1) / 2,
            "per_seed": runs, "meta": meta}


def analytic_gate(res, label, data, comp, expected, mask, tau, allowance=None):
    got = data["mean"][..., L.COMPONENTS.index(comp), :]
    ref = np.broadcast_to(expected, got.shape)
    if comp == "direct" and allowance is not None:
        bound = np.broadcast_to(allowance, got.shape)
        count = int((np.abs(got - ref)[mask] > bound[mask] + 1e-12).sum())
        return res.check(f"{label}:direct:geometric_allowance", count == 0, violations=count)
    g, r = got[mask], ref[mask]
    rel = np.abs(g.mean(0) - r.mean(0)) / np.maximum(np.abs(r.mean(0)), 1e-300)
    nrmse = np.sqrt(np.mean((g - r)**2) / np.mean(r**2))
    return res.check(f"{label}:{comp}:fixed_accuracy",
                     bool((rel <= 0.002).all() and nrmse <= 0.01),
                     per_channel_region_relative_error=rel, nrmse=nrmse)


def no_leak(out):
    res = P.Result("N010-sealed-room", "shared-edge partition: exactly zero; lit room: positive")
    for tag, origin, target in (("dark", (1.5, 1.2, 1.5), (0, 1, -1)),
                                ("lit", (-1.8, 1.2, 1.8), (-0.5, 1, -1))):
        sc = L.Scene(L.Camera(origin, target), max_bounces=8)
        sc.material("wall", P.GRAY)
        for q in P.room_quads(True).values():
            sc.quad("wall", *q)
        sc.point((-1, 1.5, 0.3), (10, 10, 10))
        data = render(res, sc, out, f"sealed-{tag}", 1024)
        if tag == "dark":
            P.check_zero_all(res, "dark", data)
        else:
            res.check("lit:direct_and_total_positive_every_pixel",
                      bool((data["mean"][..., 1, :] > 0).all() and (data["mean"][..., 3, :] > 0).all()))
    return res


def cross_iid(out, rqmc):
    rows = []
    for name in ("A7", "A6b"):
        # Retain identical authored scenes; iid source is N008 unchanged.
        scene = rqmc / f"{name}.n008"
        out.mkdir(parents=True, exist_ok=True)
        prefix = out / name
        if prefix.with_suffix(".meta.json").exists():
            raise ValueError("refuse to overwrite iid control")
        proc = subprocess.run([str(L.oracle_binary()), "--scene", str(scene), "--out", str(prefix),
                               "--seeds", ",".join(map(str, L.N007_SEEDS)), "--spp", "8192"],
                              capture_output=True, text=True, check=True)
        meta = json.loads(proc.stdout)
        (out / f"{name}.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        g = np.mean([L.read_sidecar(Path(str(rqmc / name) + f".s{i}.f64"))["mean"] for i in range(4)], axis=0)
        r = np.mean([L.read_sidecar(Path(r["prefix"] + ".f64"))["mean"] for r in meta["runs"]], axis=0)
        gi, ri = g[..., 2, :], r[..., 2, :]
        rel = np.abs(gi.mean((0, 1)) - ri.mean((0, 1))) / np.abs(ri.mean((0, 1)))
        nrmse = np.sqrt(np.mean((gi-ri)**2) / np.mean(ri**2))
        rows.append({"name": name, "per_channel_mean_relative_difference": rel.tolist(),
                     "nrmse": float(nrmse), "pass": bool((rel <= 0.002).all() and nrmse <= 0.01)})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    P.render = render
    P.check_stat = analytic_gate
    P.STAT_SPP = 8192
    res = []
    def add(result):
        res.append(result.to_json())
        print(result.cid, "PASS" if result.passed else "FAIL", flush=True)
        a.output.write_text(json.dumps({"schema": "n010-sampler-controls/1", "complete": False,
                                       "controls": res}, indent=2) + "\n")
    for fn in (lambda: P.control_a2(a.work / "rqmc"),
               lambda: P.control_a2(a.work / "rqmc", "A2b", "n001_soft", 1),
               lambda: P.control_a4(a.work / "rqmc"),
               lambda: P.control_a8(a.work / "rqmc"),
               lambda: no_leak(a.work / "rqmc"),
               lambda: P.control_a6(a.work / "rqmc"),
               lambda: P.control_a6(a.work / "rqmc", "A10", 1.6),
               lambda: P.control_a7(a.work / "rqmc")):
        add(fn())
    cross = cross_iid(a.work / "iid", a.work / "rqmc")
    result = {"schema": "n010-sampler-controls/1", "complete": True, "controls": res,
              "iid_crosscheck": cross, "all_pass": all(r["pass"] for r in res) and all(r["pass"] for r in cross),
              "binary_sha256": hashlib.sha256(BINARY.read_bytes()).hexdigest(),
              "sobol_table_sha256": hashlib.sha256(NET.read_bytes()).hexdigest(),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "uncertainty": "replicate-means only; no iid SE for digital-net samples"}
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("ALL PASS", result["all_pass"], flush=True)

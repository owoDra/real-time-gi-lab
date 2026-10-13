#!/usr/bin/env python3
"""N008 Phase B: render frozen Renderer target states with the oracle (nested
512..8192 spp ladder, four N007 seeds) and classify each cell per protocol
experiments/002. The statistical screen is the UNCHANGED N007 implementation
(check_convergence.assess / inspect_hdr.inspect) fed with oracle total PFMs."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "n007_reference_validity"))
import n008lib as L  # noqa: E402
from check_convergence import assess  # noqa: E402  (N007, unchanged)

LUMA = np.array((0.2126, 0.7152, 0.0722))
LEVELS = (512, 1024, 2048, 4096, 8192)
STATES = L.ROOT / "out/research/n008-hdr-oracle/phase-b-states"
CELLS = {
    "B1": ("static", "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    "B2": ("camera-motion", "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    "B3": ("light-motion", "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    "B4": ("moving-rigid", "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    "B5": ("deforming", "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    "B6": ("topology-churn", "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    "B7": ("leak-medium", "out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf"),
}
TRANSPORTS = {"T_B2": 2, "T_B8": 8}
# Preregistered expected state hashes (experiments/002).
EXPECTED = {
    "B1": ("77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4", "205c5a6085e555981080b6547ee6b492e387890e9988ee153d22b4096409b801"),
    "B2": ("a3493146e8e11498c3abc5c98ceaed165032a415ddefc4b3308e1f0a5bca46b5", "205c5a6085e555981080b6547ee6b492e387890e9988ee153d22b4096409b801"),
    "B3": ("8f426ee617c07f9c5c026db3725ea21b07dd28059af14bc36616f7e16c15afcd", "205c5a6085e555981080b6547ee6b492e387890e9988ee153d22b4096409b801"),
    "B4": ("77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4", "d70e8344d9ea493b6fa48d918a2f17f118030b91d708d8bb8d78d0f0422fd53d"),
    "B5": ("77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4", "937836c47638066d1107aecf3e634644910437badf666242e32f32c425745364"),
    "B6": ("77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4", "1a5770d411c18111978567919b350aed3ee14921b0a7c2e7b23608017810ea16"),
    "B7": ("64e5bae27e1719d66b4daef559f52309878ffcc6bcc72920c8cad7115df9c949", "945b99545ca9f24c5261f1eccec6eb68ce697169bfb052ffbfba87dca02a2c5b"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render_cell(cid, tname, out_root):
    state_dir = STATES / CELLS[cid][0]
    st = L.read_state(state_dir)
    if (st["sha256"]["frame"], st["sha256"]["geometry"]) != EXPECTED[cid]:
        raise SystemExit(f"{cid}: frozen state hash mismatch")
    sc = L.state_scene(st, TRANSPORTS[tname])
    work = out_root / f"{cid}_{tname}"
    work.mkdir(parents=True, exist_ok=True)
    scene_path = work / "scene.n008"
    scene_path.write_text(sc.text())
    t0 = time.time()
    proc = subprocess.run([str(L.oracle_binary()), "--scene", str(scene_path), "--out", str(work / "o"),
                           "--seeds", ",".join(map(str, L.N007_SEEDS)), "--spp", str(LEVELS[-1]),
                           "--checkpoints", ",".join(map(str, LEVELS[:-1]))], check=True, capture_output=True, text=True)
    meta = json.loads(proc.stdout)
    meta["wall_seconds_diagnostic"] = round(time.time() - t0, 1)
    meta["expected_geometry_sha256"] = sc.geometry_sha256()
    meta["state_sha256"] = st["sha256"]
    (work / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def level_prefix(work: Path, seed_index: int, spp: int) -> Path:
    return work / (f"o.s{seed_index}" + ("" if spp == LEVELS[-1] else f".c{spp}"))


def analyze_cell(cid, tname, out_root, commit):
    work = out_root / f"{cid}_{tname}"
    meta = json.loads((work / "meta.json").read_text())
    scene_sha = sha(L.ROOT / CELLS[cid][1])
    # N007 screen on prefixes of the ladder; stop at the first qualifying pair.
    screen = None
    for n in range(1, len(LEVELS) + 1):
        manifest = {"schema_version": 1, "source_commit": commit, "scene_sha256": scene_sha,
                    "frame_state_sha256": meta["state_sha256"]["frame"], "levels": []}
        for spp in LEVELS[:n]:
            refs = []
            for i, seed in enumerate(L.N007_SEEDS):
                p = Path(str(level_prefix(work, i, spp)) + ".total.pfm")
                refs.append({"seed": seed, "path": p.name, "sha256": sha(p)})
            manifest["levels"].append({"spp": spp, "references": refs})
        mpath = work / f"n007-manifest-{n}.json"
        mpath.write_text(json.dumps(manifest, indent=1))
        screen = assess(mpath)
        if screen["status"] == "statistical-screen-pass":
            break
    # Component diagnostics per level.
    levels = []
    prev_union = None
    for spp in LEVELS:
        runs = [L.read_sidecar(Path(str(level_prefix(work, i, spp)) + ".f64")) for i in range(4)]
        Y = {k: np.stack([r["mean"][..., L.COMPONENTS.index(k), :] @ LUMA for r in runs]) for k in ("direct", "indirect", "total")}
        union = (Y["total"] > 0).any(0)
        row = {"spp": spp}
        for k, y in Y.items():
            row[k] = {"union_positive": int((y > 0).any(0).sum()), "per_seed_positive": [int((s > 0).sum()) for s in y],
                      "peak_y": [float(s.max()) for s in y], "mean_y": [float(s.mean()) for s in y]}
        if prev_union is not None:
            row["zero_to_positive"] = int((union & ~prev_union).sum())
            row["positive_to_zero"] = int((~union & prev_union).sum())
        prev_union = union
        levels.append(row)
    final = [L.read_sidecar(Path(str(level_prefix(work, i, LEVELS[-1])) + ".f64")) for i in range(4)]
    direct = [r["mean"][..., 1, :] for r in final]
    direct_identical = all(np.array_equal(direct[0], d) for d in direct[1:])
    dy = direct[0] @ LUMA
    npx = dy.size
    direct_support = {"positive": int((dy > 0).sum()), "fraction": float((dy > 0).mean()), "peak_y": float(dy.max())}
    direct_signal = direct_support["positive"] >= 64 and direct_support["fraction"] >= 0.01 and direct_support["peak_y"] >= 1e-4
    # Hit diagnostics: primary coverage and back faces of single-sided triangles.
    st = L.read_state(STATES / CELLS[cid][0])
    raw = (work / "o.hits").read_bytes()
    assert raw[:8] == b"N008HIT\0"
    hits = np.frombuffer(raw, dtype=np.dtype([("t", "<f8"), ("tri", "<u4"), ("front", "<u4")]), offset=16)
    hit = hits["t"] >= 0
    single = np.zeros(hits.size, bool)
    single[hit] = st["meta"][hits["tri"][hit], 3] == 0
    back_single = hit & single & (hits["front"] == 0)
    total_final = levels[-1]["total"]
    if screen["status"] == "statistical-screen-pass":
        cls = "STATISTICALLY_ELIGIBLE"
    elif direct_identical and direct_signal:
        cls = "DIRECT_DETERMINISTIC_PROVED"
    elif direct_support["positive"] == 0 and not (total_final["union_positive"] >= 64 and total_final["union_positive"] / npx >= 0.01):
        cls = "NO_SUPPORT"
    else:
        cls = "INELIGIBLE"
    return {"cell": cid, "class_label": CELLS[cid][0], "transport": tname, "classification": cls,
            "n007_screen": screen, "levels": levels, "direct_deterministic_identical_across_seeds": direct_identical,
            "direct_support_8192": direct_support, "direct_signal_thresholds_met": direct_signal,
            "primary_hit_fraction": float(hit.mean()), "primary_backface_single_sided_fraction": float(back_single.mean()),
            "state_sha256": meta["state_sha256"], "scene_asset_sha256": scene_sha,
            "oracle_geometry_sha256": meta["geometry_sha256"], "geometry_hash_match": meta["geometry_sha256"] == meta["expected_geometry_sha256"],
            "scene_file_sha256": meta["scene_sha256"], "wall_seconds_diagnostic": meta["wall_seconds_diagnostic"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("render", "analyze"))
    ap.add_argument("--cells", nargs="*", default=list(CELLS))
    ap.add_argument("--transports", nargs="*", default=list(TRANSPORTS))
    ap.add_argument("--out", default=str(L.ROOT / "out/research/n008-hdr-oracle/phase-b"))
    ap.add_argument("--commit", help="acquisition source commit (analyze)")
    ap.add_argument("--summary")
    a = ap.parse_args()
    out = Path(a.out)
    if a.command == "render":
        for t in a.transports:
            for c in a.cells:
                m = render_cell(c, t, out)
                print(f"{c} {t} rendered in {m['wall_seconds_diagnostic']} s", flush=True)
        return 0
    rows = [analyze_cell(c, t, out, a.commit) for t in a.transports for c in a.cells]
    for r in rows:
        print(f"{r['cell']} {r['transport']} {r['classification']} screen={r['n007_screen']['status']} "
              f"direct+={r['direct_support_8192']['positive']} total_union+={r['levels'][-1]['total']['union_positive']}", flush=True)
    if a.summary:
        Path(a.summary).write_text(json.dumps({"schema": "n008-phase-b/1", "source_commit": a.commit, "cells": rows},
                                              indent=1, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

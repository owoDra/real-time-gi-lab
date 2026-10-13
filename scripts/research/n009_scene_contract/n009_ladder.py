#!/usr/bin/env python3
"""N009 WP-SC: lock the C1-C6 cell states, then render and classify them with the
UNCHANGED N008 Phase B ladder (phase_b_ladder.render_cell / analyze_cell, which
call the unchanged N007 screen). Only the cell tables are N009-specific; they are
installed into the N008 module before its functions run.

  lock     export C1-C6 with n009_state_export and write the lock record
  render   oracle ladder (4 seeds, nested 512-8192 spp) for locked cells
  analyze  classification summary (same schema as N008 result 005)"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "n008_hdr_oracle"))
import n008lib as L  # noqa: E402
import phase_b_ladder as B  # noqa: E402  (N008, unchanged)

SPONZA = "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"
OUT = L.ROOT / "out/research/n009-scene-contract"
STATES = OUT / "states"
CELLS = {
    "C1": ("static", SPONZA),
    "C2": ("camera-motion", SPONZA),
    "C3": ("light-motion", SPONZA),
    "C4": ("moving-rigid", SPONZA),
    "C5": ("deforming", SPONZA),
    "C6": ("topology-churn", SPONZA),
}
EXPORTER = L.ROOT / "build/n009/src/research/n009_scene_contract/n009_state_export"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def install(lock: dict) -> None:
    B.STATES = STATES
    B.CELLS = CELLS
    B.EXPECTED = {c: (v["frame_sha256"], v["geometry_sha256"]) for c, v in lock["cells"].items()}


def do_lock(contract: Path, record: Path) -> None:
    env = dict(os.environ, PHOS_N009_CONTRACT=str(contract))
    cells = {}
    for cid, (regime, scene) in CELLS.items():
        out = STATES / regime
        proc = subprocess.run([str(EXPORTER), "--scene", str(L.ROOT / scene), "--out", str(out), "--regime", regime],
                              check=True, capture_output=True, text=True, env=env)
        info = json.loads(proc.stdout)
        st = L.read_state(out)
        if not info["authored_camera"] or not info["bf_p_two_sided_all"]:
            raise SystemExit(f"{cid}: contract C1/BF-P not active")
        cells[cid] = {"regime": regime, "frame_sha256": st["sha256"]["frame"], "geometry_sha256": st["sha256"]["geometry"],
                      "exporter": info}
    record.write_text(json.dumps({"schema": "n009-state-lock/1", "contract_file": str(contract.relative_to(L.ROOT)),
                                  "contract_sha256": sha(contract), "scene_sha256": sha(L.ROOT / SPONZA),
                                  "exporter_sha256": sha(EXPORTER), "cells": cells}, indent=1) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("lock", "render", "analyze"))
    ap.add_argument("--contract", type=Path)
    ap.add_argument("--lock", type=Path, required=True, help="state lock record (written by lock)")
    ap.add_argument("--cells", nargs="*", default=list(CELLS))
    ap.add_argument("--transports", nargs="*", default=list(B.TRANSPORTS))
    ap.add_argument("--out", type=Path, default=OUT / "ladder")
    ap.add_argument("--commit")
    ap.add_argument("--summary", type=Path)
    a = ap.parse_args()
    if a.command == "lock":
        do_lock(a.contract.resolve(), a.lock)
        print(a.lock.read_text())
        return 0
    lock = json.loads(a.lock.read_text())
    install(lock)
    if a.command == "render":
        for t in a.transports:
            for c in a.cells:
                m = B.render_cell(c, t, a.out)
                print(f"{c} {t} rendered in {m['wall_seconds_diagnostic']} s", flush=True)
        return 0
    rows = [B.analyze_cell(c, t, a.out, a.commit) for t in a.transports for c in a.cells]
    for r in rows:
        print(f"{r['cell']} {r['transport']} {r['classification']} screen={r['n007_screen']['status']} "
              f"direct+={r['direct_support_8192']['positive']} total_union+={r['levels'][-1]['total']['union_positive']}",
              flush=True)
    if a.summary:
        a.summary.write_text(json.dumps({"schema": "n008-phase-b/1", "study": "N009 WP-SC", "source_commit": a.commit,
                                         "state_lock_sha256": sha(a.lock), "cells": rows}, indent=1, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

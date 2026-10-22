#!/usr/bin/env python3
"""Freeze canonical N008 physical source bytes for M001-H02, not oracle images.

Requires original H02 state/asset/receipts. No GPU, Monte Carlo, reference
qualification, score or timing work. A mismatch is a hard error before writing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from audit_h02_evidence import audit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n008_hdr_oracle"))
import n008lib as N008

STATE_SHA = {
    "geometry": "9d7c434202d2c9d14a7b3c4fb024b13cbd5240fc5251c22d3b533f719f968b5c",
    "frame": "70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4",
}
GEOMETRY_HASH = "b40574ad76dbcc8f80250a0b1a1be0313176983b7140e96fdee18f4970ecb6e7"
EXPECTED = {
    2: "0db4c7d6616bf14edd0e5f2378bf9f4e7f95353a6c4b9ee7f2eba2df64ae0bed",
    8: "c572d6f55726aa8898e23f5e03e8ddcc9b9696c64e012102bc48cb74f1416b31",
}


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(work: Path, output: Path) -> dict:
    work, output = work.resolve(), output.resolve()
    if output.exists():
        raise ValueError("refuse previous physical-source output overwrite")
    previous = audit(work, metadata_only=False)  # host's complete retained payload set
    if previous["h02_geometry"]["geometry_sha256"] != STATE_SHA["geometry"] or \
            previous["h02_frame"]["frame_sha256"] != STATE_SHA["frame"]:
        raise ValueError("H02 reference source identity differs from independently audited bytes")
    capture = work / "capture/M001-H02-hwrt"
    state = N008.read_state(capture)
    if state["sha256"] != STATE_SHA:
        raise ValueError("canonical N008 state decoder differs")
    scenes = []
    for bounce in (2, 8):
        s = N008.state_scene(state, max_bounces=bounce)
        data = s.text().encode("utf-8")
        if hash_bytes(data) != EXPECTED[bounce] or s.geometry_sha256() != GEOMETRY_HASH:
            raise ValueError("complete canonical N008 physical-scene identity mismatch")
        scenes.append((bounce, data))
    output.mkdir(parents=True)
    manifest = {
        "schema": "lane-m-m001-h02-reference-scene-input/1",
        "complete": True, "state_sha256": STATE_SHA,
        "n008_source_sha256": hash_bytes(Path(N008.__file__).read_bytes()),
        "physical_eligibility": "NOT_RUN",
        "reference_eligible": False,
        "gpu_executed": False, "oracle_executed": False,
        "quality_scored": False,
        "source_scenes": [
            {"transport": f"T_B{bounce}", "scene_sha256": EXPECTED[bounce],
             "geometry_f64_sha256": GEOMETRY_HASH,
             "filename": f"M001-H02-T_B{bounce}.n008",
             "max_bounces": bounce, "bytes": len(data)}
            for bounce, data in scenes
        ],
        "notes": "Inputs only; no independent statistical convergence, finite-depth GI equivalence, or reference admission."
    }
    for bounce, data in scenes:
        (output / f"M001-H02-T_B{bounce}.n008").write_bytes(data)
    (output / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args = ap.parse_args()
    manifest = prepare(args.work,args.output)
    print(json.dumps({"complete":True,"oracle_executed":False,
                      "reference_eligible":False,
                      "scene_sha256":[x["scene_sha256"] for x in manifest["source_scenes"]]},
                     indent=2))


if __name__ == "__main__":
    main()

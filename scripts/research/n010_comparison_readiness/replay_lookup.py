#!/usr/bin/env python3
"""Replay captured integer aggregation using keys exported by the GPU composite."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n008_hdr_oracle"))
import n008lib as L


def run(capture):
    state = L.read_state(capture)
    n = state["width"] * state["height"]
    work = np.frombuffer((capture / "gpu/probe-work.bin").read_bytes(),
                         dtype=[("key", "<i4", 3), ("cascade", "<u4"), ("ray", "<u4"),
                                ("output", "<u4"), ("surface", "<u4"), ("tile", "<u4"),
                                ("rest", "<f4", 8)])
    fixed = np.frombuffer((capture / "gpu/probe-contributions.bin").read_bytes(),
                          dtype=[("output", "<u4"), ("value", "<u4")])
    if len(work) != len(fixed) or not np.array_equal(work["output"], fixed["output"]):
        raise ValueError("work/contribution output identity mismatch")
    audit_raw = (capture / "gpu/composite-lookup.bin").read_bytes()
    if len(audit_raw) != n * 80:
        raise ValueError("lookup audit size mismatch")
    audit = np.frombuffer(audit_raw, dtype=[("position", "<f4", 4), ("keys", "<i4", (4, 4))])
    sums, counts, owners = defaultdict(int), defaultdict(int), {}
    for item, contribution in zip(work, fixed):
        output = int(item["output"])
        sums[output] += int(contribution["value"])
        counts[output] += 1
        if item["ray"] == 0:
            owners[output] = tuple(map(int, item["key"])) + (int(item["cascade"]),)
    if sums.keys() != owners.keys():
        raise ValueError("missing ray-zero owner")
    key_sums, key_counts = defaultdict(int), defaultdict(int)
    for output, total in sums.items():
        key = owners[output]
        key_sums[key] += (total + counts[output] // 2) // counts[output]
        key_counts[key] += 1
    pred = np.zeros(n, dtype=np.float32)
    for cascade in range(4):
        values = np.array([np.float32(key_sums[tuple(map(int, k))]) /
                           (np.float32(key_counts[tuple(map(int, k))]) * np.float32(65535))
                           if key_counts[tuple(map(int, k))] else np.float32(0)
                           for k in audit["keys"][:, cascade]], dtype=np.float32)
        pred = np.float32(pred + values)
    gpu = L.read_pfm(capture / "gpu/indirect.pfm")[..., 0].ravel()
    err = np.abs(pred.astype(float) - gpu)
    positivity = int(((pred > 0) != (gpu > 0)).sum())
    return {"capture": capture.name, "state_sha256": state["sha256"],
            "audit_sha256": hashlib.sha256(audit_raw).hexdigest(),
            "work_items": len(work), "pixels": n, "scoring_exclusions": 0,
            "max_absolute_error": float(err.max()),
            "positivity_disagreements": positivity, "bit_equal_float32_pixels": int((pred == gpu).sum()),
            "V1": bool(err.max() <= 1e-6 and positivity == 0)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", type=Path, action="append", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    rows = [run(cap) for cap in args.capture]
    args.output.write_text(json.dumps({"schema": "n010-gpu-key-replay/1", "rows": rows}, indent=2) + "\n")
    print(json.dumps(rows, indent=2))

#!/usr/bin/env python3
"""Read the ALREADY captured invalid P1m3b control/reference PFMs. NO GPU rerun.

Do not classify reference-identical as a zero-noise quality pass. Retain
original failed summary and source artifacts; emit additive diagnostic JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from run_p1m1a_canonical_probe_pilot import read_pfm_payload

ROOT = pilot.ROOT / "out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed"
SUMMARY_NAME = "n006-p1m3b-moving-rigid-signed-quality-summary.json"
EVIDENCE_NAME = pilot.EVIDENCE_NAME
OUTPUT_NAME = "n006-p1m3b-reference-forensics.json"
LUMA = (0.2126, 0.7152, 0.0722)


def rgb_diagnostic(payload: bytes) -> dict[str, float | int]:
    if len(payload) != 320 * 180 * 3 * 4:
        raise ValueError("unexpected N006 RGB float32 size")
    pixel_positive = 0
    channel_nonzero = 0
    max_luma = 0.0
    max_abs_channel = 0.0
    channel_sum = 0.0
    nonfinite_count = 0
    negative_count = 0
    vals = struct.iter_unpack("<fff", payload)
    for (r, g, b) in vals:
        if not all(math.isfinite(v) for v in (r, g, b)):
            nonfinite_count += 1
            continue
        if min(r, g, b) < 0:
            negative_count += 1
        positives = sum(v > 0 for v in (r, g, b))
        channel_nonzero += positives
        if positives:
            pixel_positive += 1
        max_abs_channel = max(max_abs_channel, abs(r), abs(g), abs(b))
        max_luma = max(max_luma, sum(v * w for v, w in zip((r,g,b),LUMA)))
        channel_sum += r + g + b
    return {
        "positive_rgb_pixels": pixel_positive,
        "positive_channel_values": channel_nonzero,
        "max_abs_channel": max_abs_channel,
        "max_luminance": max_luma,
        "rgb_channel_sum": channel_sum,
        "nonfinite_rgb_pixels": nonfinite_count,
        "negative_rgb_pixels": negative_count,
    }


def safe_artifact(folder: Path, path: object) -> Path:
    if not isinstance(path, str) or not path:
        raise ValueError("missing reference or image path in renderer evidence")
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("unsafe renderer path")
    target = folder / rel
    if not target.is_file():
        raise FileNotFoundError(target)
    return target


def diagnose(root: Path) -> dict[str, Any]:
    summary_file = root / SUMMARY_NAME
    summary_raw = summary_file.read_bytes()
    summary = json.loads(summary_raw)
    if (summary.get("protocol_version") !=
            "n006-p1m3b-moving-rigid-q8-two-reference-signed-v1" or
        summary.get("status") != "invalid-retained" or
        summary.get("scenario") != "moving-rigid"):
        raise ValueError("not original invalid P1m3b reference result")
    folder = root / "Q8_control_reference"
    raw = (folder / EVIDENCE_NAME).read_bytes()
    evidence = json.loads(raw)
    if (evidence.get("p1m3b_holdout_quality") is not True or
        evidence.get("p1m3_fractional_storage") is not True or
        evidence.get("scenario") != "moving-rigid" or
        evidence.get("p1m1_canonical_token") != 0 or
        evidence.get("reference_generation") != "rendered" or
        len(evidence.get("frames", [])) != 1):
        raise ValueError("renderer evidence unrelated to original Q8 moving-rigid control")
    frame = evidence["frames"][0]
    images: dict[str, Any] = {}
    buffers: dict[str, bytes] = {}
    for key, field in (
        ("Q8_control", frame.get("image")),
        ("N001_reference_A", (frame.get("reference") or {}).get("path")),
        ("N001_reference_B", (frame.get("reference_independent") or {}).get("path")),
    ):
        file = safe_artifact(folder, field)
        payload = read_pfm_payload(file)
        images[key] = {
            "relative_path": str(file.relative_to(root)),
            "whole_PFM_SHA256": hashlib.sha256(file.read_bytes()).hexdigest(),
            **rgb_diagnostic(payload),
        }
        buffers[key] = payload
    a, b = buffers["N001_reference_A"], buffers["N001_reference_B"]
    from run_p1m3b_moving_rigid_signed_quality import rgb_rms
    noise = rgb_rms(a, b)
    return {
        "status": "forensics-only",
        "source_invalid_summary_sha256": hashlib.sha256(summary_raw).hexdigest(),
        "source_renderer_evidence_sha256": hashlib.sha256(raw).hexdigest(),
        "original_git": summary["git"],
        "images": images,
        "reference_A_meta": frame.get("reference"),
        "reference_B_meta": frame.get("reference_independent"),
        "reference_A_and_B_exact_byte_equal": a == b,
        "reference_pair_RGB_RMS": noise,
        "reference_A_all_black": images["N001_reference_A"]["max_abs_channel"] == 0.0,
        "reference_B_all_black": images["N001_reference_B"]["max_abs_channel"] == 0.0,
        "no_new_gpu_or_cpu_reference_run": True,
        "signed_quality": "NOT EVALUATED",
        "P1_predictor_go": False,
        "P2_scheduler_go": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, help="exact already-created failed campaign folder")
    opts = parser.parse_args()
    if opts.root is not None:
        root = opts.root.resolve()
    else:
        candidates = sorted(
            ROOT.glob(f"*/{SUMMARY_NAME}"), reverse=True)
        if not candidates:
            print(f"No historical failed P1m3b capture under {ROOT}", file=sys.stderr)
            return 2
        root = candidates[0].parent
    report = diagnose(root)
    destination = root / OUTPUT_NAME
    destination.write_text(json.dumps(report,indent=2,sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "root": str(root),
        "reference_A_all_black": report["reference_A_all_black"],
        "reference_B_all_black": report["reference_B_all_black"],
        "reference_A_and_B_exact_byte_equal":
            report["reference_A_and_B_exact_byte_equal"],
        "reference_pair_RGB_RMS": report["reference_pair_RGB_RMS"],
        "Q8_control_positive_rgb_pixels":
            report["images"]["Q8_control"]["positive_rgb_pixels"],
        "diagnostic_json": str(destination),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"P1m3b offline reference forensics failed: {exc}",file=sys.stderr)
        raise SystemExit(1)

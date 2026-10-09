#!/usr/bin/env python3
"""N006 P1i: 10 frozen HWRT/software x Lane-E scenario canonical correctness cases."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot

PROTOCOL = "n006-p1i-cross-backend-correctness-v1"
VARIANTS = ("lane-e-final-hwrt", "lane-e-final-software")
SCENARIOS = (
    "static", "camera-motion", "light-motion",
    "moving-rigid", "deforming-control",
)
MATRIX = tuple((variant, scenario) for variant in VARIANTS for scenario in SCENARIOS)
GPU_PROTOTYPE_KEY_CAPACITY = 8192


def validate(
    raw: dict[str, Any], directory: Path, gpu: str,
    variant: str, scenario: str,
) -> dict[str, Any]:
    if (variant, scenario) not in MATRIX:
        raise ValueError("P1i case not in frozen matrix")
    if (
        raw.get("protocol_version") != "n006-p1-intervention-v1"
        or raw.get("variant") != variant
        or raw.get("scenario") != scenario
        or raw.get("mode") != "current"
        or raw.get("reference_generation") != "skipped"
        or raw.get("source_warmup_frames") != 32
        or raw.get("device", {}).get("name") != gpu
        or raw.get("source", {}).get("internal_correctness") is not True
    ):
        raise ValueError("P1i source/backend/protocol mismatch")
    frames = raw.get("frames")
    if not isinstance(frames, list) or len(frames) != 2:
        raise ValueError("P1i expected exactly two target frames")
    baseline, candidate = frames
    for idx, frame in enumerate(frames):
        stats = frame.get("stats", {})
        extra = frame.get("extra", {})
        if (
            frame.get("index") != idx
            or frame.get("motion_fraction") != 1.0
            or frame.get("owner_budget") != 0
            or frame.get("internal_correctness") is not True
            or frame.get("hit_diagnostics", {}).get("substantive_mismatches") != 0
            or stats.get("overflow") != 0
            or stats.get("storage_failures") != 0
            or not isinstance(stats.get("visible_owners"), int)
            or stats["visible_owners"] <= 0
            or extra.get("base_prefix_correct") is not True
            or extra.get("extra_work_correct") is not True
            or extra.get("extra_rays_traced") != 0
            or extra.get("gpu_hash_probe", {}).get("executed") is not False
        ):
            raise ValueError(f"P1i invalid renderer frame {idx}")
    original = baseline["stats"]
    actual = candidate["stats"]
    original_owners = original["visible_owners"]
    original_outputs = original_owners * 4
    original_rays = original_outputs * 8
    if (original.get("outputs") != original_outputs or
        original.get("work_items") != original_rays or
        original.get("storage_updates") != original_outputs or
        baseline["extra"].get("canonical", {}).get("executed") is not False):
        raise ValueError("P1i baseline has unexpected original ray counts")
    if actual.get("visible_owners") != original_owners:
        raise ValueError("P1i source/canonical visible-owner count differs")

    hist = candidate["extra"].get("canonical", {})
    keys = hist.get("unique_by_cascade")
    if (not hist.get("executed") or
        not isinstance(keys, list) or len(keys) != 4 or
        any(not isinstance(x, int) or x < 0 for x in keys)):
        raise ValueError("P1i missing canonical per-cascade output keys")
    unique = sum(keys)
    expected_duplicates = original_outputs - unique
    if (
        not 1 <= unique <= min(original_outputs, GPU_PROTOTYPE_KEY_CAPACITY)
        or actual.get("outputs") != unique
        or actual.get("work_items") != unique * 8
        or actual.get("storage_updates") != unique
        or hist.get("original_work_items") != original_rays
        or hist.get("original_outputs") != original_outputs
        or hist.get("canonical_work_items") != unique * 8
        or hist.get("canonical_outputs") != unique
        or hist.get("duplicates") != expected_duplicates
        or hist.get("invalid_keys") != 0
        or hist.get("failed_inserts") != 0
        or hist.get("index_overflows") != 0
        or hist.get("owner_weight_errors") != 0
        or hist.get("weighted_owner_total") != original_outputs
    ):
        raise ValueError("P1i canonical GPU hash/multiplicity/output invariant failed")
    if any(not isinstance(hist.get(key), (int, float)) or
           not math.isfinite(hist[key]) or hist[key] <= 0
           for key in ("total_canonical_gpu_us", "owner_weight_storage_gpu_us")):
        raise ValueError("P1i missing GPU canonical/weighted-storage timestamps")

    hashes = []
    for idx, frame in enumerate(frames):
        rel = Path(frame.get("image", ""))
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("P1i untrusted PFM path")
        file = directory / rel
        if not file.is_file():
            raise ValueError(f"P1i missing raw PFM for frame {idx}")
        hashes.append(hashlib.sha256(file.read_bytes()).hexdigest())
    if hashes[0] != hashes[1]:
        raise ValueError(f"P1i PFM mismatch: baseline={hashes[0]}, candidate={hashes[1]}")
    return {
        "status": "pass",
        "variant": variant, "scenario": scenario,
        "owners": original_owners,
        "baseline_ray_work_items": original_rays,
        "canonical_ray_work_items": unique * 8,
        "unique_probe_cascade_keys": keys,
        "original_outputs": original_outputs,
        "canonical_outputs": unique,
        "duplicate_owner_outputs": expected_duplicates,
        "ray_reduction_fraction": 1 - unique / original_outputs,
        "byte_identical_pfm_sha256": hashes[0],
        "canonical_build_gpu_us": hist["total_canonical_gpu_us"],
        "owner_weight_gpu_us_nested": hist["owner_weight_storage_gpu_us"],
        "additional_scratch_bytes": hist.get("scratch_bytes"),
        "complete_gi_current_gpu_us": baseline["timing_us"]["complete_gi_gpu"],
        "complete_gi_canonical_gpu_us": candidate["timing_us"]["complete_gi_gpu"],
        "performance_claim": (
            "Sequential cold targets; GPU times are descriptive, "
            "NOT evidence of matched throughput improvement."),
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run 'mise run build'")
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza scene missing/changed")
    gpu = cfg["target_gpu"]
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1i-cross-backend" /
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    dest.mkdir(parents=True, exist_ok=False)
    summary_file = dest / "n006-p1i-cross-backend-summary.json"
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL,
        "status": "in-progress",
        "formal": False,
        "gpu": gpu,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "scene_sha256": cfg["baseline"]["scene_sha256"],
        "matrix": [{"variant": v, "scenario": s} for v,s in MATRIX],
        "results": [], "failures": [], "reference_generated": False,
    }
    def checkpoint() -> None:
        summary_file.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    checkpoint()
    for index, (variant, scenario) in enumerate(MATRIX):
        output = dest / f"case-{index:02d}-{variant}-{scenario}"
        output.mkdir(parents=True, exist_ok=False)
        command = [
            "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
            str(pilot.BINARY), "--scene", str(scene),
            "--artifact-dir", str(output),
            "--scenario", scenario, "--variant", variant,
            "--mode", "current", "--source-warmup-frames", "32",
            "--target-frames", "2", "--motion-fractions", "1,1",
            "--owner-budgets", "0,0", "--skip-reference",
            "--canonical-probe-pilot", "--canonical-matrix-case",
        ]
        try:
            process = subprocess.run(command, cwd=pilot.ROOT,
                                     capture_output=True, text=True, check=False)
            (output / "stdout.log").write_text(process.stdout, encoding="utf-8")
            (output / "stderr.log").write_text(process.stderr, encoding="utf-8")
            if process.returncode:
                raise RuntimeError(
                    f"renderer exit {process.returncode}; see {output / 'stderr.log'}")
            evidence_file = output / pilot.EVIDENCE_NAME
            raw = json.loads(evidence_file.read_text(encoding="utf-8"))
            case = validate(raw, output, gpu, variant, scenario)
            case["case_index"] = index
            case["raw_evidence_sha256"] = hashlib.sha256(
                evidence_file.read_bytes()).hexdigest()
            result["results"].append(case)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            result["failures"].append({
                "case_index": index, "variant": variant,
                "scenario": scenario, "error": str(error),
                "stderr": str(output / "stderr.log"),
            })
            result["status"] = "invalid-retained"
            checkpoint()
            raise
        checkpoint()
    result["status"] = "complete"
    result["all_cases_byte_identical"] = True
    checkpoint()
    print(json.dumps({
        "status": result["status"],
        "completed_cases": len(result["results"]),
        "summary": str(summary_file),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f"N006 P1i cross-backend pilot failed: {error}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""N006 P1g: verify true compact-ray HWRT work and byte-exact image vs baseline."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

import run_p1_pilot as pilot
import run_p1d_hash_cost as p1d
from audit_p1a_images import n001_contract

PROTOCOL = "n006-p1g-canonical-probe-v1"
CANONICAL_COUNT = sum(p1d.EXPECTED_KEYS)
BASE_RAYS = p1d.EXPECTED_OWNER_COUNT * 4 * 8
CANONICAL_RAYS = CANONICAL_COUNT * 8


def validate(data: dict[str, Any], gpu: str) -> dict[str, Any]:
    if (data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("mode") != "current" or
        data.get("scenario") != "deforming-control" or
        data.get("source_warmup_frames") != 32 or
        data.get("reference_generation") != "skipped" or
        data.get("device", {}).get("name") != gpu or
        not data.get("source", {}).get("internal_correctness")):
        raise ValueError("wrong P1g source/protocol/scenario/device")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != 2:
        raise ValueError("P1g requires exactly two target frames")
    baseline, candidate = frames
    for idx, frame in enumerate(frames):
        if (frame.get("index") != idx or
            frame.get("motion_fraction") != 1 or
            frame.get("owner_budget") != 0 or
            frame.get("internal_correctness") is not True or
            frame.get("stats", {}).get("visible_owners") != p1d.EXPECTED_OWNER_COUNT or
            frame.get("stats", {}).get("overflow") != 0 or
            frame.get("stats", {}).get("storage_failures") != 0 or
            frame.get("hit_diagnostics", {}).get("substantive_mismatches") != 0 or
            frame.get("extra", {}).get("base_prefix_correct") is not True or
            frame.get("extra", {}).get("extra_work_correct") is not True or
            frame.get("extra", {}).get("extra_rays_traced") != 0):
            raise ValueError(f"P1g frame {idx} invalid")
    if (baseline["stats"]["work_items"] != BASE_RAYS or
        baseline["stats"]["outputs"] != p1d.EXPECTED_OWNER_COUNT * 4 or
        baseline["extra"]["canonical"]["executed"] is not False):
        raise ValueError("original current ray work is not frozen baseline")
    canonical = candidate["extra"]["canonical"]
    if (not canonical.get("executed") or
        candidate["stats"]["work_items"] != CANONICAL_RAYS or
        candidate["stats"]["outputs"] != CANONICAL_COUNT or
        canonical.get("canonical_work_items") != CANONICAL_RAYS or
        canonical.get("canonical_outputs") != CANONICAL_COUNT or
        canonical.get("original_work_items") != BASE_RAYS or
        canonical.get("original_outputs") != p1d.EXPECTED_OWNER_COUNT * 4 or
        canonical.get("duplicates") != sum(p1d.EXPECTED_DUPLICATES) or
        list(canonical.get("unique_by_cascade", [])) != list(p1d.EXPECTED_KEYS) or
        canonical.get("invalid_keys") != 0 or
        canonical.get("failed_inserts") != 0 or
        canonical.get("index_overflows") != 0 or
        canonical.get("owner_weight_errors") != 0 or
        canonical.get("weighted_owner_total") != p1d.EXPECTED_OWNER_COUNT * 4 or
        candidate["stats"].get("storage_updates") != CANONICAL_COUNT):
        raise ValueError("actual GPU canonicalization did not meet frozen work/storage count")
    if (baseline["stats"].get("storage_updates") != p1d.EXPECTED_OWNER_COUNT * 4):
        raise ValueError("original storage updates changed")
    stage = float(canonical["total_canonical_gpu_us"])
    weight_stage = float(canonical["owner_weight_storage_gpu_us"])
    if not math.isfinite(weight_stage) or weight_stage <= 0:
        raise ValueError("invalid owner-weighted storage GPU time")
    if not math.isfinite(stage) or stage <= 0:
        raise ValueError("invalid canonical GPU work stage time")
    if candidate["extra"]["gpu_hash_probe"].get("executed"):
        raise ValueError("P1g must not also execute P1d hash stage")
    return {
        "original_ray_work_items": BASE_RAYS,
        "canonical_ray_work_items": CANONICAL_RAYS,
        "original_owner_outputs": p1d.EXPECTED_OWNER_COUNT * 4,
        "canonical_unique_outputs": CANONICAL_COUNT,
        "ray_count_reduction_fraction": 1 - CANONICAL_RAYS / BASE_RAYS,
        "hash_duplicate_keys": canonical["duplicates"],
        "canonical_gpu_stage_us": stage,
        "owner_weight_storage_gpu_us": weight_stage,
        "original_owner_count_reconstructed": canonical["weighted_owner_total"],
        "canonical_scratch_bytes": canonical["scratch_bytes"],
        "original_complete_gi_gpu_us":
            float(baseline["timing_us"]["complete_gi_gpu"]),
        "candidate_complete_gi_gpu_us":
            float(candidate["timing_us"]["complete_gi_gpu"]),
        "timing_claim": ("Two sequential target frames, first possibly cold geometry "
                         "maintenance. Descriptive timings, NOT a controlled A/B speedup."),
    }


def image_difference(original, candidate) -> dict[str, Any]:
    if original.width != candidate.width or original.height != candidate.height:
        raise ValueError("P1g images have different dimensions")
    a, b = original.pixels, candidate.pixels
    expected = original.width * original.height * 3
    if len(a) != expected or len(b) != expected:
        raise ValueError("unexpected P1g image RGB channel count")
    changed_channels = 0
    changed_pixels = 0
    sum_squares = 0.0
    max_absolute_delta = 0.0
    significant_channels = 0
    for pixel in range(original.width * original.height):
        changed = False
        for channel in range(3):
            index = pixel * 3 + channel
            av, bv = float(a[index]), float(b[index])
            if not math.isfinite(av) or not math.isfinite(bv):
                raise ValueError("nonfinite P1g image value")
            delta = av - bv
            if delta != 0:
                changed = True
                changed_channels += 1
                max_absolute_delta = max(max_absolute_delta, abs(delta))
                sum_squares += delta * delta
                if abs(delta) > 1e-6:
                    significant_channels += 1
        if changed:
            changed_pixels += 1
    return {
        "changed_pixels": changed_pixels,
        "changed_channels": changed_channels,
        "fraction_of_pixels_changed":
            changed_pixels / (original.width * original.height),
        "max_absolute_rgb_channel_delta": max_absolute_delta,
        "rgb_rms_delta": math.sqrt(sum_squares / expected),
        "channels_absolute_delta_above_1e-6": significant_channels,
        "width": original.width, "height": original.height,
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run 'mise run build'")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza scene changed or absent")
    out = (pilot.ROOT / "out/research/n006-interval-aware-allocation/p1g-canonical"
           / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True, exist_ok=False)
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress", "formal": False,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "gpu": config["target_gpu"],
        "scenario": "stable-topology-deforming", "reference_generated": False,
        "scene_sha256": config["baseline"]["scene_sha256"],
    }
    dst = out / "n006-p1g-canonical-summary.json"

    def write() -> None:
        dst.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write()

    command = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY), "--scene", str(scene), "--artifact-dir", str(out),
        "--scenario", "deforming-control", "--mode", "current",
        "--source-warmup-frames", "32", "--target-frames", "2",
        "--owner-budgets", "0,0", "--motion-fractions", "1,1",
        "--skip-reference", "--canonical-probe-pilot",
    ]
    proc = subprocess.run(
        command, cwd=pilot.ROOT, capture_output=True, text=True, check=False)
    (out / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        result.update({"status": "incomplete-error-retained",
                       "error": f"renderer exit {proc.returncode}; inspect stderr.log"})
        write()
        raise RuntimeError(result["error"])
    data = json.loads((out / pilot.EVIDENCE_NAME).read_text(encoding="utf-8"))
    detail = validate(data, config["target_gpu"])
    frames = data["frames"]
    files = [out / f["image"] for f in frames]
    for file in files:
        if not file.is_file() or not file.resolve().is_relative_to(out.resolve()):
            raise RuntimeError("missing/out-of-directory GPU PFM")
    original_digest, canonical_digest = [pilot.sha256(x) for x in files]
    if original_digest != canonical_digest:
        delta = image_difference(
            n001_contract.read_pfm(files[0]),
            n001_contract.read_pfm(files[1]))
        result.update({"status": "invalid-image-mismatch",
                       "current_image_sha256": original_digest,
                       "canonical_image_sha256": canonical_digest,
                       "image_difference": delta,
                       "results": detail})
        write()
        raise RuntimeError(
            "P1g image differs from original current render; "
            f"{delta['changed_pixels']} changed pixels; preserved diagnostic")
    result.update({
        "status": "complete", "image_sha256": original_digest,
        "bit_identical_gpu_image": True, "results": detail,
        "raw_candidate_evidence": pilot.EVIDENCE_NAME,
    })
    write()
    print(json.dumps({
        "status": result["status"],
        "true_gpu_ray_work_reduction": detail["ray_count_reduction_fraction"],
        "original_ray_count": BASE_RAYS,
        "canonical_ray_count": CANONICAL_RAYS,
        "image_sha256": original_digest,
        "summary": str(dst),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f"N006 P1g canonical pilot failed: {error}", file=sys.stderr)
        raise SystemExit(1)

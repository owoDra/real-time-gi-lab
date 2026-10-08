#!/usr/bin/env python3
"""N006 P1e: prospective same-process A/B timing-boundary diagnostic."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as p
import run_p1d_hash_cost as p1d

PROTOCOL = "n006-p1e-disjoint-timing-v1"
MASK = "011001100110"
STAGES = (
    "primary_visibility_gpu", "renderer_depth_gpu", "frame_init_gpu",
    "visibility_reuse_gpu", "producer_gpu", "ray_prepare_gpu",
    "traversal_gpu", "radiance_gpu", "merge_gpu", "storage_update_gpu",
    "invalidation_gpu", "resolve_gpu", "traversal_maintenance_gpu",
)


def timing(frame: dict[str, Any], active: bool) -> dict[str, float]:
    values = frame["timing_us"]
    for key in (*STAGES, "complete_gi_gpu", "complete_renderer_gpu", "composite_gpu"):
        v = values.get(key)
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"missing/invalid disjoint GPU timing: {key}")
    extra = frame["extra"]
    probe = extra["gpu_hash_probe"]
    if bool(probe["executed"]) != active:
        raise ValueError("wrong per-frame hash flag")
    if active:
        p1d.validate_hash(probe)
    hash_gpu = float(probe["complete_hash_gpu_us"]) if active else 0.0
    recomputed = sum(float(values[x]) for x in STAGES) + hash_gpu
    full = float(values["complete_gi_gpu"])
    if abs(recomputed - full) > 1.0:
        raise ValueError(
            f"non-overlapping GPU stage total differs from complete GI: "
            f"sum={recomputed} complete={full}")
    if abs(float(values["complete_renderer_gpu"]) - full -
           float(values["composite_gpu"])) > 1.0:
        raise ValueError("composite and complete renderer timestamps inconsistent")
    return {**{k: float(values[k]) for k in STAGES},
            "hash_gpu": hash_gpu, "complete_gi_gpu": full,
            "complete_renderer_gpu": float(values["complete_renderer_gpu"]),
            "composite_gpu": float(values["composite_gpu"]),
            "stage_sum_gpu": recomputed, "stage_closure_error_gpu": recomputed - full,
            "dynamic_update_wall_cpu_only": float(values["dynamic_update_wall"])}


def collect(data: dict[str, Any], directory: Path, expected_gpu: str) -> dict[str, Any]:
    if (data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("device", {}).get("name") != expected_gpu or
        data.get("mode") != "current" or
        data.get("scenario") != "deforming-control" or
        data.get("source_warmup_frames") != 32 or
        data.get("reference_generation") != "skipped" or
        not data.get("source", {}).get("internal_correctness")):
        raise ValueError("wrong P1e source/scene/renderer evidence")
    frames = data.get("frames", [])
    if len(frames) != len(MASK):
        raise ValueError("incomplete P1e 12-frame target output")
    results = []
    baseline_digest = None
    for index, frame in enumerate(frames):
        active = MASK[index] == "1"
        extra = frame["extra"]
        stats = frame["stats"]
        if (frame.get("index") != index or
            not frame.get("internal_correctness") or
            frame.get("motion_fraction") != 1 or
            frame.get("owner_budget") != 0 or
            not extra.get("base_prefix_correct") or
            not extra.get("extra_work_correct") or
            extra.get("extra_rays_traced") != 0 or
            frame.get("hit_diagnostics", {}).get("substantive_mismatches") != 0 or
            stats.get("overflow") != 0 or
            stats.get("storage_failures") != 0 or
            stats.get("visible_owners") != p1d.EXPECTED_OWNER_COUNT or
            stats.get("work_items") != p1d.EXPECTED_OWNER_COUNT * 32):
            raise ValueError(f"P1e frame {index} is invalid or different")
        path = Path(frame["image"])
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe image path")
        rgb = directory / path
        if not rgb.is_file():
            raise ValueError(f"missing output image {rgb}")
        digest = hashlib.sha256(rgb.read_bytes()).hexdigest()
        if baseline_digest is None:
            baseline_digest = digest
        elif digest != baseline_digest:
            raise ValueError(f"target frame {index} has different PFM bytes")
        timings = timing(frame, active)
        results.append({
            "index": index,
            "hash_enabled": active,
            "image_sha256": digest,
            "gpu_timing": timings,
            "hash_probe": extra["gpu_hash_probe"] if active else None,
        })
    pairs = []
    for index in range(0, len(results), 2):
        left, right = results[index:index+2]
        c = right if left["hash_enabled"] else left
        h = left if left["hash_enabled"] else right
        if c["hash_enabled"] or not h["hash_enabled"]:
            raise ValueError(f"pair {index // 2} has invalid A/B order")
        differences = {
            key: h["gpu_timing"][key] - c["gpu_timing"][key]
            for key in (*STAGES, "hash_gpu", "complete_gi_gpu",
                        "complete_renderer_gpu", "composite_gpu",
                        "dynamic_update_wall_cpu_only")
        }
        pairs.append({
            "pair_index": index // 2,
            "order": ["hash" if x["hash_enabled"] else "current" for x in (left,right)],
            "current_frame_index": c["index"],
            "hash_frame_index": h["index"],
            "delta_gpu_us": differences,
        })
    return {
        "protocol_version": PROTOCOL,
        "status": "complete",
        "formal": False,
        "gpu": expected_gpu,
        "hash_mask": MASK,
        "image_sha256": baseline_digest,
        "frames": results,
        "pairs": pairs,
        "median_hash_stage_us": statistics.median(
            x["gpu_timing"]["hash_gpu"] for x in results if x["hash_enabled"]),
        "median_complete_gi_delta_us": statistics.median(
            x["delta_gpu_us"]["complete_gi_gpu"] for x in pairs),
        "note": ("Same-process diagnostic only. GPU stage sums are disjoint; "
                 "CPU dynamic wall is not included. No rays were removed."),
    }


def main() -> int:
    head = p.require_clean_branch()
    if not p.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run 'mise run build'")
    config = json.loads(p.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = p.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or p.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza asset digest mismatch")
    out = (p.ROOT / "out/research/n006-interval-aware-allocation/p1e-timing"
           / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True, exist_ok=False)
    command = [
        "bash", str(p.ROOT / "scripts/run_with_vulkan.sh"),
        str(p.BINARY), "--scene", str(scene),
        "--artifact-dir", str(out), "--scenario", "deforming-control",
        "--mode", "current", "--source-warmup-frames", "32",
        "--target-frames", "12", "--hash-frame-pattern", MASK,
        "--skip-reference",
    ]
    proc = subprocess.run(
        command, cwd=p.ROOT, capture_output=True, text=True, check=False)
    (out / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(
            f"P1e renderer failed (exit {proc.returncode}); see {out / 'stderr.log'}")
    evidence = json.loads((out / p.EVIDENCE_NAME).read_text(encoding="utf-8"))
    result = collect(evidence, out, config["target_gpu"])
    result["git"] = {"head": head, "dirty": False, "branch": p.EXPECTED_BRANCH}
    result["scene_sha256"] = config["baseline"]["scene_sha256"]
    output = out / "n006-p1e-timing-summary.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "complete", "pairs": 6,
        "median_hash_stage_us": result["median_hash_stage_us"],
        "median_complete_gi_delta_us": result["median_complete_gi_delta_us"],
        "summary": str(output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as err:
        print(f"N006 P1e timing diagnostic failed: {err}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""N006 P1h: frozen matched-state canonical vs current performance pilot."""
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

import run_p1_pilot as pilot
import run_p1d_hash_cost as p1d
from run_p1e_timing import STAGES

PROTOCOL = "n006-p1h-matched-canonical-performance-v1"
MASK = "011001100110"
PROCESSES = 3
TARGET_STATE_WARMUPS = 8
SOURCE_WARMUPS = 32
EXPECTED_IMAGE_SHA256 = "79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861"
EXPECTED_RAYS = p1d.EXPECTED_OWNER_COUNT * 32
EXPECTED_OUTPUTS = p1d.EXPECTED_OWNER_COUNT * 4
EXPECTED_CANONICAL_KEYS = sum(p1d.EXPECTED_KEYS)
EXPECTED_CANONICAL_RAYS = EXPECTED_CANONICAL_KEYS * 8
WORK_STAGES = (
    "ray_prepare_gpu", "traversal_gpu", "radiance_gpu", "merge_gpu",
    "storage_update_gpu", "invalidation_gpu", "resolve_gpu",
)


def finite_timing(timing: dict[str, Any], key: str) -> float:
    value = timing.get(key)
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
        or not math.isfinite(value) or value < 0):
        raise ValueError(f"nonfinite/missing P1h GPU time: {key}")
    return float(value)


def validate_frame(
    frame: dict[str, Any], index: int, directory: Path,
    expected_image: str,
) -> dict[str, Any]:
    canonical_mode = MASK[index] == "1"
    extra = frame.get("extra", {})
    stats = frame.get("stats", {})
    hist = extra.get("canonical", {})
    hit = frame.get("hit_diagnostics", {})
    if (
        frame.get("index") != index
        or frame.get("motion_fraction") != 1.0
        or frame.get("owner_budget") != 0
        or frame.get("internal_correctness") is not True
        or hit.get("substantive_mismatches") != 0
        or stats.get("visible_owners") != p1d.EXPECTED_OWNER_COUNT
        or stats.get("overflow") != 0
        or stats.get("storage_failures") != 0
        or stats.get("topology_mutations") != 0
        or stats.get("moved_primitives") != 796
        or extra.get("base_prefix_correct") is not True
        or extra.get("extra_work_correct") is not True
        or extra.get("extra_rays_traced") != 0
        or extra.get("gpu_hash_probe", {}).get("executed") is not False
        or hist.get("executed") is not canonical_mode
    ):
        raise ValueError(f"P1h frame {index} failed renderer/protocol correctness")
    expected_ray_count = EXPECTED_CANONICAL_RAYS if canonical_mode else EXPECTED_RAYS
    expected_outputs = EXPECTED_CANONICAL_KEYS if canonical_mode else EXPECTED_OUTPUTS
    if (stats.get("work_items") != expected_ray_count
        or stats.get("outputs") != expected_outputs
        or stats.get("storage_updates") != expected_outputs
    ):
        raise ValueError(f"P1h frame {index} actual ray/output/storage counts wrong")
    if canonical_mode:
        if (
            hist.get("original_work_items") != EXPECTED_RAYS
            or hist.get("original_outputs") != EXPECTED_OUTPUTS
            or hist.get("canonical_work_items") != EXPECTED_CANONICAL_RAYS
            or hist.get("canonical_outputs") != EXPECTED_CANONICAL_KEYS
            or hist.get("duplicates") != sum(p1d.EXPECTED_DUPLICATES)
            or hist.get("unique_by_cascade") != list(p1d.EXPECTED_KEYS)
            or hist.get("invalid_keys") != 0
            or hist.get("failed_inserts") != 0
            or hist.get("index_overflows") != 0
            or hist.get("owner_weight_errors") != 0
            or hist.get("weighted_owner_total") != EXPECTED_OUTPUTS
            or hist.get("scratch_bytes") != 8421464
        ):
            raise ValueError(f"P1h frame {index} has invalid canonical GPU hash or weights")

    source = frame.get("image", "")
    relative = Path(source)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"P1h frame {index} image path escapes output root")
    filename = directory / relative
    if not filename.is_file():
        raise ValueError(f"P1h frame {index} PFM missing: {filename}")
    digest = hashlib.sha256(filename.read_bytes()).hexdigest()
    if digest != expected_image:
        raise ValueError(f"P1h frame {index} changed original frozen HDR image bytes")

    times = frame.get("timing_us", {})
    if not isinstance(times, dict):
        raise ValueError(f"P1h frame {index} missing GPU timing")
    numbers = {key: finite_timing(times, key) for key in (
        *STAGES, "complete_gi_gpu", "complete_renderer_gpu", "composite_gpu",
        "dynamic_update_wall")}
    if numbers["traversal_maintenance_gpu"] != 0.0:
        raise ValueError(f"P1h frame {index} unexpectedly rebuilds dynamic geometry")
    canonical_build = 0.0
    owner_restore = 0.0
    if canonical_mode:
        canonical_build = finite_timing(hist, "total_canonical_gpu_us")
        owner_restore = finite_timing(hist, "owner_weight_storage_gpu_us")
        if (canonical_build == 0 or owner_restore == 0
            or owner_restore > numbers["storage_update_gpu"] + 0.000001):
            raise ValueError(f"P1h frame {index} invalid canonical timing overlap")
    total_stages = sum(numbers[key] for key in STAGES) + canonical_build
    if abs(total_stages - numbers["complete_gi_gpu"]) > 1.0:
        raise ValueError(
            f"P1h frame {index} missing/overlapping GPU stage: "
            f"sum={total_stages}, total={numbers['complete_gi_gpu']}")
    if abs(
        numbers["complete_renderer_gpu"]
        - numbers["complete_gi_gpu"] - numbers["composite_gpu"]
    ) > 1.0:
        raise ValueError(f"P1h frame {index} composite timing closure failed")
    # Disjoint GPU subtotal affected by dedup: owner restore is already nested
    # inside storage_update_gpu and MUST NOT be counted a second time.
    affected_subtotal = canonical_build + sum(numbers[s] for s in WORK_STAGES)
    return {
        "index": index,
        "canonical": canonical_mode,
        "image_sha256": digest,
        "actual_gpu_rays": expected_ray_count,
        "actual_gpu_outputs": expected_outputs,
        "complete_gi_gpu_us": numbers["complete_gi_gpu"],
        "complete_renderer_gpu_us": numbers["complete_renderer_gpu"],
        "primary_visibility_gpu_us": numbers["primary_visibility_gpu"],
        "post_producer_gi_work_gpu_us": affected_subtotal,
        "canonical_build_gpu_us": canonical_build,
        "owner_restore_gpu_us_nested_in_storage_update": owner_restore,
        "gpu_stage_closure_error_us": total_stages - numbers["complete_gi_gpu"],
        "gpu_us": {k: numbers[k] for k in STAGES},
    }


def audit_process(data: dict[str, Any], directory: Path, gpu: str) -> dict[str, Any]:
    if (
        data.get("protocol_version") != "n006-p1-intervention-v1"
        or data.get("scenario") != "deforming-control"
        or data.get("mode") != "current"
        or data.get("device", {}).get("name") != gpu
        or data.get("reference_generation") != "skipped"
        or data.get("source_warmup_frames") != SOURCE_WARMUPS
        or data.get("source", {}).get("internal_correctness") is not True
    ):
        raise ValueError("P1h wrong source process protocol/GPU/scene")
    warmup = data.get("target_state_warmup", {})
    if (
        warmup.get("frames") != TARGET_STATE_WARMUPS
        or warmup.get("correct") is not True
        or warmup.get("last_traversal_maintenance_gpu") != 0
        or warmup.get("last_visible_owners") != p1d.EXPECTED_OWNER_COUNT
        or warmup.get("last_work_items") != EXPECTED_RAYS
    ):
        raise ValueError("P1h target-state warmup did not stabilize")
    raw = data.get("frames")
    if not isinstance(raw, list) or len(raw) != len(MASK):
        raise ValueError("P1h requires exactly 12 target frames per fresh process")
    frames = [validate_frame(f, i, directory, EXPECTED_IMAGE_SHA256)
              for i, f in enumerate(raw)]
    pairs = []
    for i in range(0, len(frames), 2):
        left, right = frames[i], frames[i+1]
        if left["canonical"] == right["canonical"]:
            raise ValueError(f"P1h pair {i // 2} is not balanced")
        candidate = left if left["canonical"] else right
        current = left if not left["canonical"] else right
        measures = (
            "complete_gi_gpu_us", "complete_renderer_gpu_us",
            "primary_visibility_gpu_us", "post_producer_gi_work_gpu_us",
        )
        differences = {
            measure: candidate[measure] - current[measure] for measure in measures
        }
        for stage in STAGES:
            differences[f"stage_{stage}"] = (
                candidate["gpu_us"][stage] - current["gpu_us"][stage])
        pairs.append({
            "pair": i // 2,
            "order": ["canonical" if f["canonical"] else "current"
                      for f in (left, right)],
            "current_frame": current["index"],
            "canonical_frame": candidate["index"],
            "deltas_candidate_minus_current_us": differences,
        })
    return {
        "frames": frames,
        "pairs": pairs,
        "pair_count": len(pairs),
        "median_complete_gi_delta_us": statistics.median(
            p["deltas_candidate_minus_current_us"]["complete_gi_gpu_us"]
            for p in pairs),
        "median_post_producer_delta_us": statistics.median(
            p["deltas_candidate_minus_current_us"]["post_producer_gi_work_gpu_us"]
            for p in pairs),
        "image_sha256": EXPECTED_IMAGE_SHA256,
    }


def summarize(processes: list[dict[str, Any]]) -> dict[str, Any]:
    if len(processes) != PROCESSES:
        raise ValueError("P1h requires all three frozen fresh-process runs")
    all_pairs = [pair for run in processes for pair in run["pairs"]]
    if len(all_pairs) != PROCESSES * 6:
        raise ValueError("P1h 18 matched comparisons incomplete")
    def describe(key: str) -> dict[str, float]:
        samples = [
            pair["deltas_candidate_minus_current_us"][key] for pair in all_pairs
        ]
        return {
            "count": len(samples),
            "median_us": statistics.median(samples),
            "min_us": min(samples),
            "max_us": max(samples),
            "negative_pairs": sum(x < 0 for x in samples),
            "positive_pairs": sum(x > 0 for x in samples),
        }
    return {
        "pair_count": len(all_pairs),
        "complete_gi": describe("complete_gi_gpu_us"),
        "complete_renderer": describe("complete_renderer_gpu_us"),
        "primary_visibility": describe("primary_visibility_gpu_us"),
        "post_producer_gi_work": describe("post_producer_gi_work_gpu_us"),
        "per_process_complete_gi_medians_us":
            [r["median_complete_gi_delta_us"] for r in processes],
        "per_process_post_producer_medians_us":
            [r["median_post_producer_delta_us"] for r in processes],
        "interpretation": (
            "Non-formal, fixed workload only. No selective exclusions, "
            "no declaration of speedup based solely on ray reduction."),
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run 'mise run build'")
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza asset absent or digest mismatch")
    gpu = cfg["target_gpu"]
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1h-matched-canonical"
            / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    dest.mkdir(parents=True, exist_ok=False)
    summary_file = dest / "n006-p1h-matched-canonical-summary.json"
    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL,
        "status": "in-progress",
        "formal": False,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "gpu": gpu,
        "scene_sha256": cfg["baseline"]["scene_sha256"],
        "source_warmups": SOURCE_WARMUPS,
        "target_state_warmups": TARGET_STATE_WARMUPS,
        "processes_requested": PROCESSES,
        "canonical_pattern": MASK,
        "reference_generated": False,
        "runs": [],
        "failures": [],
    }
    def checkpoint() -> None:
        summary_file.write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
    checkpoint()
    for run_index in range(PROCESSES):
        output = dest / f"process-{run_index}"
        output.mkdir(parents=True, exist_ok=False)
        command = [
            "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
            str(pilot.BINARY), "--scene", str(scene), "--artifact-dir", str(output),
            "--scenario", "deforming-control", "--mode", "current",
            "--source-warmup-frames", str(SOURCE_WARMUPS),
            "--target-state-warmup-frames", str(TARGET_STATE_WARMUPS),
            "--target-frames", "12", "--canonical-frame-pattern", MASK,
            "--skip-reference",
        ]
        try:
            proc = subprocess.run(
                command, cwd=pilot.ROOT, text=True, capture_output=True,
                check=False)
            (output / "stdout.log").write_text(proc.stdout, encoding="utf-8")
            (output / "stderr.log").write_text(proc.stderr, encoding="utf-8")
            if proc.returncode:
                raise RuntimeError(
                    f"P1h process {run_index} failed exit={proc.returncode}, "
                    f"see {output / 'stderr.log'}")
            data = json.loads(
                (output / pilot.EVIDENCE_NAME).read_text(encoding="utf-8"))
            run = audit_process(data, output, gpu)
            run["process_index"] = run_index
            run["source_evidence_sha256"] = hashlib.sha256(
                (output / pilot.EVIDENCE_NAME).read_bytes()).hexdigest()
            summary["runs"].append(run)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as err:
            summary["failures"].append({
                "process_index": run_index,
                "error": str(err),
                "stderr": str(output / "stderr.log"),
            })
            summary["status"] = "invalid-retained"
            checkpoint()
            raise
        checkpoint()
    summary["result"] = summarize(summary["runs"])
    summary["status"] = "complete"
    checkpoint()
    print(json.dumps({
        "status": "complete",
        "processes": len(summary["runs"]),
        "paired_comparisons": summary["result"]["pair_count"],
        "complete_gi_median_delta_us":
            summary["result"]["complete_gi"]["median_us"],
        "post_producer_median_delta_us":
            summary["result"]["post_producer_gi_work"]["median_us"],
        "summary": str(summary_file),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as err:
        print(f"N006 P1h matched canonical performance failed: {err}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""P1k frozen three-arm warm-state GPU timing: current vs copyback vs direct."""
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
from run_p1e_timing import STAGES

PROTOCOL = "n006-p1k-three-arm-timing-v1"
PATTERN = "012120201021102210"
BACKENDS = ("lane-e-final-hwrt", "lane-e-final-software")
REPEATS = 3
SOURCE_WARMUP = 32
TARGET_WARMUP = 8
EXPECTED_SHA = "79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861"
KEYS = [1853, 815, 284, 77]
OUTPUTS = 4172 * 4
RAYS = OUTPUTS * 8
CANONICAL_RAYS = sum(KEYS) * 8
SCRATCH = 4489304
GI_WORK_STAGES = (
    "ray_prepare_gpu", "traversal_gpu", "radiance_gpu",
    "merge_gpu", "storage_update_gpu", "invalidation_gpu", "resolve_gpu",
)
METRICS = ("complete_gi_gpu_us", "complete_renderer_gpu_us",
           "primary_visibility_gpu_us", "post_producer_gpu_us",
           "canonical_build_gpu_us")


def gpu(timing: dict[str, Any], name: str) -> float:
    x = timing.get(name)
    if (not isinstance(x, (int, float)) or isinstance(x, bool)
        or not math.isfinite(x) or x < 0):
        raise ValueError(f"P1k missing/invalid GPU timestamp: {name}")
    return float(x)


def audit_frame(frame: dict[str, Any], index: int, folder: Path) -> dict[str, Any]:
    arm = PATTERN[index]
    stats = frame.get("stats", {})
    extra = frame.get("extra", {})
    can = extra.get("canonical", {})
    canonical = arm != "0"
    if (
        frame.get("index") != index or
        frame.get("motion_fraction") != 1 or
        frame.get("owner_budget") != 0 or
        frame.get("internal_correctness") is not True or
        frame.get("hit_diagnostics", {}).get("substantive_mismatches") != 0 or
        stats.get("visible_owners") != 4172 or
        stats.get("work_items") != (CANONICAL_RAYS if canonical else RAYS) or
        stats.get("outputs") != (sum(KEYS) if canonical else OUTPUTS) or
        stats.get("storage_updates") != (sum(KEYS) if canonical else OUTPUTS) or
        stats.get("moved_primitives") != 796 or
        stats.get("topology_mutations") != 0 or
        stats.get("storage_failures") != 0 or
        stats.get("overflow") != 0 or
        extra.get("base_prefix_correct") is not True or
        extra.get("extra_work_correct") is not True or
        extra.get("extra_rays_traced") != 0 or
        extra.get("gpu_hash_probe", {}).get("executed") is not False or
        can.get("executed") is not canonical
    ):
        raise ValueError(f"P1k frame {index} failed shader/counter/traversal safety gate")
    if canonical and (
        can.get("copyback_executed") is not (arm == "1") or
        can.get("hash_slots") != 32768 or
        can.get("scratch_bytes") != SCRATCH or
        can.get("unique_by_cascade") != KEYS or
        can.get("canonical_outputs") != sum(KEYS) or
        can.get("canonical_work_items") != CANONICAL_RAYS or
        can.get("original_outputs") != OUTPUTS or
        can.get("original_work_items") != RAYS or
        can.get("duplicates") != OUTPUTS - sum(KEYS) or
        can.get("weighted_owner_total") != OUTPUTS or
        can.get("owner_weight_errors") != 0 or
        can.get("invalid_keys") != 0 or
        can.get("failed_inserts") != 0 or
        can.get("index_overflows") != 0
    ):
        raise ValueError(f"P1k frame {index} incorrect copyback / lean canonical ray evidence")

    rel = Path(frame.get("image", ""))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"P1k frame {index} invalid image path")
    file = folder / rel
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError(f"P1k frame {index} HDR PFM byte parity failed")
    times = frame.get("timing_us", {})
    disjoint = sum(gpu(times, key) for key in STAGES)
    complete = gpu(times, "complete_gi_gpu")
    renderer = gpu(times, "complete_renderer_gpu")
    composite = gpu(times, "composite_gpu")
    if gpu(times, "traversal_maintenance_gpu") != 0:
        raise ValueError(f"P1k frame {index} cold dynamic maintenance in measurement")
    build = gpu(can, "total_canonical_gpu_us") if canonical else 0.0
    weight = gpu(can, "owner_weight_storage_gpu_us") if canonical else 0.0
    if canonical and (build <= 0 or weight <= 0 or
                      weight > gpu(times, "storage_update_gpu") + 1e-6):
        raise ValueError(f"P1k frame {index} nested GPU timing invalid")
    if abs(disjoint + build - complete) > 1.0:
        raise ValueError(f"P1k frame {index} disjoint GPU stage closure failed")
    if abs(complete + composite - renderer) > 1.0:
        raise ValueError(f"P1k frame {index} composite GPU timestamp closure failed")
    return {
        "frame": index, "arm": arm, "image_sha256": EXPECTED_SHA,
        "actual_rays": stats["work_items"],
        "complete_gi_gpu_us": complete,
        "complete_renderer_gpu_us": renderer,
        "primary_visibility_gpu_us": gpu(times, "primary_visibility_gpu"),
        "post_producer_gpu_us": build +
            sum(gpu(times, key) for key in GI_WORK_STAGES),
        "canonical_build_gpu_us": build,
        "weight_gpu_us_nested": weight,
        "stage_closure_us": disjoint + build - complete,
        "raw_stages_gpu_us": {key: gpu(times, key) for key in STAGES},
    }


def audit_run(data: dict[str, Any], folder: Path, backend: str) -> dict[str, Any]:
    if (
        data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("variant") != backend or
        data.get("scenario") != "deforming-control" or
        data.get("mode") != "current" or
        data.get("three_arm_pattern") != PATTERN or
        data.get("reference_generation") != "skipped" or
        data.get("source_warmup_frames") != SOURCE_WARMUP or
        data.get("source", {}).get("internal_correctness") is not True
    ):
        raise ValueError("P1k source/backend/pattern contract failed")
    warmup = data.get("target_state_warmup", {})
    if (
        warmup.get("frames") != TARGET_WARMUP or
        warmup.get("correct") is not True or
        warmup.get("last_traversal_maintenance_gpu") != 0 or
        warmup.get("last_visible_owners") != 4172 or
        warmup.get("last_work_items") != RAYS
    ):
        raise ValueError("P1k target warmup was not stable")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != len(PATTERN):
        raise ValueError("P1k missing measured three-arm frames")
    observed = [audit_frame(frame, i, folder) for i, frame in enumerate(frames)]
    triplets: list[dict[str, Any]] = []
    for start in range(0, len(observed), 3):
        group = observed[start:start + 3]
        if set(x["arm"] for x in group) != {"0", "1", "2"}:
            raise ValueError("P1k triplet must contain all three arms")
        lookup = {f["arm"]: f for f in group}
        deltas = {}
        for name, left, right in (
            ("copyback_minus_current", "1", "0"),
            ("direct_minus_current", "2", "0"),
            ("direct_minus_copyback", "2", "1"),
        ):
            deltas[name] = {
                key: lookup[left][key] - lookup[right][key] for key in METRICS
            }
        triplets.append({
            "triplet": start // 3, "order": "".join(x["arm"] for x in group),
            "deltas_us": deltas,
        })
    if len(triplets) != 6:
        raise ValueError("P1k expected six complete balanced triplets")
    return {"backend": backend, "frames": observed, "triplets": triplets}


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) != len(BACKENDS)*REPEATS or (
        any(sum(x["backend"] == name for x in runs) != REPEATS
            for name in BACKENDS)
    ):
        raise ValueError("P1k requires exactly three completed fresh runs per backend")
    report: dict[str, Any] = {}
    for backend in BACKENDS:
        selected = [r for r in runs if r["backend"] == backend]
        pairs = [p for run in selected for p in run["triplets"]]
        measurements = {}
        for contrast in ("copyback_minus_current", "direct_minus_current",
                         "direct_minus_copyback"):
            measurements[contrast] = {}
            for key in METRICS:
                values = [p["deltas_us"][contrast][key] for p in pairs]
                measurements[contrast][key] = {
                    "n": len(values),
                    "median_us": statistics.median(values),
                    "minimum_us": min(values),
                    "maximum_us": max(values),
                    "faster_triplets": sum(x < 0 for x in values),
                    "slower_triplets": sum(x > 0 for x in values),
                    "per_process_median_us": [
                        statistics.median([
                            p["deltas_us"][contrast][key] for p in run["triplets"]
                        ]) for run in selected
                    ],
                }
        report[backend] = {"triplets": len(pairs), "contrasts": measurements}
    return {
        "measured_frames": len(runs)*len(PATTERN),
        "triplets": sum(len(r["triplets"]) for r in runs),
        "by_backend": report,
        "claim_scope": "Nonformal AMD GPU fixed deforming workload: 3-arm same-state triplets only.",
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("N006 binary missing; run mise run build")
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise RuntimeError("P1k accepted scene hash mismatch or missing")
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1k-three-arm" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    dest.mkdir(parents=True, exist_ok=False)
    output_summary = dest / "n006-p1k-three-arm-summary.json"
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "reference_generated": False,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "gpu": cfg["target_gpu"], "scene_sha256": cfg["baseline"]["scene_sha256"],
        "pattern": PATTERN, "backends": list(BACKENDS), "processes_per_backend": REPEATS,
        "runs": [], "failures": [],
    }

    def save() -> None:
        output_summary.write_text(json.dumps(result, indent=2, sort_keys=True)
                                  + "\n", encoding="utf-8")
    save()
    for backend in BACKENDS:
        for attempt in range(REPEATS):
            folder = dest / f"{backend}-{attempt}"
            folder.mkdir(parents=True, exist_ok=False)
            command = [
                "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
                str(pilot.BINARY), "--scene", str(scene),
                "--artifact-dir", str(folder),
                "--scenario", "deforming-control", "--variant", backend,
                "--mode", "current", "--source-warmup-frames", "32",
                "--target-state-warmup-frames", "8",
                "--target-frames", "18", "--three-arm-pattern", PATTERN,
                "--skip-reference", "--canonical-lean-hash", "--canonical-zero-copy",
            ]
            try:
                proc = subprocess.run(command, cwd=pilot.ROOT, text=True,
                                      capture_output=True, check=False)
                (folder / "stdout.log").write_text(proc.stdout, encoding="utf-8")
                (folder / "stderr.log").write_text(proc.stderr, encoding="utf-8")
                if proc.returncode:
                    raise RuntimeError(f"P1k {backend} run {attempt} exited {proc.returncode}")
                raw_file = folder / pilot.EVIDENCE_NAME
                raw = json.loads(raw_file.read_text(encoding="utf-8"))
                if raw.get("device", {}).get("name") != cfg["target_gpu"]:
                    raise ValueError("P1k target GPU changed")
                audited = audit_run(raw, folder, backend)
                audited["attempt"] = attempt
                audited["source_evidence_sha256"] = hashlib.sha256(
                    raw_file.read_bytes()).hexdigest()
                result["runs"].append(audited)
            except (RuntimeError, ValueError, OSError, TypeError, KeyError) as err:
                result["failures"].append({
                    "backend": backend, "attempt": attempt,
                    "error": str(err), "stderr_path": str(folder / "stderr.log"),
                })
                result["status"] = "invalid-retained"
                save()
                raise
            save()
    result["results"] = summarize(result["runs"])
    result["status"] = "complete"
    save()
    print(json.dumps({
        "status": result["status"], "frames": result["results"]["measured_frames"],
        "triplets": result["results"]["triplets"],
        "summary": str(output_summary),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"N006 P1k matched three-arm diagnostic failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

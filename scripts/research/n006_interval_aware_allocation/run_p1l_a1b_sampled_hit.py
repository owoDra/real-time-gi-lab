#!/usr/bin/env python3
"""N006 P1l-A1b: sampled N004 CPU reference, full-frame GPU/HDR stage profiling."""
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
from run_p1i_cross_backend import MATRIX

PROTOCOL = "n006-p1l-a1b-sampled-hit-stage-isolation-v1"
PROCESS_TIMEOUT_SECONDS = 600
PROCESSES_PER_CASE = 3
MEASURED_FRAMES = 12
SOURCE_WARMUPS = 32
TARGET_WARMUPS = 8
LEAN_SCRATCH = 4489304
HASH_SLOTS = 32768
# Frozen from P1j-B's 10 accepted bit-exact current/canonical PFM cases.
# Do not silently force hardware/software moving-rigid images to match:
# those two accepted HDR images have different bytes.
SCENE_EXPECTATIONS = {
    "static": (4167, (1842, 807, 282, 77)),
    "camera-motion": (4231, (1973, 869, 300, 78)),
    "light-motion": (4167, (1842, 807, 282, 77)),
    "moving-rigid": (4213, (1890, 836, 299, 79)),
    "deforming-control": (4172, (1853, 815, 284, 77)),
}
SCENE_IMAGE_SHA = {
    "static": "2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e",
    "camera-motion": "eb889a8796ebae5cfb23ff820c01fcf5e2fd2d21376dc06b8c4a447512362bcd",
    "light-motion": "7b48345b67311652fcba9f7083a21fa07eb316d6ded75a1807f75070516333ec",
    "deforming-control": "79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861",
}
RIGID_IMAGE_SHA = {
    "lane-e-final-hwrt": "b0829e21214de633f80c935ddcfa5ca63204c2c1e353ff5ea1f9fd9b7eb1fe17",
    "lane-e-final-software": "d1e43a880cd7a4276b62127b6ae64cf4d1b50ca7922c81589095783fe055a0dd",
}
CORE_STAGES = tuple(STAGES)
STAGE_FIELDS = (*CORE_STAGES, "composite_gpu", "complete_gi_gpu",
                "complete_renderer_gpu")
REPORT_FIELDS = (*STAGE_FIELDS, "canonical_build_gpu", "owner_weight_gpu_nested",
                 "post_producer_gpu")
AFTER_PRODUCER_STAGES = (
    "ray_prepare_gpu", "traversal_gpu", "radiance_gpu", "merge_gpu",
    "storage_update_gpu", "invalidation_gpu", "resolve_gpu",
)


def finite_gpu(obj: dict[str, Any], key: str) -> float:
    x = obj.get(key)
    if (not isinstance(x, (int, float)) or isinstance(x, bool)
        or not math.isfinite(x) or x < 0):
        raise ValueError(f"P1l missing/bad GPU value: {key}")
    return float(x)


def expected_sha(variant: str, scenario: str) -> str:
    if (variant, scenario) not in MATRIX:
        raise ValueError("P1l unexpected scenario/backend combination")
    return RIGID_IMAGE_SHA[variant] if scenario == "moving-rigid" else SCENE_IMAGE_SHA[scenario]


def validate_frame(
    frame: dict[str, Any], index: int, folder: Path, variant: str,
    scenario: str, sampled_hit_index: int = 0,
) -> dict[str, Any]:
    owners, cascades = SCENE_EXPECTATIONS[scenario]
    outputs = sum(cascades)
    original_outputs = owners * 4
    canonical_rays = outputs * 8
    diagnostics = frame.get("hit_diagnostics")
    if index == sampled_hit_index:
        if (not isinstance(diagnostics, dict) or
            diagnostics.get("substantive_mismatches") != 0):
            raise ValueError("P1l-A1b sampled first canonical N004 hit diagnostic failed")
    elif diagnostics is not None:
        raise ValueError("P1l-A1b unsampled frame falsely reported CPU hit diagnostics")
    stats = frame.get("stats", {})
    extra = frame.get("extra", {})
    can = extra.get("canonical", {})
    if (
        frame.get("index") != index or
        frame.get("motion_fraction") != 1.0 or
        frame.get("owner_budget") != 0 or
        frame.get("internal_correctness") is not True or
        stats.get("visible_owners") != owners or
        stats.get("work_items") != canonical_rays or
        stats.get("outputs") != outputs or
        stats.get("storage_updates") != outputs or
        stats.get("overflow") != 0 or
        stats.get("storage_failures") != 0 or
        stats.get("topology_mutations") != 0 or
        extra.get("base_prefix_correct") is not True or
        extra.get("extra_work_correct") is not True or
        extra.get("extra_rays_traced") != 0 or
        extra.get("gpu_hash_probe", {}).get("executed") is not False or
        can.get("executed") is not True or
        can.get("copyback_executed") is not True or
        can.get("hash_slots") != HASH_SLOTS or
        can.get("scratch_bytes") != LEAN_SCRATCH or
        can.get("original_work_items") != original_outputs * 8 or
        can.get("original_outputs") != original_outputs or
        can.get("canonical_work_items") != canonical_rays or
        can.get("canonical_outputs") != outputs or
        can.get("unique_by_cascade") != list(cascades) or
        can.get("duplicates") != original_outputs - outputs or
        can.get("weighted_owner_total") != original_outputs or
        can.get("owner_weight_errors") != 0 or
        can.get("invalid_keys") != 0 or
        can.get("failed_inserts") != 0 or
        can.get("index_overflows") != 0 or
        not isinstance(can.get("collision_steps"), int) or
        isinstance(can.get("collision_steps"), bool) or
        can["collision_steps"] < 0
    ):
        raise ValueError(f"P1l frame {index} failed owner/hash/storage/coverage contract")
    rel = Path(frame.get("image", ""))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"P1l frame {index} unsafe HDR path")
    image = folder / rel
    digest = expected_sha(variant, scenario)
    if not image.is_file() or hashlib.sha256(image.read_bytes()).hexdigest() != digest:
        raise ValueError(f"P1l frame {index} not bit-identical to accepted {variant}/{scenario} HDR")
    times = frame.get("timing_us", {})
    values = {name: finite_gpu(times, name) for name in STAGE_FIELDS}
    build = finite_gpu(can, "total_canonical_gpu_us")
    weight = finite_gpu(can, "owner_weight_storage_gpu_us")
    if (build <= 0 or weight <= 0 or
        weight > values["storage_update_gpu"] + 1e-6 or
        values["traversal_maintenance_gpu"] != 0):
        raise ValueError(f"P1l frame {index} invalid build/owner-weight/cold maintenance")
    closure = sum(values[name] for name in CORE_STAGES) + build - values["complete_gi_gpu"]
    composite_closure = (
        values["complete_gi_gpu"] + values["composite_gpu"]
        - values["complete_renderer_gpu"]
    )
    if abs(closure) > 1.0 or abs(composite_closure) > 1.0:
        raise ValueError(f"P1l frame {index} overlapping or missing GPU stage timestamps")
    return {
        "frame_index": index, "image_sha256": digest,
        "canonical_ray_work_items": canonical_rays,
        "original_ray_work_items": original_outputs * 8,
        "canonical_outputs": outputs, "owner_count": owners,
        "hash_collision_steps": can["collision_steps"],
        **values,
        "canonical_build_gpu": build,
        "owner_weight_gpu_nested": weight,
        "post_producer_gpu": build +
            sum(values[s] for s in AFTER_PRODUCER_STAGES),
        "stage_closure_us": closure,
        "composite_closure_us": composite_closure,
    }


def validate_run(data: dict[str, Any], folder: Path, gpu: str,
                 variant: str, scenario: str) -> dict[str, Any]:
    if (
        (variant, scenario) not in MATRIX or
        data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("variant") != variant or
        data.get("scenario") != scenario or
        data.get("mode") != "current" or
        data.get("p1l_stage_fast") is not True or
        data.get("p1l_stage_probe") is not False or
        data.get("p1l_hit_diagnostic_frame") != 0 or
        data.get("source", {}).get("hit_diagnostics") is not None or
        data.get("reference_generation") != "skipped" or
        data.get("source_warmup_frames") != SOURCE_WARMUPS or
        data.get("source_warmups_correct") is not True or
        data.get("device", {}).get("name") != gpu or
        data.get("source", {}).get("internal_correctness") is not True or
        data.get("three_arm_pattern") != ""
    ):
        raise ValueError("P1l process source/backend/protocol drift")
    warm = data.get("target_state_warmup", {})
    owners, _ = SCENE_EXPECTATIONS[scenario]
    history = warm.get("maintenance_gpu_us")
    if (
        warm.get("frames") != TARGET_WARMUPS or
        warm.get("correct") is not True or
        warm.get("last_traversal_maintenance_gpu") != 0 or
        warm.get("last_visible_owners") != owners or
        warm.get("last_work_items") != owners * 32 or
        not isinstance(history, list) or len(history) != TARGET_WARMUPS
    ):
        raise ValueError("P1l source/target warmup did not stabilize")
    maintenance_samples = [finite_gpu({"t": value}, "t") for value in history]
    if any(value != 0.0 for value in maintenance_samples[1:]):
        raise ValueError("P1l target warmup repeated geometry maintenance")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != MEASURED_FRAMES:
        raise ValueError("P1l expected exactly 12 canonical measured frames")
    observed = [validate_frame(f, i, folder, variant, scenario)
                for i, f in enumerate(frames)]
    return {
        "variant": variant, "scenario": scenario,
        "expected_image_sha256": expected_sha(variant, scenario),
        "source_warmups": SOURCE_WARMUPS,
        "target_warmup_maintenance_gpu_us": maintenance_samples,
        "target_first_maintenance_gpu_us": maintenance_samples[0],
        "measured_frame_count": len(observed),
        "frames": observed,
        "per_process_medians_gpu_us": {
            name: statistics.median(frame[name] for frame in observed)
            for name in REPORT_FIELDS
        },
    }


def percentile(values: list[float], fraction: float) -> float:
    """Sorted linear interpolation at percentile position p*(n-1)."""
    if not values or not 0 <= fraction <= 1:
        raise ValueError("P1l invalid percentile request")
    sorted_values = sorted(values)
    pos = fraction * (len(values) - 1)
    i = math.floor(pos)
    return sorted_values[i] if i + 1 == len(values) else (
        sorted_values[i] * (1 - pos + i) +
        sorted_values[i + 1] * (pos - i)
    )


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    expected_runs = len(MATRIX) * PROCESSES_PER_CASE
    if len(runs) != expected_runs:
        raise ValueError("P1l requires complete frozen 30-process matrix")
    aggregate: dict[str, Any] = {}
    for variant, scenario in MATRIX:
        selected = [r for r in runs if (
            r["variant"] == variant and r["scenario"] == scenario
        )]
        if len(selected) != PROCESSES_PER_CASE or (
            sorted(r.get("attempt") for r in selected) != list(range(PROCESSES_PER_CASE))
        ):
            raise ValueError(f"P1l missing/duplicated process {variant}/{scenario}")
        samples = [frame for run in selected for frame in run["frames"]]
        if len(samples) != PROCESSES_PER_CASE * MEASURED_FRAMES:
            raise ValueError("P1l missing measured frames")
        summary = {}
        for name in REPORT_FIELDS:
            values = [finite_gpu(frame, name) for frame in samples]
            summary[name] = {
                "count": len(values), "median_us": statistics.median(values),
                "p10_us": percentile(values, 0.1),
                "p90_us": percentile(values, 0.9),
                "minimum_us": min(values), "maximum_us": max(values),
                "per_process_medians_us": [
                    finite_gpu(r["per_process_medians_gpu_us"], name)
                    for r in sorted(selected, key=lambda x: x["attempt"])
                ],
            }
        aggregate[f"{variant}/{scenario}"] = summary
    # These ratios compare DIFFERENT fresh processes. They are descriptive,
    # not a paired treatment effect or a guarantee of HWRT-free portability.
    ratios: dict[str, Any] = {}
    for scenario in SCENE_EXPECTATIONS:
        h = aggregate[f"lane-e-final-hwrt/{scenario}"]
        s = aggregate[f"lane-e-final-software/{scenario}"]
        ratios[scenario] = {}
        for stage in ("primary_visibility_gpu", "traversal_gpu",
                      "composite_gpu", "post_producer_gpu",
                      "complete_gi_gpu", "complete_renderer_gpu"):
            lhs = h[stage]["median_us"]
            rhs = s[stage]["median_us"]
            ratios[scenario][stage] = rhs / lhs if lhs > 0 else None
    return {
        "cases": len(MATRIX), "fresh_processes": len(runs),
        "measured_frames": expected_runs * MEASURED_FRAMES,
        "per_case_gpu_stage_summary": aggregate,
        "software_over_hwrt_median_ratios_unpaired": ratios,
        "interpretation": (
            "A1b: only canonical frame 0 has CPU N004 hit oracle; all measured "
            "frames have accepted PFM SHA and GPU safety gates. "
            "Stage-level diagnosis only. HWRT and Software run in separate processes; "
            "ratios are not causal, and a stage timestamp is not a BVH visit counter."),
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("N006 renderer binary missing; run mise run build")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("P1l accepted scene absent or changed")
    target_gpu = config["target_gpu"]
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1l-a1b-sampled-hit-stage"
            / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    dest.mkdir(parents=True, exist_ok=False)
    summary_file = dest / "n006-p1l-a1b-sampled-hit-summary.json"
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "reference_generated": False,
        "git": {"branch": pilot.EXPECTED_BRANCH, "head": head, "dirty": False},
        "gpu": target_gpu, "scene_sha256": config["baseline"]["scene_sha256"],
        "source_warmups": SOURCE_WARMUPS,
        "target_state_warmups": TARGET_WARMUPS,
        "measured_frames_per_process": MEASURED_FRAMES,
        "processes_per_case": PROCESSES_PER_CASE,
        "cpu_hit_diagnostic_sampled_frame": 0,
        "cpu_hit_diagnostic_per_process": 1,
        "subprocess_timeout_seconds": PROCESS_TIMEOUT_SECONDS,
        "matrix": [{"variant": variant, "scenario": scenario}
                   for variant, scenario in MATRIX],
        "runs": [], "failures": [],
    }

    def checkpoint() -> None:
        summary_file.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    checkpoint()
    for variant, scenario in MATRIX:
        for attempt in range(PROCESSES_PER_CASE):
            folder = dest / f"{variant}-{scenario}-run-{attempt}"
            folder.mkdir(parents=True, exist_ok=False)
            command = [
                "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
                str(pilot.BINARY),
                "--scene", str(scene), "--artifact-dir", str(folder),
                "--scenario", scenario, "--variant", variant,
                "--mode", "current", "--source-warmup-frames", "32",
                "--target-state-warmup-frames", "8", "--target-frames", "12",
                "--skip-reference", "--canonical-lean-hash",
                "--p1l-stage-fast",
            ]
            print(f"[P1l-A1b] start {variant}/{scenario} run={attempt} "
                  f"({len(result['runs']) + 1}/30) "
                  f"wall-time cap={PROCESS_TIMEOUT_SECONDS}s", flush=True)
            try:
                try:
                    process = subprocess.run(
                        command, cwd=pilot.ROOT, timeout=PROCESS_TIMEOUT_SECONDS,
                        text=True, capture_output=True, check=False)
                except subprocess.TimeoutExpired as timeout:
                    def decoded(value: bytes | str | None) -> str:
                        if isinstance(value, bytes):
                            return value.decode("utf-8", errors="replace")
                        return value or ""
                    (folder / "stdout.log").write_text(
                        decoded(timeout.stdout), encoding="utf-8")
                    (folder / "stderr.log").write_text(
                        decoded(timeout.stderr), encoding="utf-8")
                    raise RuntimeError(
                        f"P1l-A1b process exceeded {PROCESS_TIMEOUT_SECONDS}s "
                        "wall timeout; killed renderer process; inspect logs") from timeout
                (folder / "stdout.log").write_text(process.stdout, encoding="utf-8")
                (folder / "stderr.log").write_text(process.stderr, encoding="utf-8")
                if process.returncode:
                    raise RuntimeError(
                        f"P1l-A1b {variant}/{scenario} run={attempt} exited "
                        f"{process.returncode}; see {folder / 'stderr.log'}")
                source_file = folder / pilot.EVIDENCE_NAME
                data = json.loads(source_file.read_text(encoding="utf-8"))
                audited = validate_run(data, folder, target_gpu, variant, scenario)
                audited["attempt"] = attempt
                audited["raw_evidence_sha256"] = hashlib.sha256(
                    source_file.read_bytes()).hexdigest()
                result["runs"].append(audited)
                print(f"[P1l-A1b] accepted {len(result['runs'])}/30 "
                      f"{variant}/{scenario} run={attempt}", flush=True)
            except (RuntimeError, ValueError, OSError, KeyError, TypeError) as error:
                result["status"] = "invalid-retained"
                result["failures"].append({
                    "variant": variant, "scenario": scenario,
                    "attempt": attempt, "error": str(error),
                    "stderr": str(folder / "stderr.log"),
                })
                checkpoint()
                raise
            checkpoint()
    result["results"] = summarize(result["runs"])
    result["status"] = "complete"
    checkpoint()
    print(json.dumps({
        "status": result["status"],
        "fresh_processes": result["results"]["fresh_processes"],
        "measured_frames": result["results"]["measured_frames"],
        "summary": str(summary_file),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, KeyError, TypeError) as error:
        print(f"N006 P1l-A1b sampled-hit isolation failed: {error}", file=sys.stderr)
        raise SystemExit(1)

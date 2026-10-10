#!/usr/bin/env python3
"""P1l-B0: standalone software primary/shadow and E003 GPU work-count triage.

Instrumented shaders run *after* accepted uninstrumented GPU timestamps.
They write separate outputs, compared byte-for-byte against accepted output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from run_p1l_a1b_sampled_hit import (
    SCENE_EXPECTATIONS, SOURCE_WARMUPS, TARGET_WARMUPS,
    validate_frame, finite_gpu, LEAN_SCRATCH, HASH_SLOTS,
)

PROTOCOL = "n006-p1l-b0-work-counts-v1"
TIMEOUT_SECONDS = 600
VARIANT = "lane-e-final-software"
SCENARIOS = ("light-motion", "camera-motion", "static",
             "moving-rigid", "deforming-control")
SMOKE = SCENARIOS[:2]
LABELS = {
    "primary": ("node_pops", "triangle_tests", "hit", "stack_overflow"),
    "shadow": ("shadow_queries", "node_pops", "triangle_tests",
               "blockers", "valid_pixels", "positive_cosine",
               "stack_overflow", "storage_lookups"),
    "secondary": ("instance_tests", "dda_cells", "hash_probes",
                  "quant_node_pops", "child_aabb_tests",
                  "triangle_tests", "leaf_visits", "overflow"),
}


def audit_profile(profile: dict[str, Any], actual_rays: int) -> dict[str, Any]:
    if (profile.get("diagnostic_only") is not True or
        profile.get("uninstrumented_gpu_timing") is not True or
        profile.get("output_byte_identical") is not True or
        profile.get("pixels") != 320 * 180 or
        profile.get("secondary_rays") != actual_rays):
        raise ValueError("B0 incorrect diagnostic capture scope or byte parity")
    for group, labels in LABELS.items():
        metrics = profile.get(group)
        if not isinstance(metrics, dict) or set(metrics) != set(labels):
            raise ValueError(f"B0 missing/extra {group} metrics")
        capacity = actual_rays if group == "secondary" else 320 * 180
        for name in labels:
            v = metrics[name]
            if not isinstance(v, dict) or set(v) != {
                "sum", "mean", "p50", "p90", "p99", "max", "nonzero"
            }:
                raise ValueError(f"B0 missing distribution: {group}.{name}")
            total, maximum, nonzero = v["sum"], v["max"], v["nonzero"]
            values = [v[key] for key in ("mean", "p50", "p90", "p99")]
            if (any(not isinstance(x, int) or isinstance(x, bool) or x < 0
                    for x in (total, maximum, nonzero)) or
                nonzero > capacity or nonzero > total or
                any(not isinstance(x, (int, float)) or
                    isinstance(x, bool) or not math.isfinite(x) or x < 0
                    for x in values) or
                values[1] > values[2] + 1e-6 or
                values[2] > values[3] + 1e-6 or
                values[3] > maximum + 1e-6 or
                abs(values[0] - total / capacity) > 1e-4):
                raise ValueError(f"B0 invalid bounded distribution: {group}.{name}")
    if (profile["primary"]["stack_overflow"]["sum"] or
        profile["shadow"]["stack_overflow"]["sum"] or
        profile["secondary"]["overflow"]["sum"]):
        raise ValueError("B0 instrumented shader overflow detected")
    if profile["shadow"]["shadow_queries"]["sum"] > (
        profile["shadow"]["positive_cosine"]["sum"]
    ):
        raise ValueError("B0 more shadow rays than positive-hemisphere pixels")
    if profile["shadow"]["blockers"]["sum"] > (
        profile["shadow"]["shadow_queries"]["sum"]
    ):
        raise ValueError("B0 more shadow blockers than launched rays")
    return profile


def audit_case(data: dict[str, Any], folder: Path, gpu: str,
               scenario: str) -> dict[str, Any]:
    owners, _ = SCENE_EXPECTATIONS[scenario]
    if (data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("variant") != VARIANT or data.get("scenario") != scenario or
        data.get("p1l_b0_counts") is not True or
        data.get("p1l_stage_fast") is not False or
        data.get("p1l_stage_probe") is not False or
        data.get("p1l_hit_diagnostic_frame") != 0 or
        data.get("source_warmup_frames") != SOURCE_WARMUPS or
        data.get("source_warmups_correct") is not True or
        data.get("device", {}).get("name") != gpu or
        data.get("mode") != "current" or
        data.get("reference_generation") != "skipped" or
        data.get("source", {}).get("hit_diagnostics") is not None or
        data.get("source", {}).get("internal_correctness") is not True):
        raise ValueError("B0 process/backend/source contract drift")
    warm = data.get("target_state_warmup", {})
    if (warm.get("frames") != TARGET_WARMUPS or
        warm.get("correct") is not True or
        warm.get("last_visible_owners") != owners or
        warm.get("last_work_items") != owners * 32 or
        warm.get("last_traversal_maintenance_gpu") != 0 or
        not isinstance(warm.get("maintenance_gpu_us"), list) or
        len(warm["maintenance_gpu_us"]) != TARGET_WARMUPS or
        any(finite_gpu({"maintenance": x}, "maintenance") != 0
            for x in warm["maintenance_gpu_us"][1:])):
        raise ValueError("B0 target-state warmup contract drift")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != 1:
        raise ValueError("B0 requires exactly one uninstrumented measured image")
    measured = validate_frame(frames[0], 0, folder, VARIANT, scenario)
    counted = audit_profile(frames[0].get("p1l_b0_counts"),
                            measured["canonical_ray_work_items"])
    return {
        "scenario": scenario, "variant": VARIANT,
        "source_warmup_maintenance_gpu_us": warm["maintenance_gpu_us"],
        "original_uninstrumented_gpu_stage_us": {
            key: value for key, value in measured.items()
            if key.endswith("_gpu") or key in (
                "canonical_build_gpu", "post_producer_gpu",
            )
        },
        "accepted_image_sha256": measured["image_sha256"],
        "actual_secondary_rays": measured["canonical_ray_work_items"],
        "diagnostic_counts": counted,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true",
                        help="run only light-motion and camera-motion before all scenes")
    args = parser.parse_args()
    cases = SMOKE if args.smoke else SCENARIOS
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run mise run build")
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise RuntimeError("accepted Sponza scene missing/modified")
    path = pilot.ROOT / "out/research/n006-interval-aware-allocation" / (
        "p1l-b0-smoke" if args.smoke else "p1l-b0-five-scenes"
    ) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path.mkdir(parents=True, exist_ok=False)
    summary_path = path / "n006-p1l-b0-work-counts-summary.json"
    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "mode": "smoke" if args.smoke else "five-scenes",
        "reference_generated": False, "instrumented_timing_valid": False,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "gpu": cfg["target_gpu"], "scene_sha256": cfg["baseline"]["scene_sha256"],
        "case_matrix": list(cases), "results": [], "failures": [],
        "timeout_seconds_per_process": TIMEOUT_SECONDS,
    }

    def save() -> None:
        summary_path.write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
    save()
    for scenario in cases:
        folder = path / scenario
        folder.mkdir(parents=True, exist_ok=False)
        cmd = [
            "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
            str(pilot.BINARY), "--scene", str(scene),
            "--artifact-dir", str(folder),
            "--scenario", scenario, "--variant", VARIANT,
            "--mode", "current", "--source-warmup-frames", "32",
            "--target-state-warmup-frames", "8", "--target-frames", "1",
            "--skip-reference", "--canonical-lean-hash", "--p1l-b0-counts",
        ]
        print(f"[B0] starting {scenario} "
              f"({len(summary['results'])+1}/{len(cases)})", flush=True)
        try:
            try:
                proc = subprocess.run(cmd, cwd=pilot.ROOT,
                    capture_output=True, text=True, check=False,
                    timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as e:
                for log, value in (("stdout.log", e.stdout), ("stderr.log", e.stderr)):
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="replace")
                    (folder / log).write_text(value or "", encoding="utf-8")
                raise RuntimeError(f"B0 {scenario} exceeded 600s wall timeout") from e
            (folder / "stdout.log").write_text(proc.stdout, encoding="utf-8")
            (folder / "stderr.log").write_text(proc.stderr, encoding="utf-8")
            if proc.returncode:
                raise RuntimeError(f"B0 {scenario} exit {proc.returncode}: "
                                   f"inspect {folder / 'stderr.log'}")
            evidence_path = folder / pilot.EVIDENCE_NAME
            data = json.loads(evidence_path.read_text(encoding="utf-8"))
            result = audit_case(data, folder, cfg["target_gpu"], scenario)
            result["raw_evidence_sha256"] = hashlib.sha256(
                evidence_path.read_bytes()).hexdigest()
            summary["results"].append(result)
            print(f"[B0] accepted {len(summary['results'])}/{len(cases)} "
                  f"{scenario}", flush=True)
        except (RuntimeError, ValueError, OSError, KeyError, TypeError) as e:
            summary["status"] = "invalid-retained"
            summary["failures"].append({
                "scenario": scenario, "error": str(e),
                "stderr": str(folder / "stderr.log")})
            save()
            raise
        save()
    summary["status"] = "complete"
    save()
    print(json.dumps({"status": summary["status"],
        "accepted_cases": len(summary["results"]),
        "summary": str(summary_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, KeyError, TypeError) as e:
        print(f"P1l-B0 work-count diagnostic failed: {e}", file=sys.stderr)
        raise SystemExit(1)

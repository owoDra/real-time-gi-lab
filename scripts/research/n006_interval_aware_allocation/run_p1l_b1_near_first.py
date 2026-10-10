#!/usr/bin/env python3
"""P1l-B1a frozen near-first primary: five-scene correctness, then matched GPU A/B.

One CPU hit oracle per process at measured candidate frame index 1.
The Python runner never modifies the accepted N003 shader or relaxes PFM SHA.
"""
from __future__ import annotations

import argparse
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
from run_p1l_a1b_sampled_hit import (
    SCENE_EXPECTATIONS, SOURCE_WARMUPS, TARGET_WARMUPS,
    expected_sha, finite_gpu, validate_frame,
)

PROTOCOL = "n006-p1l-b1a-primary-near-first-v1"
B1C_PROTOCOL = "n006-p1l-b1c-packed-axis-v1"
VARIANT = "lane-e-final-software"
SCENARIOS = ("static", "camera-motion", "light-motion",
             "moving-rigid", "deforming-control")
PREFLIGHT = "01"
BALANCED = "011001100110011001100110"  # six ABBA blocks, 12 matched pairs/run
PROCESSES = 3
TIMEOUT_SECONDS = 600
STAGES = (
    "primary_visibility_gpu", "complete_gi_gpu", "complete_renderer_gpu",
    "producer_gpu", "traversal_gpu", "composite_gpu",
)


def audit_run(data: dict[str, Any], folder: Path, gpu: str, scene: str,
              pattern: str, axis_proxy: bool = False) -> dict[str, Any]:
    if (scene not in SCENARIOS or pattern not in (PREFLIGHT, BALANCED) or
        data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("variant") != VARIANT or data.get("scenario") != scene or
        data.get("mode") != "current" or
        data.get("p1l_b1_pattern") != pattern or
        data.get("p1l_b1c_axis_proxy", False) is not axis_proxy or
        data.get("p1l_stage_fast") is not False or
        data.get("p1l_stage_probe") is not False or
        data.get("p1l_b0_counts") is not False or
        data.get("p1l_hit_diagnostic_frame") != 1 or
        data.get("three_arm_pattern") != "" or
        data.get("source_warmup_frames") != SOURCE_WARMUPS or
        data.get("source_warmups_correct") is not True or
        data.get("reference_generation") != "skipped" or
        data.get("device", {}).get("name") != gpu or
        data.get("source", {}).get("internal_correctness") is not True or
        data.get("source", {}).get("hit_diagnostics") is not None):
        raise ValueError("P1l-B1 source/backend/frozen schedule drift")
    warm = data.get("target_state_warmup", {})
    owners, _ = SCENE_EXPECTATIONS[scene]
    history = warm.get("maintenance_gpu_us")
    if (warm.get("frames") != TARGET_WARMUPS or
        warm.get("correct") is not True or
        warm.get("last_traversal_maintenance_gpu") != 0 or
        warm.get("last_visible_owners") != owners or
        warm.get("last_work_items") != owners * 32 or
        not isinstance(history, list) or len(history) != TARGET_WARMUPS or
        any(finite_gpu({"t": t}, "t") != 0 for t in history[1:])):
        raise ValueError("P1l-B1 target warmup/cold maintenance invalid")
    pack_cpu = data.get("p1l_b1c_axis_pack_cpu_us")
    packed_nodes = data.get("p1l_b1c_axis_packed_nodes")
    if axis_proxy and (not isinstance(pack_cpu, (int, float)) or
                       not math.isfinite(pack_cpu) or pack_cpu < 0 or
                       not isinstance(packed_nodes, int) or packed_nodes <= 0):
        raise ValueError("P1l-B1c missing CPU packing accounting")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != len(pattern):
        raise ValueError("P1l-B1 wrong number of measured frames")
    result_frames = []
    for idx, (frame, arm) in enumerate(zip(frames, pattern)):
        if (frame.get("p1l_b1_arm") != int(arm) or
            frame.get("p1l_b1_primary_exact") is not True or
            frame.get("p1l_b0_counts") is not None):
            raise ValueError(f"P1l-B1 frame {idx} wrong primary arm/byte parity")
        audited = validate_frame(frame, idx, folder, VARIANT, scene,
                                 sampled_hit_index=1)
        result_frames.append({
            "index": idx, "arm": int(arm),
            "image_sha256": audited["image_sha256"],
            "primary_hits_byte_exact": True,
            "canonical_rays": audited["canonical_ray_work_items"],
            "gpu_us": {stage: finite_gpu(audited, stage) for stage in STAGES},
        })
    return {
        "scenario": scene, "variant": VARIANT,
        "b1c_axis_proxy": axis_proxy,
        "b1c_axis_pack_cpu_us": pack_cpu if axis_proxy else None,
        "b1c_axis_packed_nodes": packed_nodes if axis_proxy else None,
        "pattern": pattern, "measured_frames": len(frames),
        "sampled_cpu_hit_candidate_frame": 1,
        "accepted_image_sha256": expected_sha(VARIANT, scene),
        "baseline_primary_bytes_equal_all_frames": True,
        "warmup_gpu_maintenance_us": history,
        "frames": result_frames,
    }


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("P1l-B1 median needs samples")
    return statistics.median(values)


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) != len(SCENARIOS) * PROCESSES:
        raise ValueError("P1l-B1 must have 15 complete processes")
    by_scene = {}
    for scene in SCENARIOS:
        selected = [r for r in runs if r["scenario"] == scene]
        if (len(selected) != PROCESSES or
            sorted(r["attempt"] for r in selected) != list(range(PROCESSES))):
            raise ValueError(f"P1l-B1 missing/duplicate process {scene}")
        paired = []
        per_process = []
        for run in sorted(selected, key=lambda x: x["attempt"]):
            frames = run["frames"]
            if (run["pattern"] != BALANCED or len(frames) != len(BALANCED)):
                raise ValueError("P1l-B1 process not full ABBA pattern")
            process_pairs = []
            for i in range(0, len(frames), 2):
                pair = frames[i:i+2]
                if sorted(f["arm"] for f in pair) != [0, 1]:
                    raise ValueError("P1l-B1 invalid adjacent AB or BA pair")
                baseline = next(f for f in pair if f["arm"] == 0)
                candidate = next(f for f in pair if f["arm"] == 1)
                differences = {}
                for stage in STAGES:
                    b = finite_gpu(baseline["gpu_us"], stage)
                    c = finite_gpu(candidate["gpu_us"], stage)
                    differences[stage] = {
                        "baseline_us": b, "candidate_us": c,
                        "delta_us": c - b,
                        "delta_percent": (c-b)/b*100 if b > 0 else None,
                        "faster": c < b,
                    }
                item = {
                    "attempt": run["attempt"], "pair_index": i//2,
                    "order": "".join(str(f["arm"]) for f in pair),
                    "differences": differences,
                }
                process_pairs.append(item)
                paired.append(item)
            per_process.append(process_pairs)
        if len(paired) != 36:
            raise ValueError("P1l-B1 expected 36 matched pairs per scene")
        stage_summaries = {}
        for stage in STAGES:
            diff = [p["differences"][stage]["delta_us"] for p in paired]
            pct = [p["differences"][stage]["delta_percent"] for p in paired]
            if any(v is None or not math.isfinite(v) for v in pct):
                raise ValueError("P1l-B1 invalid baseline GPU percent denominator")
            stage_summaries[stage] = {
                "pairs": 36, "median_delta_us": median(diff),
                "median_delta_percent": median(pct),
                "faster_pairs": sum(v < 0 for v in diff),
                "per_process_median_delta_us": [
                    median([x["differences"][stage]["delta_us"] for x in p])
                    for p in per_process
                ],
                "min_delta_us": min(diff), "max_delta_us": max(diff),
            }
        p = stage_summaries["primary_visibility_gpu"]
        c = stage_summaries["complete_renderer_gpu"]
        primary_win = (
            p["median_delta_percent"] <= -5 and
            p["faster_pairs"] >= 24 and
            sum(x < 0 for x in p["per_process_median_delta_us"]) >= 2
        )
        renderer_safe = c["median_delta_percent"] <= 3
        by_scene[scene] = {
            "metrics": stage_summaries,
            "primary_5percent_win": primary_win,
            "renderer_no_over3pct_regression": renderer_safe,
            "pairs": paired,
        }
    winning = [s for s in SCENARIOS if by_scene[s]["primary_5percent_win"]]
    safe = all(by_scene[s]["renderer_no_over3pct_regression"] for s in SCENARIOS)
    return {
        "scenarios": by_scene, "processes": len(runs),
        "measured_frames": sum(r["measured_frames"] for r in runs),
        "paired_samples": len(SCENARIOS)*36,
        "winning_scenes": winning,
        "renderer_regression_safe": safe,
        "decision": "ACCEPT_EXPLORATORY" if len(winning) >= 3 and safe
                    else "REJECT_OR_REFINE",
        "claims": ("Same-process paired GPU timestamps on one AMD RADV GPU. "
                   "An accepted image and primary-hit SHA/byte parity are "
                   "required; no portable HWRT-free speedup is implied."),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b1c", action="store_true",
                        help="run prospectively frozen B1c packed-axis variant")
    parser.add_argument("--preflight", action="store_true",
                        help="5 processes x two frozen 01 frames, no timing decision")
    args = parser.parse_args()
    pattern = PREFLIGHT if args.preflight else BALANCED
    processes = 1 if args.preflight else PROCESSES
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("P1l-B1 missing N006 binary; run mise run build")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene_file = pilot.ROOT / config["baseline"]["scene"]
    if (not scene_file.is_file() or
        pilot.sha256(scene_file) != config["baseline"]["scene_sha256"]):
        raise RuntimeError("P1l-B1 accepted Sponza scene missing/drifted")
    output_dir = (
        pilot.ROOT / "out/research/n006-interval-aware-allocation" /
        (("p1l-b1c" if args.b1c else "p1l-b1a") +
         ("-preflight" if args.preflight else "-matched")) /
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    summary_file = output_dir / (
        "n006-p1l-b1c-summary.json" if args.b1c else "n006-p1l-b1a-summary.json")
    summary: dict[str, Any] = {
        "protocol_version": B1C_PROTOCOL if args.b1c else PROTOCOL,
        "b1c_axis_proxy": args.b1c, "status": "in-progress",
        "mode": "preflight" if args.preflight else "matched",
        "formal": False, "reference_generated": False,
        "gpu": config["target_gpu"],
        "scene_sha256": config["baseline"]["scene_sha256"],
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "pattern": pattern, "processes_per_scene": processes,
        "measured_frames_per_process": len(pattern),
        "cpu_oracle_measured_frame": 1,
        "timeout_seconds": TIMEOUT_SECONDS,
        "runs": [], "failures": [],
    }

    def checkpoint() -> None:
        summary_file.write_text(
            json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    checkpoint()
    total = len(SCENARIOS)*processes
    for scenario in SCENARIOS:
        for attempt in range(processes):
            folder = output_dir / f"{scenario}-run-{attempt}"
            folder.mkdir(parents=True, exist_ok=False)
            command = [
                "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
                str(pilot.BINARY), "--scene", str(scene_file),
                "--artifact-dir", str(folder), "--scenario", scenario,
                "--variant", VARIANT, "--mode", "current",
                "--source-warmup-frames", str(SOURCE_WARMUPS),
                "--target-state-warmup-frames", str(TARGET_WARMUPS),
                "--target-frames", str(len(pattern)),
                "--skip-reference", "--canonical-lean-hash",
                "--p1l-b1-pattern", pattern,
                *(["--p1l-b1c-axis-proxy"] if args.b1c else []),
            ]
            print(f"[P1l-B1] start {scenario} attempt={attempt} "
                  f"({len(summary['runs'])+1}/{total}), timeout={TIMEOUT_SECONDS}s",
                  flush=True)
            try:
                try:
                    proc = subprocess.run(
                        command, cwd=pilot.ROOT, capture_output=True,
                        text=True, check=False, timeout=TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired as e:
                    def decoded(value: bytes | str | None) -> str:
                        if isinstance(value, bytes):
                            return value.decode("utf-8", errors="replace")
                        return value or ""
                    (folder / "stdout.log").write_text(
                        decoded(e.stdout), encoding="utf-8")
                    (folder / "stderr.log").write_text(
                        decoded(e.stderr), encoding="utf-8")
                    raise RuntimeError(f"P1l-B1 {scenario}/{attempt} timed out") from e
                (folder / "stdout.log").write_text(proc.stdout, encoding="utf-8")
                (folder / "stderr.log").write_text(proc.stderr, encoding="utf-8")
                if proc.returncode:
                    raise RuntimeError(
                        f"P1l-B1 {scenario}/{attempt} exited {proc.returncode}; "
                        f"see {folder/'stderr.log'}")
                raw_file = folder / pilot.EVIDENCE_NAME
                data = json.loads(raw_file.read_text(encoding="utf-8"))
                audited = audit_run(data, folder, config["target_gpu"],
                                    scenario, pattern, axis_proxy=args.b1c)
                audited["attempt"] = attempt
                audited["raw_evidence_sha256"] = hashlib.sha256(
                    raw_file.read_bytes()).hexdigest()
                summary["runs"].append(audited)
                print(f"[P1l-B1] accepted {len(summary['runs'])}/{total} "
                      f"{scenario} attempt={attempt}", flush=True)
            except (RuntimeError, ValueError, OSError, KeyError, TypeError) as e:
                summary["status"] = "invalid-retained"
                summary["failures"].append({
                    "scenario": scenario, "attempt": attempt,
                    "error": str(e), "stderr": str(folder/"stderr.log")})
                checkpoint()
                raise
            checkpoint()
    if not args.preflight:
        summary["results"] = aggregate(summary["runs"])
    else:
        summary["results"] = {
            "preflight_pass": True, "accepted_scenes": list(SCENARIOS),
            "valid_measured_frames": len(summary["runs"])*len(PREFLIGHT),
            "performance_decision": "NOT_MEASURED",
        }
    summary["status"] = "complete"
    checkpoint()
    print(json.dumps({
        "status": summary["status"], "mode": summary["mode"],
        "accepted_processes": len(summary["runs"]),
        "summary": str(summary_file),
        "decision": summary["results"].get("decision", "PREFLIGHT_ONLY"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, OSError, KeyError, TypeError) as e:
        print(f"P1l-B1 frozen near-first experiment failed: {e}", file=sys.stderr)
        raise SystemExit(1)

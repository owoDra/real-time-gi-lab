#!/usr/bin/env python3
"""N006 P1m0: five-scene exact-image canonical probe consumer coverage.

GPU diagnostics run only AFTER unchanged frame's timestamps, N004 oracle,
and HDR PFM capture. Counts are not marginal-ray-quality labels or GPU
speedup evidence. Retain errors and every attempted run.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import math
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from p1m1_calibration_selection import select_calibration_keys
from run_p1l_a1b_sampled_hit import (
    HASH_SLOTS, SCENE_EXPECTATIONS, SOURCE_WARMUPS, TARGET_WARMUPS,
    validate_frame, expected_sha,
)

PROTOCOL = "n006-p1m0-consumer-coverage-five-scenes-v1"
PRETRACE_PROTOCOL = "n006-p1m0b-pretrace-cost-five-scenes-v1"
# Prospective source-control fingerprints from independent completed M0 5/5:
# results/030-p1m0-five-scene-coverage-pass.md, original summary SHA256
# f355b7202e52127b044120ac8406e5dba4626dd88f4cf29a78f16abbc2c66cec.
# This test checks the same GPU signal is available PRE-SECONDARY, not gain.
FROZEN_M0 = {
    "static": ("020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2", 11400, 100),
    "camera-motion": ("ee0cebb3771f6cb2e43622f843b8ca9c7504c39f6f7239f9d887062e93c34e5e", 12437, 42),
    "light-motion": ("020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2", 11400, 100),
    "moving-rigid": ("189e6c69f3bd96f7b99cbb13cecba777e4094d35f7f47d42521d087380b95ec4", 11032, 38),
    "deforming-control": ("fea8628c854aa807deb08a222efc50d64be785ea680e859999a78feeea80c4fe", 11403, 100),
}
VARIANT = "lane-e-final-software"
SCENARIOS = ("static", "camera-motion", "light-motion",
             "moving-rigid", "deforming-control")
TIMEOUT_SECONDS = 600
# Independent accepted P1l-B0 one-frame SOFTWARE primary-valid-pixel
# counts, from result 021. An exact accepted PFM alone does not independently
# prove the diagnostic's validity mask matches the accepted primary shader.
VALID_PRIMARY_PIXELS = {
    "static": 12770, "camera-motion": 12629, "light-motion": 12770,
    "moving-rigid": 18357, "deforming-control": 12772,
}
METRICS = ("valid_primary_pixels", "lookup_attempts", "matched_lookups",
           "absent_keys", "invalid_keys", "probe_exhaustions",
           "uint32_overflows", "invalid_launch", "canonical_keys",
           "keys_with_consumers", "max_consumer_pixels")

def nonnegative_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"P1m0 invalid integer {name}")
    return value

def audit_coverage(cov: dict[str, Any], scenario: str) -> dict[str, Any]:
    if not isinstance(cov, dict) or cov.get("diagnostic_only") is not True:
        raise ValueError("P1m0 coverage missing or not marked diagnostic")
    owners, cascades = SCENE_EXPECTATIONS[scenario]
    stats = {name: nonnegative_int(cov.get(name), name) for name in METRICS}
    if nonnegative_int(cov.get("hash_capacity"), "hash_capacity") != HASH_SLOTS:
        raise ValueError("P1m0 unexpected canonical hash capacity")
    if (stats["canonical_keys"] != sum(cascades) or
        stats["lookup_attempts"] != stats["valid_primary_pixels"] * 4 or
        stats["valid_primary_pixels"] != VALID_PRIMARY_PIXELS[scenario] or
        stats["valid_primary_pixels"] > 320 * 180 or
        stats["matched_lookups"] + stats["absent_keys"] +
        stats["invalid_keys"] + stats["probe_exhaustions"] !=
        stats["lookup_attempts"] or
        stats["invalid_launch"] != 0 or stats["uint32_overflows"] != 0 or
        stats["probe_exhaustions"] != 0 or
        stats["keys_with_consumers"] > stats["canonical_keys"]):
        raise ValueError("P1m0 count closure, accepted canonical key or overflow failed")
    by_cascade = cov.get("consumer_lookups_by_cascade")
    keys_by_cascade = cov.get("keys_with_consumers_by_cascade")
    if (not isinstance(by_cascade, list) or len(by_cascade) != 4 or
        not isinstance(keys_by_cascade, list) or len(keys_by_cascade) != 4):
        raise ValueError("P1m0 per-cascade arrays missing")
    by_cascade = [nonnegative_int(x, "cascade_consumer_pixels")
                  for x in by_cascade]
    keys_by_cascade = [nonnegative_int(x, "cascade_keys_with_consumers")
                       for x in keys_by_cascade]
    rows = cov.get("key_rows")
    if not isinstance(rows, list) or len(rows) != stats["canonical_keys"]:
        raise ValueError("P1m0 missing full canonical key zero/nonzero rows")
    seen: set[int] = set()
    per_cascade_count = [0] * 4
    by_cascade_actual = [0] * 4
    keys_by_cascade_actual = [0] * 4
    owner_sum = 0
    consumer_sum = 0
    max_consumer = 0
    keys_with_consumers = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
            "token", "consumer_pixels", "producer_owner_outputs"
        }:
            raise ValueError(f"P1m0 invalid key row at {index}")
        token = nonnegative_int(row["token"], "token")
        consumers = nonnegative_int(row["consumer_pixels"], "consumer_pixels")
        owners_for_key = nonnegative_int(
            row["producer_owner_outputs"], "producer_owner_outputs")
        if (token in (0, 0xffffffff) or token > 0xffffffff or
            token in seen or (index and token <= rows[index-1]["token"]) or
            owners_for_key == 0 or consumers > stats["valid_primary_pixels"]):
            raise ValueError(f"P1m0 invalid/unsorted/nonunique canonical key at {index}")
        seen.add(token)
        cascade = (token - 1) >> 30
        if cascade >= 4:
            raise ValueError("P1m0 invalid encoded cascade")
        per_cascade_count[cascade] += 1
        owner_sum += owners_for_key
        consumer_sum += consumers
        max_consumer = max(max_consumer, consumers)
        by_cascade_actual[cascade] += consumers
        if consumers:
            keys_with_consumers += 1
            keys_by_cascade_actual[cascade] += 1
    if (per_cascade_count != list(cascades) or owner_sum != owners * 4 or
        consumer_sum != stats["matched_lookups"] or
        max_consumer != stats["max_consumer_pixels"] or
        keys_with_consumers != stats["keys_with_consumers"] or
        by_cascade_actual != by_cascade or
        keys_by_cascade_actual != keys_by_cascade):
        raise ValueError("P1m0 per-key/multiplicity/cascade conservation failed")
    if any(keys_by_cascade[i] > cascades[i] for i in range(4)):
        raise ValueError("P1m0 per-cascade coverage overcapacity")
    return {
        "diagnostic_only": True, **stats,
        "consumer_lookups_by_cascade": by_cascade,
        "keys_with_consumers_by_cascade": keys_by_cascade,
        "unconsumed_keys_by_cascade": [
            cascades[i] - keys_by_cascade[i] for i in range(4)
        ],
        "unconsumed_key_count": stats["canonical_keys"] -
                                 stats["keys_with_consumers"],
        "producer_owner_outputs": owner_sum,
        "key_rows_sha256": hashlib.sha256(json.dumps(
            rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }

def audit_case(data: dict[str, Any], folder: Path,
               gpu: str, scenario: str) -> dict[str, Any]:
    owners, _ = SCENE_EXPECTATIONS[scenario]
    if (
        data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("variant") != VARIANT or data.get("scenario") != scenario or
        data.get("mode") != "current" or
        data.get("p1m0_consumer_coverage") is not True or
        data.get("p1l_stage_fast") is not False or
        data.get("p1l_stage_probe") is not False or
        data.get("p1l_b0_counts") is not False or
        data.get("p1l_b1b_counts") is not False or
        data.get("p1l_b1_pattern") != "" or
        data.get("reference_generation") != "skipped" or
        data.get("source_warmup_frames") != SOURCE_WARMUPS or
        data.get("source_warmups_correct") is not True or
        data.get("device", {}).get("name") != gpu or
        data.get("source", {}).get("internal_correctness") is not True or
        data.get("target_state_warmup", {}).get("frames") != TARGET_WARMUPS or
        data.get("target_state_warmup", {}).get("correct") is not True or
        data.get("target_state_warmup", {}).get("last_visible_owners") != owners
    ):
        raise ValueError("P1m0 input GPU/source/target/protocol drift")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != 1:
        raise ValueError("P1m0 requires exactly one GPU frame/case")
    checked_frame = validate_frame(frames[0], 0, folder, VARIANT, scenario)
    coverage = audit_coverage(
        frames[0].get("p1m0_consumer_coverage"), scenario)
    return {
        "scenario": scenario,
        "expected_image_sha256": expected_sha(VARIANT, scenario),
        "actual_secondary_rays": checked_frame["canonical_ray_work_items"],
        "original_secondary_rays": checked_frame["original_ray_work_items"],
        "accepted_stage_timestamps_gpu_us": {
            key: value for key, value in checked_frame.items()
            if key.endswith("_gpu") or key in (
                "canonical_build_gpu", "post_producer_gpu")
        },
        "consumer_key_coverage": coverage,
    }

def audit_pretrace(cov: dict[str, Any], audited: dict[str, Any],
                   scenario: str, timing: dict[str, Any]) -> dict[str, Any]:
    if (cov.get("pretrace_executed") is not True or
        cov.get("pretrace_slot_byte_equal") is not True or
        cov.get("pretrace_stats_byte_equal") is not True):
        raise ValueError("P1m0b pre-secondary/postframe full-slot/stat parity failed")
    expected_hash, expected_matched, expected_keys = FROZEN_M0[scenario]
    if (audited["key_rows_sha256"] != expected_hash or
        audited["matched_lookups"] != expected_matched or
        audited["keys_with_consumers"] != expected_keys):
        raise ValueError("P1m0b pre-secondary counters drifted from accepted M0 5/5")
    cost = cov.get("pretrace_clear_and_count_gpu_us")
    bytes_ = nonnegative_int(cov.get("pretrace_scratch_bytes"),
                             "pretrace_scratch_bytes")
    if (type(cost) not in (float, int) or
        not math.isfinite(float(cost)) or cost <= 0 or
        bytes_ != (HASH_SLOTS + 8) * 4):
        raise ValueError("P1m0b GPU cost or 131104-byte scratch invalid")
    # Prospective, conservative illustrative cost feasibility check for
    # this pretrace counting stage; NOT a P1 predictive-quality or P2 GO.
    # A full P2 ROI still needs equal-K paired measurements and quality.
    complete = timing.get("complete_gi_gpu")
    traversal = timing.get("traversal_gpu")
    if (type(complete) not in (float, int) or
        type(traversal) not in (float, int) or
        complete <= 0 or traversal <= 0 or
        not math.isfinite(float(complete)) or
        not math.isfinite(float(traversal))):
        raise ValueError("P1m0b missing instrumented primary cost denominators")
    cost_limit = min(0.10 * float(complete), 0.50 * float(traversal))
    return {
        "pretrace_clear_dispatch_barrier_gpu_us": float(cost),
        "pretrace_scratch_bytes": bytes_,
        "full_slot_byte_equal_to_postframe": True,
        "eight_stats_byte_equal_to_postframe": True,
        "previous_m0_key_rows_sha256": expected_hash,
        "cost_gate": "within_predeclared_limit" if cost <= cost_limit
                     else "over_predeclared_limit",
        "predeclared_limit_gpu_us": cost_limit,
        "not": "marginal quality benefit, predictor, P2 performance, GPU ROI",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrace", action="store_true",
                        help="N006-only pre-secondary hash coverage cost + parity")
    args = parser.parse_args()
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("P1m0 binary missing: mise run build")
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise RuntimeError("P1m0 accepted Sponza scene absent/modified")
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation" /
            ("p1m0b-pretrace-coverage-five-scenes" if args.pretrace
             else "p1m0-consumer-coverage-five-scenes") /
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    dest.mkdir(parents=True, exist_ok=False)
    summary_file = dest / "n006-p1m0-consumer-coverage-summary.json"
    summary: dict[str, Any] = {
        "protocol_version": PRETRACE_PROTOCOL if args.pretrace else PROTOCOL,
        "status": "in-progress",
        "formal": False,
        "diagnostic_only": True,
        "target_device": cfg["target_gpu"],
        "source_sponza_sha256": cfg["baseline"]["scene_sha256"],
        "git": {"branch": pilot.EXPECTED_BRANCH, "head": head, "dirty": False},
        "source_warmup_frames": SOURCE_WARMUPS,
        "target_warmup_frames": TARGET_WARMUPS,
        "candidate_rays_added": 0,
        "reference_generated": False,
        "diagnostic_work_inside_accepted_timing": bool(args.pretrace),
        "prior_m0_upload_sha256": (
            "f355b7202e52127b044120ac8406e5dba4626dd88f4cf29a78f16abbc2c66cec"
            if args.pretrace else None),
        "case_matrix": list(SCENARIOS),
        "cases": [], "failures": [],
        "timeout_seconds_per_process": TIMEOUT_SECONDS,
        "status_meaning": "M0 lookup coverage only; no signed marginal quality label",
    }
    def save() -> None:
        summary_file.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    save()
    print(f"[P1m0] evidence root: {dest.resolve()}", flush=True)
    for scenario in SCENARIOS:
        folder = dest / scenario
        folder.mkdir(parents=True, exist_ok=False)
        cmd = [
            "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
            str(pilot.BINARY),
            "--scene", str(scene), "--artifact-dir", str(folder),
            "--scenario", scenario, "--variant", VARIANT, "--mode", "current",
            "--source-warmup-frames", "32",
            "--target-state-warmup-frames", "8", "--target-frames", "1",
            "--skip-reference", "--canonical-lean-hash",
            "--p1m0-consumer-coverage",
        ]
        if args.pretrace:
            cmd.append("--p1m0-pretrace-coverage")
        print(f"[P1m0] {scenario} ({len(summary['cases'])+1}/5); "
              f"stderr={folder.resolve() / 'stderr.log'}", flush=True)
        try:
            # Stream both child logs directly to durable files. capture_output
            # did not preserve useful partial progress when a long GPU/CPU
            # operation stalled and subprocess.run timed out.
            stdout_path = (folder / "stdout.log").resolve()
            stderr_path = (folder / "stderr.log").resolve()
            try:
                with stdout_path.open("wb") as stdout_stream, \
                     stderr_path.open("wb") as stderr_stream:
                    process = subprocess.run(
                        cmd, cwd=pilot.ROOT, stdout=stdout_stream,
                        stderr=stderr_stream, check=False,
                        timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as exc:
                stderr_tail = stderr_path.read_text(
                    encoding="utf-8", errors="replace")[-6000:]
                stdout_tail = stdout_path.read_text(
                    encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(
                    f"P1m0 {scenario} exceeded {TIMEOUT_SECONDS}s; "
                    f"last stage / stderr: {stderr_path}; "
                    f"stdout: {stdout_path}; "
                    f"stderr tail:\n{stderr_tail or '(no stderr)'}\n"
                    f"stdout tail:\n{stdout_tail or '(no stdout)'}"
                ) from exc
            if process.returncode:
                stderr_tail = stderr_path.read_text(
                    encoding="utf-8", errors="replace")[-6000:]
                stdout_tail = stdout_path.read_text(
                    encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(
                    f"P1m0 {scenario} exit {process.returncode}; "
                    f"stderr={stderr_path}; stdout={stdout_path}; "
                    f"stderr tail:\n{stderr_tail or '(no stderr)'}\n"
                    f"stdout tail:\n{stdout_tail or '(no stdout)'}")
            evidence_file = folder / pilot.EVIDENCE_NAME
            raw = evidence_file.read_bytes()
            data = json.loads(raw)
            result = audit_case(
                data, folder, cfg["target_gpu"], scenario)
            if args.pretrace:
                if data.get("p1m0_pretrace_coverage") is not True:
                    raise ValueError("P1m0b opt-in was not serialized by renderer")
                result["m0b_pretrace_cost"] = audit_pretrace(
                    data["frames"][0]["p1m0_consumer_coverage"],
                    result["consumer_key_coverage"], scenario,
                    data["frames"][0]["timing_us"])
                # The measured frame includes the opt-in GPU counting stage;
                # do not present it as accepted baseline stage timestamps.
                result["accepted_stage_timestamps_gpu_us"] = None
                result["instrumented_in_renderer_timing_us"] = (
                    data["frames"][0]["timing_us"])
            # Prospective M1 calibration strata are decided only after full
            # M0 SHA/counter/parity validation. No quality reference or gain
            # values are read to select these candidate canonical keys.
            key_rows = data["frames"][0]["p1m0_consumer_coverage"]["key_rows"]
            result["m1_calibration_only_selection"] = select_calibration_keys(key_rows)
            result["raw_evidence_sha256"] = hashlib.sha256(raw).hexdigest()
            summary["cases"].append(result)
            save()
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            summary["status"] = "invalid-retained"
            summary["failures"].append({
                "scenario": scenario, "error": str(exc),
                "stderr_path": str((folder / "stderr.log").resolve()),
                "stdout_path": str((folder / "stdout.log").resolve()),
            })
            save()
            print(f"[P1m0] failure report: {summary_file.resolve()}",
                  file=sys.stderr, flush=True)
            raise
    summary["status"] = "complete"
    if args.pretrace:
        summary["pretrace_cost_gate_status"] = (
            "within_predeclared_limit_5_of_5"
            if all(case["m0b_pretrace_cost"]["cost_gate"] ==
                   "within_predeclared_limit" for case in summary["cases"])
            else "over_predeclared_limit_no_m1_go")
    summary["m1_calibration_only_key_status"] = (
        "ready_calibration_only"
        if all(case["m1_calibration_only_selection"]["status"] ==
               "ready_calibration_only" for case in summary["cases"])
        else "incomplete_strata_no_intervention")
    summary["m1_calibration_only_selection_count"] = sum(
        case["m1_calibration_only_selection"]["actual_selection_count"]
        for case in summary["cases"])
    summary["m1_calibration_only_expected_selection_count"] = 60
    save()
    print(json.dumps({"status": "complete", "cases": len(summary["cases"]),
                      "summary": str(summary_file)},
                     indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(f"P1m0 diagnostic failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

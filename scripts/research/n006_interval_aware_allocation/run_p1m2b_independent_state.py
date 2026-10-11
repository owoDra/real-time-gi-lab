#!/usr/bin/env python3
"""N006 P1m2b — bounded, prospective observable-image screen.

Two original control processes per scenario are validated BEFORE any key
selection/extra-ray execution. Select at most one highest-consumer and one
zero-consumer canonical token per cascade with frozen token ties. Both
original-uniform and tetra direction arms get exactly four extra rays/key.
Changed images are checked in a second independent process; no quality labels.
No P2 scheduler, no extra scenes/keys chosen after influence outcomes.
"""
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
from run_p1m0_consumer_coverage import FROZEN_M0, audit_coverage
from run_p1l_a1b_sampled_hit import (
    HASH_SLOTS, SCENE_EXPECTATIONS, SOURCE_WARMUPS, TARGET_WARMUPS,
    expected_sha,
)
from run_p1m1a_canonical_probe_pilot import image_delta, read_pfm_payload

PROTOCOL = "n006-p1m2b-independent-state-observable-v1"
SCENARIOS = ("camera-motion", "light-motion")
ARMS = ("p1m1a-original", "p1m2a-tetra")
VARIANT = "lane-e-final-software"
PROCESS_TIMEOUT = 600
MAX_SELECTED_KEYS_PER_SCENE = 8
MAX_TREATMENT_CELLS = 32
RESULT_NAME = "n006-p1m2b-independent-state-summary.json"


def select_frozen_keys(rows: list[dict[str, int]]) -> dict[str, Any]:
    """Predeclared key selector: max coverage (tie lowest token), zero lowest."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("P1m2b selection requires full validated M0 rows")
    buckets: list[list[dict[str, int]]] = [[] for _ in range(4)]
    previous = 0
    for row in rows:
        if set(row) != {"token", "consumer_pixels", "producer_owner_outputs"}:
            raise ValueError("P1m2b unexpected key row schema")
        token, consumers, multiplicity = (
            row["token"], row["consumer_pixels"], row["producer_owner_outputs"])
        if (any(type(x) is not int for x in (token, consumers, multiplicity)) or
            token <= previous or token >= 0xffffffff or
            consumers < 0 or multiplicity <= 0):
            raise ValueError("P1m2b unvalidated or unsorted M0 key input")
        previous = token
        cascade = (token - 1) >> 30
        if cascade < 0 or cascade > 3:
            raise ValueError("P1m2b invalid cascade token")
        buckets[cascade].append(row)
    selected: list[dict[str, int | str]] = []
    missing: list[dict[str, int | str]] = []
    for cascade, bucket in enumerate(buckets):
        if not bucket:
            for stratum in ("max_consumer", "zero_consumer"):
                missing.append({"cascade": cascade, "stratum": stratum})
            continue
        highest = min(bucket, key=lambda row: (-row["consumer_pixels"], row["token"]))
        zero = next((row for row in bucket if row["consumer_pixels"] == 0), None)
        for stratum, row in (("max_consumer", highest), ("zero_consumer", zero)):
            if row is None:
                missing.append({"cascade": cascade, "stratum": stratum})
                continue
            if any(x["token"] == row["token"] for x in selected):
                missing.append({"cascade": cascade, "stratum": stratum,
                                "reason": "same_key_deduplicated"})
                continue
            selected.append({
                "cascade": cascade,
                "stratum": stratum,
                "token": row["token"],
                "consumer_pixels": row["consumer_pixels"],
                "producer_owner_outputs": row["producer_owner_outputs"],
            })
    if len(selected) > MAX_SELECTED_KEYS_PER_SCENE or len({
        x["token"] for x in selected}) != len(selected):
        raise ValueError("P1m2b selection exceeded budget or was non-unique")
    return {"selected": selected, "missing_strata": missing}


def verify_frame(data: dict[str, Any], scenario: str, gpu: str,
                 token: int, arm: str) -> dict[str, Any]:
    if scenario not in SCENARIOS or arm not in ("control", *ARMS):
        raise ValueError("P1m2b invalid predeclared scenario or arm")
    owners, cascades = SCENE_EXPECTATIONS[scenario]
    outputs = sum(cascades)
    base_rays = outputs * 8
    intervention = token != 0
    if ((arm == "control") != (not intervention) or
        data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("variant") != VARIANT or data.get("scenario") != scenario or
        data.get("mode") != "current" or
        data.get("p1m2b_independent_state") is not True or
        data.get("p1m1_canonical_token") != token or
        data.get("p1m2_tetra_octant_directions") is not (
            intervention and arm == "p1m2a-tetra") or
        data.get("p1m0_consumer_coverage") is not True or
        data.get("p1m0_pretrace_coverage") is not False or
        data.get("source_warmup_frames") != SOURCE_WARMUPS or
        data.get("source_warmups_correct") is not True or
        data.get("target_state_warmup", {}).get("frames") != TARGET_WARMUPS or
        data.get("target_state_warmup", {}).get("correct") is not True or
        data.get("target_state_warmup", {}).get("last_visible_owners") != owners or
        data.get("device", {}).get("name") != gpu or
        data.get("source", {}).get("internal_correctness") is not True or
        data.get("reference_generation") != "skipped"):
        raise ValueError("P1m2b scene/device/state/branch arm contract drift")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != 1:
        raise ValueError("P1m2b expects exactly one independent target frame")
    frame = frames[0]
    stats, extra, hits = (
        frame.get("stats", {}), frame.get("extra", {}),
        frame.get("hit_diagnostics", {}))
    can = extra.get("canonical", {})
    trace = extra.get("canonical_m1", {})
    if (frame.get("index") != 0 or frame.get("motion_fraction") != 1.0 or
        frame.get("owner_budget") != 0 or
        frame.get("internal_correctness") is not True or
        not isinstance(hits, dict) or hits.get("substantive_mismatches") != 0 or
        stats.get("visible_owners") != owners or
        stats.get("outputs") != outputs or
        stats.get("work_items") != base_rays + (4 if intervention else 0) or
        stats.get("storage_updates") != outputs or
        stats.get("storage_failures") != 0 or stats.get("overflow") != 0 or
        extra.get("base_prefix_correct") is not True or
        extra.get("extra_work_correct") is not True or
        extra.get("base_traced_rays") != base_rays or
        extra.get("extra_rays_traced") != (4 if intervention else 0) or
        can.get("executed") is not True or
        can.get("copyback_executed") is not True or
        can.get("canonical_outputs") != outputs or
        can.get("canonical_work_items") != base_rays or
        can.get("hash_slots") != HASH_SLOTS or
        can.get("unique_by_cascade") != list(cascades) or
        can.get("original_outputs") != owners * 4 or
        can.get("original_work_items") != owners * 4 * 8 or
        can.get("weighted_owner_total") != owners * 4 or
        can.get("owner_weight_errors") != 0 or
        can.get("invalid_keys") != 0 or can.get("failed_inserts") != 0 or
        can.get("index_overflows") != 0):
        raise ValueError("P1m2b canonical prefix/tracing/owner/hit parity failure")
    raw_coverage = frame.get("p1m0_consumer_coverage")
    coverage = audit_coverage(raw_coverage, scenario)
    fingerprint, matched, used_keys = FROZEN_M0[scenario]
    if (coverage["key_rows_sha256"] != fingerprint or
        coverage["matched_lookups"] != matched or
        coverage["keys_with_consumers"] != used_keys):
        raise ValueError("P1m2b original accepted M0 rows fingerprint mismatch")
    if intervention:
        matching = [r for r in raw_coverage["key_rows"] if r["token"] == token]
        if len(matching) != 1 or
            trace.get("executed") is not True or
            trace.get("selected_token") != token or
            type(trace.get("output_id")) is not int or
            not 0 <= trace["output_id"] < outputs or
            trace.get("base_ray_count") != 8 or
            trace.get("extra_ray_count") != 4 or
            trace.get("merged_sample_count") != 12):
            raise ValueError("P1m2b selected canonical output mismatch")
        base_sum = trace.get("base_radiance_sum16")
        tail_sum = trace.get("extra_radiance_sum16")
        if (type(base_sum) is not int or type(tail_sum) is not int or
            base_sum < 0 or tail_sum < 0 or
            trace.get("baseline_mean16") != (base_sum + 4) // 8 or
            trace.get("candidate_mean16") !=
                (base_sum + tail_sum + 6) // 12):
            raise ValueError("P1m2b 8+4 integer radiance closure mismatch")
        fields = (
            "base_hit_count", "base_positive_radiance_rays",
            "extra_hit_count", "extra_miss_count",
            "extra_positive_radiance_rays", "extra_hit_zero_radiance_rays")
        if any(type(trace.get(f)) is not int or trace[f] < 0 for f in fields):
            raise ValueError("P1m2b GPU hit/radiance fields absent or invalid")
        if (trace["base_hit_count"] > 8 or
            trace["base_positive_radiance_rays"] > trace["base_hit_count"] or
            trace["extra_hit_count"] + trace["extra_miss_count"] != 4 or
            trace["extra_positive_radiance_rays"] +
                trace["extra_hit_zero_radiance_rays"] != trace["extra_hit_count"] or
            trace["extra_positive_radiance_rays"] > tail_sum or
            trace["base_positive_radiance_rays"] > base_sum):
            raise ValueError("P1m2b GPU hit/fate closure mismatch")
        cost = trace.get("extra_injection_gpu_us")
        if (not isinstance(cost, (float, int)) or
            isinstance(cost, bool) or not math.isfinite(float(cost)) or
            cost <= 0):
            raise ValueError("P1m2b invalid append GPU timestamp")
    elif trace != {"executed": False}:
        raise ValueError("P1m2b control unexpectedly contains tail rays")
    return {
        "original_owner_count": owners,
        "canonical_outputs": outputs,
        "base_rays": base_rays,
        "actual_rays": stats["work_items"],
        "coverage_sha256": coverage["key_rows_sha256"],
        "matched_lookups": coverage["matched_lookups"],
        "keys_with_consumers": coverage["keys_with_consumers"],
        "selected_key_row": matching[0] if intervention else None,
        "canonical_m1_trace": trace,
        "key_rows": raw_coverage["key_rows"] if not intervention else None,
    }


def run_once(root: Path, scenario: str, label: str, token: int, arm: str,
             scene_path: Path, gpu: str) -> tuple[dict[str, Any], bytes]:
    folder = root / scenario / label
    folder.mkdir(parents=True, exist_ok=False)
    command = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY),
        "--scene", str(scene_path),
        "--artifact-dir", str(folder), "--scenario", scenario,
        "--variant", VARIANT, "--mode", "current",
        "--source-warmup-frames", str(SOURCE_WARMUPS),
        "--target-state-warmup-frames", str(TARGET_WARMUPS),
        "--target-frames", "1", "--skip-reference", "--canonical-lean-hash",
        "--p1m0-consumer-coverage", "--p1m2b-independent-state",
    ]
    if token:
        command += ["--p1m1-canonical-token", str(token)]
        if arm == "p1m2a-tetra":
            command.append("--p1m2-tetra-octant-directions")
    out, err = folder / "stdout.log", folder / "stderr.log"
    print(f"[P1m2b] {scenario}/{label}, token={token}, arm={arm}", flush=True)
    try:
        with out.open("wb") as a, err.open("wb") as b:
            process = subprocess.run(command, cwd=pilot.ROOT, stdout=a,
                                     stderr=b, timeout=PROCESS_TIMEOUT,
                                     check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"P1m2b {scenario}/{label} timed out, log={err}") from exc
    if process.returncode:
        raise RuntimeError(
            f"P1m2b {scenario}/{label} renderer exited {process.returncode}; "
            f"stderr tail:\n{err.read_text(errors='replace')[-3500:]}")
    raw = (folder / pilot.EVIDENCE_NAME).read_bytes()
    checked = verify_frame(json.loads(raw), scenario, gpu, token, arm)
    data = json.loads(raw)
    rel = Path(data["frames"][0]["image"])
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("P1m2b unsafe PFM path")
    image = folder / rel
    payload = read_pfm_payload(image)
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    checked["image_sha256"] = digest
    checked["raw_renderer_evidence_sha256"] = hashlib.sha256(raw).hexdigest()
    checked["label"] = label
    checked["arm"] = arm
    checked["token"] = token
    checked["scenario"] = scenario
    return checked, payload


def main() -> int:
    head = pilot.require_clean_branch()
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise ValueError("P1m2b source scene SHA mismatch")
    if not pilot.BINARY.is_file():
        raise ValueError("P1m2b renderer binary missing")
    root = (
        pilot.ROOT / "out/research/n006-interval-aware-allocation" /
        "p1m2b-independent-state" /
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    root.mkdir(parents=True, exist_ok=False)
    path = root / RESULT_NAME
    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "calibration_only": True,
        "reference_generated": False, "predictive_quality_established": False,
        "scenarios": list(SCENARIOS), "direction_arms": list(ARMS),
        "max_treatment_cells": MAX_TREATMENT_CELLS,
        "source_scene_sha256": config["baseline"]["scene_sha256"],
        "target_gpu": config["target_gpu"],
        "git": {"branch": pilot.EXPECTED_BRANCH, "head": head, "dirty": False},
        "controls": [], "selections": {}, "cases": [], "failures": [],
        "observable_replicated_cells": [], "total_treatment_cells": 0,
    }

    def save() -> None:
        path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    save()

    try:
        for scenario in SCENARIOS:
            controls = []
            payloads = []
            for replica in (0, 1):
                case, payload = run_once(root, scenario, f"control_{replica}",
                                         0, "control", scene, config["target_gpu"])
                if case["image_sha256"] != expected_sha(VARIANT, scenario):
                    raise ValueError(f"P1m2b {scenario} original accepted image SHA drift")
                controls.append(case)
                payloads.append(payload)
                summary["controls"].append({
                    k: v for k, v in case.items() if k != "key_rows"
                })
                save()
            if (controls[0]["image_sha256"] != controls[1]["image_sha256"] or
                payloads[0] != payloads[1] or
                controls[0]["key_rows"] != controls[1]["key_rows"] or
                controls[0]["coverage_sha256"] != controls[1]["coverage_sha256"]):
                raise ValueError(f"P1m2b {scenario} control-control instability")
            frozen = select_frozen_keys(controls[0]["key_rows"])
            selected = frozen["selected"]
            if len(selected) > MAX_SELECTED_KEYS_PER_SCENE:
                raise ValueError("P1m2b too many scenario keys")
            summary["selections"][scenario] = {
                **frozen, "control_sha256": controls[0]["image_sha256"],
                "key_rows_sha256": controls[0]["coverage_sha256"],
            }
            # Selection table is persisted BEFORE any extra GPU work.
            save()
            for selection in selected:
                token = int(selection["token"])
                for arm in ARMS:
                    if summary["total_treatment_cells"] >= MAX_TREATMENT_CELLS:
                        raise ValueError("P1m2b prospective intervention budget exceeded")
                    label = f"c{selection['cascade']}_{selection['stratum']}_{token}_{arm}"
                    case, payload = run_once(root, scenario, label, token,
                                             arm, scene, config["target_gpu"])
                    if (case["coverage_sha256"] != controls[0]["coverage_sha256"] or
                        case["selected_key_row"] != {
                            "token": token,
                            "consumer_pixels": selection["consumer_pixels"],
                            "producer_owner_outputs": selection["producer_owner_outputs"],
                        }):
                        raise ValueError(f"P1m2b {scenario}/{label} selected pretrace key drift")
                    delta = image_delta(payloads[0], payload)
                    if (delta["changed_rgb_pixels"] == 0) != (
                            case["image_sha256"] == controls[0]["image_sha256"]):
                        raise ValueError("P1m2b raw float PFM channel/image SHA discrepancy")
                    case.pop("key_rows")
                    case["stratum"] = selection["stratum"]
                    case["consumer_pixels"] = selection["consumer_pixels"]
                    case["image_delta_vs_control"] = delta
                    summary["cases"].append(case)
                    summary["total_treatment_cells"] += 1
                    save()
                    if delta["changed_rgb_pixels"]:
                        repeated, again = run_once(
                            root, scenario, label + "_repeat", token,
                            arm, scene, config["target_gpu"])
                        if (repeated["coverage_sha256"] != case["coverage_sha256"] or
                            repeated["selected_key_row"] != case["selected_key_row"] or
                            repeated["image_sha256"] != case["image_sha256"] or
                            again != payload or
                            image_delta(payloads[0], again) != delta):
                            raise ValueError(f"P1m2b {scenario}/{label} nonreplicated HDR influence")
                        case["repeat_image_sha256"] = repeated["image_sha256"]
                        case["repeat_raw_renderer_sha256"] = (
                            repeated["raw_renderer_evidence_sha256"])
                        case["reproduced"] = True
                        summary["observable_replicated_cells"].append({
                            "scenario": scenario, "token": token,
                            "arm": arm, "delta": delta,
                        })
                        save()
        summary["status"] = (
            "observable-influence-screen-complete"
            if summary["observable_replicated_cells"]
            else "bounded-observable-null-stop"
        )
        summary["next_gate"] = (
            "independent converged HDR common reference, paired signed RMS, "
            "noise and sealed trajectory holdout; NOT quality/P2 GO"
            if summary["observable_replicated_cells"] else
            "STOP this +4-ray/current-integer-quantization family; "
            "new representation requires a distinct prospective protocol"
        )
        save()
        print(json.dumps({"status": summary["status"],
                          "total_treatment_cells": summary["total_treatment_cells"],
                          "replicated_changed_cells": len(summary["observable_replicated_cells"]),
                          "summary": str(path)}, indent=2), flush=True)
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        summary["status"] = "invalid-retained"
        summary["failures"].append({"error": str(exc)})
        save()
        print(f"[P1m2b] invalid retained: {exc}; summary: {path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        print(f"P1m2b setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

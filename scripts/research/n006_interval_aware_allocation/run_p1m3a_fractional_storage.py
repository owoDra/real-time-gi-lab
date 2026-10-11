#!/usr/bin/env python3
"""P1m3a opt-in fractional-Q8 storage feasibility: CALIBRATION ONLY.

Frozen exact scenarios/cells from the already-exposed M2b sample.
Two separately-warmed Q8 controls/scenario. No independent quality reference,
no P2 scheduler. Old accepted image SHA not required for Q8 controls.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from run_p1l_a1b_sampled_hit import expected_sha
from run_p1m1a_canonical_probe_pilot import image_delta, read_pfm_payload
from run_p1m2b_independent_state import (
    PROCESS_TIMEOUT, RESULT_NAME as OLD_M2B_NAME, VARIANT,
    verify_frame,
)

PROTOCOL = "n006-p1m3a-fractional-q8-storage-calibration-v1"
RESULT_NAME = "n006-p1m3a-fractional-storage-summary.json"
# Original M2b integer sums are EXPOSED CALIBRATION, not independent holdouts.
# (token, consumer_pixels, producer_owner_outputs, original_base_sum16,
# original_extra_sum16, expected_fractional_change)
FROZEN = {
    "camera-motion": (
        (1084233745, 36, 2, 0, 2, True),
        (3223324678, 919, 84, 10, 0, True),
        (2152730633, 153, 1, 0, 0, False),
    ),
    "light-motion": (
        (3223324678, 875, 125, 1, 0, True),
    ),
}
Q8 = 256


def q8_value(total: int, count: int) -> int:
    if type(total) is not int or type(count) is not int or total < 0 or count <= 0:
        raise ValueError("P1m3a invalid fixed-point sample")
    return (total * Q8 + count // 2) // count


def run_case(root: Path, scene_path: Path, scenario: str,
             label: str, token: int, gpu: str) -> tuple[dict[str, Any], bytes]:
    folder = root / scenario / label
    folder.mkdir(parents=True, exist_ok=False)
    cmd = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY), "--scene", str(scene_path),
        "--artifact-dir", str(folder), "--scenario", scenario,
        "--variant", VARIANT, "--mode", "current",
        "--source-warmup-frames", "32",
        "--target-state-warmup-frames", "8", "--target-frames", "1",
        "--skip-reference", "--canonical-lean-hash",
        "--p1m0-consumer-coverage", "--p1m2b-independent-state",
        "--p1m3-fractional-storage",
    ]
    if token:
        cmd.extend(["--p1m1-canonical-token", str(token)])
    print(f"[P1m3a] {scenario}/{label}, Q8, token={token}", flush=True)
    stdout, stderr = folder / "stdout.log", folder / "stderr.log"
    try:
        with stdout.open("wb") as o, stderr.open("wb") as e:
            run = subprocess.run(
                cmd, cwd=pilot.ROOT, stdout=o, stderr=e,
                timeout=PROCESS_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"P1m3a {scenario}/{label} timeout: {stderr}") from exc
    if run.returncode:
        raise RuntimeError(
            f"P1m3a {scenario}/{label} exit={run.returncode}; "
            f"stderr tail:\n{stderr.read_text(errors='replace')[-5000:]}")
    evidence = (folder / pilot.EVIDENCE_NAME).read_bytes()
    data = json.loads(evidence)
    if data.get("p1m3_fractional_storage") is not True:
        raise ValueError("P1m3a opt-in Q8 renderer evidence missing")
    arm = "control" if not token else "p1m1a-original"
    verified = verify_frame(data, scenario, gpu, token, arm)
    image_rel = Path(data["frames"][0]["image"])
    if image_rel.is_absolute() or ".." in image_rel.parts:
        raise ValueError("P1m3a unsafe PFM path")
    image = folder / image_rel
    payload = read_pfm_payload(image)
    verified["image_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    verified["raw_evidence_sha256"] = hashlib.sha256(evidence).hexdigest()
    verified["scenario"] = scenario
    verified["label"] = label
    verified["token"] = token
    return verified, payload


def main() -> int:
    head = pilot.require_clean_branch()
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene_path = pilot.ROOT / config["baseline"]["scene"]
    if (not scene_path.is_file() or
        pilot.sha256(scene_path) != config["baseline"]["scene_sha256"]):
        raise ValueError("P1m3a Sponza source missing or fingerprint drift")
    if not pilot.BINARY.is_file():
        raise ValueError("P1m3a N006 renderer missing; build first")
    root = (
        pilot.ROOT / "out/research/n006-interval-aware-allocation" /
        "p1m3a-fractional-q8-calibration" /
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    root.mkdir(parents=True, exist_ok=False)
    summary_file = root / RESULT_NAME
    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL,
        "status": "in-progress",
        "formal": False,
        "calibration_only": True,
        "independent_reference_generated": False,
        "signed_quality_gain_established": False,
        "representation": "Q8-uint-storage",
        "fractional_bits": 8,
        "gpu": config["target_gpu"],
        "scene_sha256": config["baseline"]["scene_sha256"],
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "frozen_case_matrix": {k: [list(c) for c in v] for k,v in FROZEN.items()},
        "controls": [], "cases": [], "failures": [],
        "changed_confirmed_cells": [],
    }

    def save() -> None:
        summary_file.write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
    save()
    try:
        for scenario, frozen_cases in FROZEN.items():
            controls, payloads = [], []
            for replica in range(2):
                checked, pixels = run_case(
                    root, scene_path, scenario,
                    f"q8_control_{replica}", 0, config["target_gpu"])
                controls.append(checked)
                payloads.append(pixels)
                summary["controls"].append({
                    k: v for k, v in checked.items() if k != "key_rows"})
                summary["controls"][-1]["old_accepted_image_sha256"] = (
                    expected_sha(VARIANT, scenario))
                summary["controls"][-1]["same_as_old_accepted_image"] = (
                    checked["image_sha256"] == expected_sha(VARIANT, scenario))
                save()
            if (controls[0]["image_sha256"] != controls[1]["image_sha256"] or
                payloads[0] != payloads[1] or
                controls[0]["key_rows"] != controls[1]["key_rows"] or
                controls[0]["coverage_sha256"] != controls[1]["coverage_sha256"]):
                raise ValueError(f"P1m3a {scenario} two Q8 controls unstable")
            # Old, already observed M2b selected keys are calibration. Verify
            # the control's exact M0 row before candidate GPU computation.
            rows = {r["token"]: r for r in controls[0]["key_rows"]}
            for (token, consumers, owner_count, original_base, original_extra,
                 expected_fractional_change) in frozen_cases:
                if rows.get(token) != {
                    "token": token, "consumer_pixels": consumers,
                    "producer_owner_outputs": owner_count,
                }:
                    raise ValueError(
                        f"P1m3a {scenario}/{token} frozen original M0 row drift")
            summary.setdefault("frozen_key_selection", {})[scenario] = {
                "validated": True,
                "M0_coverage_sha256": controls[0]["coverage_sha256"],
                "Q8_control_PFM_sha256": controls[0]["image_sha256"],
                "cases": [c[0] for c in frozen_cases],
            }
            save()  # Persist selected keys before any new treatment.
            for (token, consumers, owner_count, original_base, original_extra,
                 predicted) in frozen_cases:
                label = f"q8_key_{token}"
                case, changed_payload = run_case(
                    root, scene_path, scenario, label, token, config["target_gpu"])
                tr = case["canonical_m1_trace"]
                if (case["coverage_sha256"] != controls[0]["coverage_sha256"] or
                    case["selected_key_row"] != rows[token] or
                    tr["base_radiance_sum16"] != original_base or
                    tr["extra_radiance_sum16"] != original_extra):
                    raise ValueError(
                        f"P1m3a {scenario}/{token} unchanged-ray/M0 parity failed")
                predicted_delta = (
                    q8_value(original_base + original_extra, 12) -
                    q8_value(original_base, 8))
                if bool(predicted_delta) != predicted:
                    raise ValueError("P1m3a frozen Q8 counterfactual contradiction")
                delta = image_delta(payloads[0], changed_payload)
                if (delta["changed_rgb_pixels"] == 0) != (
                    case["image_sha256"] == controls[0]["image_sha256"]):
                    raise ValueError("P1m3a PFM image diff versus SHA disagreement")
                case.pop("key_rows", None)
                case["consumer_pixels"] = consumers
                case["expected_Q8_numerator_delta"] = predicted_delta
                case["expected_fractional_change"] = predicted
                case["image_delta_vs_Q8_control"] = delta
                summary["cases"].append(case)
                save()
                if delta["changed_rgb_pixels"]:
                    repeated, repeated_payload = run_case(
                        root, scene_path, scenario,
                        label + "_repeat", token, config["target_gpu"])
                    if (repeated["image_sha256"] != case["image_sha256"] or
                        repeated_payload != changed_payload or
                        repeated["coverage_sha256"] != case["coverage_sha256"] or
                        repeated["selected_key_row"] != case["selected_key_row"] or
                        repeated["canonical_m1_trace"]["base_radiance_sum16"] != original_base or
                        repeated["canonical_m1_trace"]["extra_radiance_sum16"] != original_extra):
                        raise ValueError(f"P1m3a {scenario}/{token} Q8 nonreplication")
                    case["reproduced"] = True
                    case["repeat_image_sha256"] = repeated["image_sha256"]
                    if not predicted:
                        raise ValueError(
                            "P1m3a negative-control key unexpectedly affected image")
                    summary["changed_confirmed_cells"].append({
                        "scenario": scenario, "token": token,
                        "consumer_pixels": consumers, "delta": delta,
                    })
                    save()
        if summary["changed_confirmed_cells"]:
            summary["status"] = "fractional-storage-mechanism-go-only"
            summary["next_gate"] = (
                "prospective distinct holdout and SAME-Q8-representation "
                "independent converged HDR reference with paired signed RMS, "
                "repeat uncertainty and cost; P2 remains NO GO")
        else:
            summary["status"] = "fractional-storage-mechanism-stop"
            summary["next_gate"] = (
                "Q8 storage had no observable nonzero PFM influence on "
                "prespecified consumer-positive arithmetic calibration cells. "
                "STOP P1m3a; no S retuning, cherry-picking, or P2 GO.")
        save()
        print(json.dumps({
            "status": summary["status"],
            "cases": len(summary["cases"]),
            "confirmed_nonzero": len(summary["changed_confirmed_cells"]),
            "summary": str(summary_file),
        }, indent=2), flush=True)
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        summary["status"] = "invalid-retained"
        summary["failures"].append({"error": str(exc)})
        save()
        print(f"[P1m3a] invalid: {exc}; summary={summary_file}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        print(f"[P1m3a] setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""N006 P1m3b: moving-rigid Q8 holdout vs two disjoint CPU reference seeds.

Prospectively frozen after P1m3a calibration: 4 per-cascade max-consumer
keys, one global zero-consumer negative; original uniform +4 only. Common
independently converged 8-bounce HDR reference pair, 2 GPU controls and
isolated case reproductions. A changed pixel is not automatically a benefit.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from run_p1l_a1b_sampled_hit import expected_sha
from run_p1m1a_canonical_probe_pilot import image_delta, read_pfm_payload
from run_p1m2b_independent_state import verify_frame, VARIANT

PROTOCOL = "n006-p1m3b-moving-rigid-q8-two-reference-signed-v1"
SCENARIO = "moving-rigid"
Q8 = 256
MAX_CASES = 5
RESULT_NAME = "n006-p1m3b-moving-rigid-signed-quality-summary.json"
REFERENCED_TIMEOUT = 7200
GPU_TIMEOUT = 600
MIN_SPP = 512
MAX_SPP = 8192
# Conservative, not a confidence interval or a P2 gate.
NOISE_RULE = "both_signed_gains_strictly_exceed_RMS_between_independent_CPU_references"


def select_prospective_holdout(rows: list[dict[str, int]]) -> dict[str, Any]:
    """Max-consumer smallest token per cascade + global min zero token."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("P1m3b requires accepted complete M0 rows")
    buckets: list[list[dict[str, int]]] = [[] for _ in range(4)]
    seen: set[int] = set()
    prev = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "token", "consumer_pixels", "producer_owner_outputs"
        }:
            raise ValueError("P1m3b malformed key row")
        token, consumers, owners = (
            row["token"], row["consumer_pixels"], row["producer_owner_outputs"])
        if (any(type(x) is not int for x in (token, consumers, owners)) or
            token <= prev or token >= 0xffffffff or
            consumers < 0 or owners <= 0 or token in seen):
            raise ValueError("P1m3b invalid or unsorted M0 key rows")
        prev = token
        seen.add(token)
        cascade = (token - 1) >> 30
        if not 0 <= cascade < 4:
            raise ValueError("P1m3b invalid cascade")
        buckets[cascade].append(row)
    selected = []
    missing = []
    for cascade, bucket in enumerate(buckets):
        positives = [row for row in bucket if row["consumer_pixels"] > 0]
        if not positives:
            missing.append({"cascade": cascade, "stratum": "max_positive"})
            continue
        pick = min(positives, key=lambda row: (-row["consumer_pixels"], row["token"]))
        selected.append({**pick, "cascade": cascade, "stratum": "max_positive"})
    zeros = [x for x in rows if x["consumer_pixels"] == 0]
    if zeros:
        negative = min(zeros, key=lambda x: x["token"])
        if negative["token"] not in {x["token"] for x in selected}:
            selected.append({
                **negative, "cascade": (negative["token"] - 1) >> 30,
                "stratum": "global_zero_negative",
            })
    else:
        missing.append({"cascade": None, "stratum": "global_zero_negative"})
    if len(selected) > MAX_CASES:
        raise ValueError("P1m3b frozen intervention cap exceeded")
    return {
        "selected": selected, "missing_strata": missing,
        "selection_basis": "M0 full raw rows ONLY, before extra ray or reference-quality inspection",
    }


def rgb_rms(a: bytes, b: bytes) -> float:
    if len(a) != len(b) or len(a) != 320 * 180 * 3 * 4:
        raise ValueError("P1m3b RGB payload size mismatch")
    diff_sq = 0.0
    for va, vb in zip(struct.iter_unpack("<f", a),
                      struct.iter_unpack("<f", b), strict=True):
        x, y = va[0], vb[0]
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("P1m3b nonfinite HDR value")
        diff_sq += (float(x)-float(y)) ** 2
    return math.sqrt(diff_sq / (320 * 180 * 3))


def safe_image(folder: Path, raw: object) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError("P1m3b missing renderer relative path")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("P1m3b unsafe renderer image path")
    path = folder / relative
    if not path.is_file():
        raise ValueError(f"P1m3b missing renderer PFM {relative}")
    return path


def reference_pair(folder: Path, evidence: dict[str, Any]) -> tuple[dict[str, Any], bytes, bytes]:
    frame = evidence["frames"][0]
    files = []
    buffers = []
    for key in ("reference", "reference_independent"):
        meta = frame.get(key)
        if not isinstance(meta, dict) or meta.get("converged") is not True:
            raise ValueError(f"P1m3b {key} N001 reference did not converge")
        spp = meta.get("spp")
        if type(spp) is not int or not MIN_SPP <= spp <= MAX_SPP:
            raise ValueError(f"P1m3b {key} SPP outside accepted bounds")
        for field, limit in (("replicate_p99_abs_luminance", 0.001),
                             ("replicate_p99_relative_luminance", 0.01)):
            value = meta.get(field)
            if (type(value) not in (int, float) or
                not math.isfinite(float(value)) or value > limit or value < 0):
                raise ValueError(f"P1m3b {key} convergence {field} failed")
        file = safe_image(folder, meta.get("path"))
        files.append({**meta, "SHA256": hashlib.sha256(file.read_bytes()).hexdigest()})
        buffers.append(read_pfm_payload(file))
    if files[0]["SHA256"] == files[1]["SHA256"]:
        # Distinct seeds are verified from the C++ source static regression.
        raise ValueError("P1m3b two independent reference images identical; cannot bound noise")
    noise = rgb_rms(buffers[0], buffers[1])
    if noise <= 0 or not math.isfinite(noise):
        raise ValueError("P1m3b nonpositive or nonfinite independent reference RMS")
    return {
        "N001_CPU_references": files,
        "RMS_reference_A_vs_B": noise,
        "reference_seed_A_B": [0x12345678, 0x9abcdef0],
        "independent_reference_seed_A_B": [
            0x517cc1b727220a95, 0x8b8b8b8b4f1bbcdd,
        ],
    }, buffers[0], buffers[1]


def run_case(root: Path, scene: Path, gpu: str,
             label: str, token: int, with_reference: bool, *,
             scenario: str = SCENARIO) -> tuple[
                 dict[str, Any], bytes, dict[str, Any], Path]:
    if scenario not in ("moving-rigid", "deforming-control"):
        raise ValueError("P1m3b/M3c unexpected scenario")
    flag = ("--p1m3b-holdout-quality" if scenario == "moving-rigid"
            else "--p1m3c-reference-preflight")
    folder = root / label
    folder.mkdir(parents=True, exist_ok=False)
    cmd = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY), "--scene", str(scene),
        "--artifact-dir", str(folder),
        "--scenario", scenario, "--variant", VARIANT,
        "--mode", "current", "--source-warmup-frames", "32",
        "--target-state-warmup-frames", "8", "--target-frames", "1",
        "--canonical-lean-hash", "--p1m0-consumer-coverage",
        "--p1m2b-independent-state", "--p1m3-fractional-storage",
        flag,
    ]
    if not with_reference:
        cmd.append("--skip-reference")
    if token:
        cmd += ["--p1m1-canonical-token", str(token)]
    print(f"[P1m3b] {label}: key={token}, common reference={with_reference}", flush=True)
    stdout, stderr = folder / "stdout.log", folder / "stderr.log"
    try:
        with stdout.open("wb") as out, stderr.open("wb") as err:
            done = subprocess.run(
                cmd, cwd=pilot.ROOT, stdout=out, stderr=err,
                timeout=REFERENCED_TIMEOUT if with_reference else GPU_TIMEOUT,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"P1m3b {label} GPU/reference timeout; stderr {stderr}") from exc
    if done.returncode:
        raise RuntimeError(
            f"P1m3b {label} renderer exit {done.returncode}, stderr: "
            + stderr.read_text(errors="replace")[-5000:])
    binary = (folder / pilot.EVIDENCE_NAME).read_bytes()
    evidence = json.loads(binary)
    valid = verify_frame(
        evidence, scenario, gpu, token,
        "control" if token == 0 else "p1m1a-original",
        holdout=True, require_reference=with_reference,
    )
    frame = evidence["frames"][0]
    pfm = safe_image(folder, frame.get("image"))
    data = read_pfm_payload(pfm)
    valid.update({
        "label": label, "scenario": SCENARIO, "selected_token": token,
        "image_sha256": hashlib.sha256(pfm.read_bytes()).hexdigest(),
        "renderer_evidence_sha256": hashlib.sha256(binary).hexdigest(),
        "extra_reference_generated": with_reference,
    })
    return valid, data, evidence, folder


def main() -> int:
    head = pilot.require_clean_branch()
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise ValueError("P1m3b independent Sponza geometry SHA mismatch")
    if not pilot.BINARY.is_file():
        raise ValueError("P1m3b intervention binary missing")
    root = (pilot.ROOT / "out/research/n006-interval-aware-allocation" /
            "p1m3b-moving-rigid-q8-signed" /
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    root.mkdir(parents=True, exist_ok=False)
    summary_path = root / RESULT_NAME
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "single_trajectory_same_geometry": True,
        "reference_generated": False, "P1_predictor_go": False,
        "P2_scheduler_go": False, "quality_gain_established": False,
        "noise_rule": NOISE_RULE, "scenario": SCENARIO,
        "max_interventions": MAX_CASES,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "scene_sha256": cfg["baseline"]["scene_sha256"],
        "gpu": cfg["target_gpu"],
        "controls": [], "references": None, "selection": None,
        "cases": [], "failures": [], "qualifying_quality_cells": [],
    }
    def save() -> None:
        summary_path.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    save()

    try:
        verified0, control, evidence0, folder0 = run_case(
            root, scene, cfg["target_gpu"], "Q8_control_reference", 0, True)
        reference_info, ref_a, ref_b = reference_pair(folder0, evidence0)
        result["references"] = reference_info
        result["reference_generated"] = True
        result["controls"].append({
            k: v for k, v in verified0.items() if k != "key_rows"
        })
        save()
        verified1, control_repeat, _evidence1, _folder1 = run_case(
            root, scene, cfg["target_gpu"], "Q8_control_repeat", 0, False)
        result["controls"].append({
            k: v for k,v in verified1.items() if k != "key_rows"
        })
        save()
        if (verified0["image_sha256"] != verified1["image_sha256"] or
            control != control_repeat or
            verified0["coverage_sha256"] != verified1["coverage_sha256"] or
            verified0["key_rows"] != verified1["key_rows"]):
            raise ValueError("P1m3b two independent-process Q8 controls disagree")
        # Do not compare Q8 control against the original INTEGER image as a
        # quality label; record only its SHA as provenance for representation.
        result["old_integer_storage_PFM_sha256"] = (
            expected_sha(VARIANT, SCENARIO))
        selection = select_prospective_holdout(verified0["key_rows"])
        result["selection"] = {
            **selection,
            "source_control_Q8_PFM_sha256": verified0["image_sha256"],
            "M0_sha256": verified0["coverage_sha256"],
        }
        save()  # Must happen BEFORE ANY new holdout extra-ray GPU treatment.
        baseline_A = rgb_rms(control, ref_a)
        baseline_B = rgb_rms(control, ref_b)
        result["references"]["Q8_control_RMS_A"] = baseline_A
        result["references"]["Q8_control_RMS_B"] = baseline_B
        save()
        threshold = reference_info["RMS_reference_A_vs_B"]
        for selected in selection["selected"]:
            token = selected["token"]
            label = f"q8_{selected['stratum']}_{selected['cascade']}_{token}"
            candidate, payload, _evidence, _folder = run_case(
                root, scene, cfg["target_gpu"], label, token, False)
            if (candidate["coverage_sha256"] != verified0["coverage_sha256"] or
                candidate["selected_key_row"] != {
                    k: selected[k] for k in (
                        "token", "consumer_pixels", "producer_owner_outputs"
                    )
                }):
                raise ValueError("P1m3b candidate changed preselected key/coverage")
            delta = image_delta(control, payload)
            if (delta["changed_rgb_pixels"] == 0) != (
                verified0["image_sha256"] == candidate["image_sha256"]):
                raise ValueError("P1m3b SHA/float32 RGB influence mismatch")
            after_A = rgb_rms(payload, ref_a)
            after_B = rgb_rms(payload, ref_b)
            gain_A, gain_B = baseline_A - after_A, baseline_B - after_B
            candidate.pop("key_rows", None)
            candidate.update({
                "selection": selected,
                "image_delta_vs_Q8_control": delta,
                "Q8_control_RMS_reference_A": baseline_A,
                "Q8_control_RMS_reference_B": baseline_B,
                "candidate_RMS_reference_A": after_A,
                "candidate_RMS_reference_B": after_B,
                "signed_gain_A": gain_A, "signed_gain_B": gain_B,
                "signed_gain_ref_sensitivity": abs(gain_A - gain_B),
                "reference_RMS_noise_bound": threshold,
                "quality_signal": False,
                "reproduced": False,
            })
            result["cases"].append(candidate)
            save()
            if delta["changed_rgb_pixels"]:
                repeated, again, _ev, _folder = run_case(
                    root, scene, cfg["target_gpu"], label + "_repeat", token, False)
                if (again != payload or
                    repeated["image_sha256"] != candidate["image_sha256"] or
                    repeated["coverage_sha256"] != candidate["coverage_sha256"] or
                    repeated["selected_key_row"] != candidate["selected_key_row"] or
                    repeated["canonical_m1_trace"]["base_radiance_sum16"] !=
                    candidate["canonical_m1_trace"]["base_radiance_sum16"] or
                    repeated["canonical_m1_trace"]["extra_radiance_sum16"] !=
                    candidate["canonical_m1_trace"]["extra_radiance_sum16"]):
                    raise ValueError(f"P1m3b {label} image/hit-fate not repeatable")
                candidate["reproduced"] = True
                candidate["repeat_sha256"] = repeated["image_sha256"]
            if selected["stratum"] == "global_zero_negative" and delta["changed_rgb_pixels"]:
                raise ValueError("P1m3b zero-consumer negative control changed image")
            candidate["quality_signal"] = (
                candidate["reproduced"] and gain_A > threshold and gain_B > threshold
            )
            if candidate["quality_signal"]:
                result["qualifying_quality_cells"].append({
                    "token": token, "cascade": selected["cascade"],
                    "signed_gain_A": gain_A, "signed_gain_B": gain_B,
                    "reference_noise_RMS": threshold,
                })
            save()
        positive_cells = [c for c in result["cases"]
                          if c["selection"]["stratum"] == "max_positive"]
        if not any(c["image_delta_vs_Q8_control"]["changed_rgb_pixels"]
                   for c in positive_cells):
            result["status"] = "holdout-Q8-zero-influence-stop"
        elif not result["qualifying_quality_cells"]:
            result["status"] = "holdout-Q8-quality-not-detectable-stop"
        else:
            result["status"] = "holdout-Q8-signed-signal-calibration-only"
        result["quality_gain_established"] = bool(result["qualifying_quality_cells"])
        result["P1_predictor_go"] = False
        result["P2_scheduler_go"] = False
        result["next_gate"] = (
            "A reference-noise-exceeding positive signal on one MOVING-RIGID "
            "trajectory is NOT generalizable; preregister sealed deforming/other "
            "geometry, independent predictive ranking and paired GPU cost first."
            if result["qualifying_quality_cells"] else
            "STOP one-key Q8 P1 predictive quality/ROI expansion under this "
            "heldout trajectory. Do not tune observed key/directions/precision."
        )
        save()
        print(json.dumps({
            "status": result["status"], "keys": len(result["cases"]),
            "quality_signal_count": len(result["qualifying_quality_cells"]),
            "reference_RMS_noise_bound": threshold,
            "summary": str(summary_path),
        }, indent=2), flush=True)
        return 0
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as exc:
        result["status"] = "invalid-retained"
        result["failures"].append({"error": str(exc)})
        save()
        print(f"[P1m3b] invalid: {exc}; summary={summary_path}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as exc:
        print(f"P1m3b setup invalid: {exc}", file=sys.stderr)
        raise SystemExit(1)
